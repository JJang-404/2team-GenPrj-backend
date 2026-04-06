# SQLite 데이터베이스 연결 및 쿼리 실행을 담당하는 클라이언트 클래스
from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Any
from backend.common.defines import DB_FILE_PATH

class SQLiteDB:
	def __init__(self)-> None:
		# DB 파일 경로 설정 및 쿼리 큐 초기화
		self.db_path = Path(DB_FILE_PATH)
		self._sql_queue: list[str] = []

	# SQLite 연결 객체 생성
	def _connect(self) -> sqlite3.Connection:
		return sqlite3.connect(self.db_path)

	# SELECT 쿼리 실행 후 결과를 딕셔너리 리스트로 반환
	def SelectSQL(self, sql: str, params: Any = None) -> list[dict[str, Any]]:
		with self._connect() as conn:
			conn.row_factory = sqlite3.Row
			cur = conn.cursor()
			if params is not None:
				cur.execute(sql, params)
			else:
				cur.execute(sql)
			return [dict(row) for row in cur.fetchall()]

	# 단일 INSERT/UPDATE/DELETE 쿼리 실행
	def ExecuteSQL(self, sql: str, params: Any = None) -> bool:
		with self._connect() as conn:
			cur = conn.cursor()
			if params is not None:
				cur.execute(sql, params)
			else:
				cur.execute(sql)
			conn.commit()
		return True

	# 다중 데이터 일괄 실행
	def ExecuteMany(self, sql: str, data_list: list[Any]) -> int:
		if not data_list:
			return 0
		with self._connect() as conn:
			cur = conn.cursor()
			cur.executemany(sql, data_list)
			count = cur.rowcount
			conn.commit()
		return count

	# 배치 처리를 위해 쿼리 큐에 추가
	def AddSQL(self, sql: str) -> None:
		self._sql_queue.append(sql)

	# 다중 쿼리 실행 또는 영향받은 행 수 반환 기능 포함 실행기
	def ExecuteSQLEx(self, sql_or_limit: Any = None, out_map: dict[str, Any] | None = None) -> int | bool:
		# 리스트 형태의 다중 쿼리 일괄 실행
		if isinstance(sql_or_limit, list):
			count = 0
			with self._connect() as conn:
				cur = conn.cursor()
				for sql in sql_or_limit:
					cur.execute(str(sql))
					count += cur.rowcount if cur.rowcount > 0 else 0
				conn.commit()
			return count

		# 단일 문자열 쿼리 실행 및 영향받은 행 수 기록
		if isinstance(sql_or_limit, str):
			with self._connect() as conn:
				cur = conn.cursor()
				cur.execute(sql_or_limit)
				conn.commit()
				if out_map is not None:
					out_map["executeCount"] = cur.rowcount
			return True

		# 큐에 쌓인 쿼리들을 지정된 개수만큼 실행 (Batch)
		if isinstance(sql_or_limit, int):
			limit = sql_or_limit
			if limit <= 0:
				limit = len(self._sql_queue)
			use_sql = self._sql_queue[:limit]
			self._sql_queue = self._sql_queue[limit:]
			with self._connect() as conn:
				cur = conn.cursor()
				count = 0
				for sql in use_sql:
					cur.execute(sql)
					count += cur.rowcount if cur.rowcount > 0 else 0
				conn.commit()
			return count

		return False
