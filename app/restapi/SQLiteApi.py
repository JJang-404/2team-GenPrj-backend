from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.common.util import error_response, ok_response
from app.db.SQLiteDB import SQLiteDB


router = APIRouter(prefix="/addhelper/sqlite", tags=["addhelper-sqlite"])


class SqlExecRequest(BaseModel):
	sql: str = Field(..., min_length=1)
	params: list[Any] | None = None


def _is_read_query(sql: str) -> bool:
	first = (sql or "").strip().split(" ", 1)[0].lower()
	return first in {"select", "pragma", "with"}


@router.post("/putsql", response_model=None)
def put_sql(req: SqlExecRequest):
	# 개발/테스트 용도: 전달받은 SQL을 그대로 실행합니다.
	try:
		db = SQLiteDB()
		sql = req.sql.strip()
		params_tuple = tuple(req.params or [])

		if _is_read_query(sql):
			rows = db.SelectSQL(sql, params_tuple)
			return ok_response(
				{
					"data": f"조회 성공 ({len(rows)}건)",
					"datalist": rows,
				}
			)

		db.ExecuteSQL(sql, params_tuple if req.params is not None else None)
		return ok_response({"data": "실행 성공"})
	except Exception as ex:
		return error_response(str(ex))
