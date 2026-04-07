from __future__ import annotations

import sqlite3
from pathlib import Path

from app.common.defines import DB_FILE_PATH


def create_users_table() -> None:
    db_path = Path(DB_FILE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    sql_file_path = Path(__file__).with_name("SQLiteCreate.sql")
    sql_text = sql_file_path.read_text(encoding="utf-8")

    with sqlite3.connect(db_path) as conn:
        conn.executescript(sql_text)

        # 기존 DB 마이그레이션: user_images_tbl에 file_desc 컬럼이 없으면 추가
        table_info = conn.execute("PRAGMA table_info(user_images_tbl)").fetchall()
        column_names = {str(row[1]) for row in table_info}
        if "file_desc" not in column_names:
            conn.execute("ALTER TABLE user_images_tbl ADD COLUMN file_desc TEXT NOT NULL DEFAULT ''")

        conn.commit()

    print(f"SQLite schema created successfully in: {db_path}")


if __name__ == "__main__":
    create_users_table()
