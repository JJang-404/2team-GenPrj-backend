# SQLite 데이터베이스 연결 및 쿼리 실행을 담당하는 클라이언트 클래스
from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Any
from app.common.defines import DB_FILE_PATH

class SQLiteDB:
	def __init__(self)-> None:
		# DB 파일 경로 설정 및 쿼리 큐 초기화
		self.db_path = Path(DB_FILE_PATH)
		self.db_path.parent.mkdir(parents=True, exist_ok=True)
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

	# 로그인 ID 기준 단건 조회
	def GetUserByLoginId(self, user_id: str) -> dict[str, Any] | None:
		sql = "SELECT user_no, user_id, user_name, user_passwd FROM users_tbl WHERE user_id = ?"
		rows = self.SelectSQL(sql, (user_id,))
		return rows[0] if rows else None

	# 회원가입용 사용자 추가 후 생성된 user_no 반환
	def InsertUser(self, user_id: str, user_name: str, user_passwd: str) -> int:
		sql = "INSERT INTO users_tbl (user_id, user_name, user_passwd) VALUES (?, ?, ?)"
		with self._connect() as conn:
			cur = conn.cursor()
			cur.execute(sql, (user_id, user_name, user_passwd))
			conn.commit()
			last_row_id = cur.lastrowid
			if last_row_id is None:
				return 0
			return int(last_row_id)

	# 로그인용 자격 검증
	def VerifyUser(self, user_id: str, user_passwd: str) -> dict[str, Any] | None:
		sql = "SELECT user_no, user_id, user_name FROM users_tbl WHERE user_id = ? AND user_passwd = ?"
		rows = self.SelectSQL(sql, (user_id, user_passwd))
		return rows[0] if rows else None

	# 로그인 ID 기준 단건 조회 (호환 메서드)
	def GetUserById(self, user_id: str) -> dict[str, Any] | None:
		sql = "SELECT user_no, user_id, user_name FROM users_tbl WHERE user_id = ?"
		rows = self.SelectSQL(sql, (user_id,))
		return rows[0] if rows else None

	# 이미지 메타데이터 저장
	def InsertUserImage(
		self,
		user_id: str,
		original_name: str,
		file_desc: str,
		stored_name: str,
		stored_path: str,
		content_type: str,
		file_ext: str,
		file_size: int,
	) -> int:
		sql = (
			"INSERT INTO user_images_tbl "
			"(user_id, original_name, file_desc, stored_name, stored_path, content_type, file_ext, file_size) "
			"VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
		)
		with self._connect() as conn:
			cur = conn.cursor()
			cur.execute(
				sql,
				(user_id, original_name, file_desc, stored_name, stored_path, content_type, file_ext, file_size),
			)
			conn.commit()
			last_row_id = cur.lastrowid
			if last_row_id is None:
				return 0
			return int(last_row_id)

	# image_id 기준 이미지 메타 조회
	def GetUserImageById(self, image_id: int) -> dict[str, Any] | None:
		sql = (
			"SELECT image_id, user_id, original_name, file_desc, stored_name, stored_path, content_type, file_ext, file_size, created_at "
			"FROM user_images_tbl WHERE image_id = ?"
		)
		rows = self.SelectSQL(sql, (image_id,))
		return rows[0] if rows else None

	# 사용자별 이미지 목록 조회
	def GetUserImages(self, user_id: str) -> list[dict[str, Any]]:
		sql = (
			"SELECT image_id, user_id, original_name, file_desc, stored_name, stored_path, content_type, file_ext, file_size, created_at "
			"FROM user_images_tbl WHERE user_id = ? ORDER BY image_id DESC"
		)
		return self.SelectSQL(sql, (user_id,))

	# user_id, 파일명, 설명 키워드로 이미지 목록 조회
	def FindUserImages(
		self,
		user_id: str | None = None,
		file_name: str | None = None,
		file_desc: str | None = None,
	) -> list[dict[str, Any]]:
		base_sql = (
			"SELECT image_id, user_id, original_name, file_desc, stored_name, stored_path, content_type, file_ext, file_size, created_at "
			"FROM user_images_tbl"
		)
		where_parts: list[str] = []
		params: list[Any] = []

		if user_id is not None:
			where_parts.append("user_id = ?")
			params.append(user_id)

		normalized_name = (file_name or "").strip()
		if normalized_name:
			where_parts.append("(original_name LIKE ? OR stored_name LIKE ? OR stored_path LIKE ?)")
			like_value = f"%{normalized_name}%"
			params.extend([like_value, like_value, like_value])

		normalized_desc = (file_desc or "").strip()
		if normalized_desc:
			where_parts.append("file_desc LIKE ?")
			params.append(f"%{normalized_desc}%")

		if where_parts:
			base_sql += " WHERE " + " AND ".join(where_parts)

		base_sql += " ORDER BY image_id DESC"
		return self.SelectSQL(base_sql, tuple(params))
