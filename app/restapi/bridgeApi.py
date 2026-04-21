import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter(prefix="/addhelper/bridge", tags=["addhelper-bridge"])


_store: dict[str, Any] = {}


class EditingBridgeRequest(BaseModel):
    payload: Any


@router.post("/editing")
def create_editing_bridge(req: EditingBridgeRequest) -> dict[str, str]:
    token = uuid.uuid4().hex
    _store[token] = req.payload
    return {"token": token}


@router.get("/editing/{token}")
def read_editing_bridge(token: str) -> Any:
    if token not in _store:
        raise HTTPException(status_code=404, detail="token not found")
    return _store[token]
