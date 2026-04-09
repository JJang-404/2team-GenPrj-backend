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
		conn = sqlite3.connect(self.db_path)
		conn.execute("PRAGMA foreign_keys = ON")
		return conn

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

	# 디자인 프로필 저장 테이블 생성 보장
	def EnsureDesignProfileTable(self) -> None:
		create_table_sql = (
			"CREATE TABLE IF NOT EXISTS design_profile_tbl ("
			"profile_id INTEGER PRIMARY KEY AUTOINCREMENT, "
			"user_id TEXT NOT NULL, "
			"profile_json TEXT NOT NULL, "
			"ai_image_id INTEGER NULL, "
			"created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')), "
			"CONSTRAINT valid_json CHECK (json_valid(profile_json)), "
			"FOREIGN KEY (user_id) REFERENCES users_tbl(user_id), "
			"FOREIGN KEY (ai_image_id) REFERENCES user_images_tbl(image_id)"
			")"
		)
		create_index_sql = (
			"CREATE INDEX IF NOT EXISTS idx_design_profile_tbl_user_id "
			"ON design_profile_tbl(user_id)"
		)

		with self._connect() as conn:
			cur = conn.cursor()
			cur.execute(create_table_sql)
			table_info = cur.execute("PRAGMA table_info(design_profile_tbl)").fetchall()
			column_names = {str(row[1]) for row in table_info}
			if "ai_image_id" not in column_names:
				cur.execute("ALTER TABLE design_profile_tbl ADD COLUMN ai_image_id INTEGER")
			cur.execute(create_index_sql)
			conn.commit()

	# 디자인 프로필 JSON 저장
	def InsertDesignProfile(self, user_id: str, profile_json: str, ai_image_id: int | None = None) -> tuple[int, str]:
		self.EnsureDesignProfileTable()
		if not user_id.strip():
			return (0, "user_id가 비어 있습니다.")
		if not self.GetUserById(user_id):
			return (0, "존재하지 않는 사용자입니다.")
		if ai_image_id is not None:
			image_row = self.GetUserImageById(ai_image_id)
			if image_row is None:
				return (0, "존재하지 않는 ai_image_id 입니다.")
			if str(image_row.get("user_id", "")) != user_id:
				return (0, "다른 사용자의 이미지로는 저장할 수 없습니다.")

		sql = "INSERT INTO design_profile_tbl (user_id, profile_json, ai_image_id) VALUES (?, ?, ?)"
		try:
			with self._connect() as conn:
				cur = conn.cursor()
				cur.execute(sql, (user_id, profile_json, ai_image_id))
				if cur.rowcount <= 0:
					conn.rollback()
					return (0, "INSERT 결과가 없습니다.")
				conn.commit()
				last_row_id = cur.lastrowid
				if last_row_id is None:
					return (0, "생성된 profile_id를 확인할 수 없습니다.")
				return (int(last_row_id), "OK")
		except sqlite3.IntegrityError as ex:
			return (0, str(ex))
		except Exception as ex:
			return (0, str(ex))

	# profile_id 기준 디자인 프로필 저장 (0: INSERT, 0 초과: UPDATE)
	def SaveDesignProfile(
		self,
		profile_id: int,
		user_id: str,
		profile_json: str,
		ai_image_id: int | None = None,
	) -> tuple[int, str]:
		self.EnsureDesignProfileTable()
		if not user_id.strip():
			return (0, "user_id가 비어 있습니다.")
		if not self.GetUserById(user_id):
			return (0, "존재하지 않는 사용자입니다.")
		if ai_image_id is not None:
			image_row = self.GetUserImageById(ai_image_id)
			if image_row is None:
				return (0, "존재하지 않는 ai_image_id 입니다.")
			if str(image_row.get("user_id", "")) != user_id:
				return (0, "다른 사용자의 이미지로는 저장할 수 없습니다.")

		if profile_id <= 0:
			return self.InsertDesignProfile(user_id=user_id, profile_json=profile_json, ai_image_id=ai_image_id)

		find_sql = "SELECT profile_id FROM design_profile_tbl WHERE profile_id = ? AND user_id = ?"
		rows = self.SelectSQL(find_sql, (profile_id, user_id))
		if not rows:
			return (0, "수정할 디자인 프로필이 없습니다.")

		update_sql = "UPDATE design_profile_tbl SET profile_json = ?, ai_image_id = ? WHERE profile_id = ? AND user_id = ?"
		try:
			with self._connect() as conn:
				cur = conn.cursor()
				cur.execute(update_sql, (profile_json, ai_image_id, profile_id, user_id))
				if cur.rowcount <= 0:
					conn.rollback()
					return (0, "UPDATE 결과가 없습니다.")
				conn.commit()
				return (profile_id, "OK")
		except sqlite3.IntegrityError as ex:
			return (0, str(ex))
		except Exception as ex:
			return (0, str(ex))

	# user_id 기준 디자인 프로필 목록 조회
	def GetDesignProfilesByUserId(self, user_id: str) -> list[dict[str, Any]]:
		self.EnsureDesignProfileTable()
		sql = (
			"SELECT profile_id, user_id, profile_json, ai_image_id, created_at "
			"FROM design_profile_tbl WHERE user_id = ? ORDER BY profile_id"
		)
		return self.SelectSQL(sql, (user_id,))
