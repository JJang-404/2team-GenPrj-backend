import threading
import uuid
from typing import Any, Callable

from fastapi.responses import JSONResponse, Response

_ASYNC_JOB_STORES: dict[str, dict[str, dict[str, Any]]] = {
    "generate": {},
    "changeimage": {},
    "makebgimage": {},
    "makebgimageollama": {},
    "generatecomfyui": {},
    "changeimagecomfyui": {},
    "changeimagecomfyui_opt": {},
    "makebgimagecomfyui": {},
}
_ASYNC_JOB_STORE_LOCK = threading.Lock()


def _get_async_job(job_kind: str, job_id: str) -> dict[str, Any] | None:
    with _ASYNC_JOB_STORE_LOCK:
        job = _ASYNC_JOB_STORES[job_kind].get(job_id)
        return dict(job) if job is not None else None


def _update_async_job(job_kind: str, job_id: str, **updates: Any) -> None:
    with _ASYNC_JOB_STORE_LOCK:
        job = _ASYNC_JOB_STORES[job_kind].get(job_id)
        if job is None:
            return
        job.update(updates)


def _run_async_job(job_kind: str, job_id: str, runner: Callable[[], tuple[bytes, str]]) -> None:
    _update_async_job(job_kind, job_id, status="running")
    try:
        body, content_type = runner()
    except Exception as ex:
        print(f"[async-job Error] kind={job_kind}, job_id={job_id}, error={type(ex).__name__}: {ex}")
        _update_async_job(job_kind, job_id, status="failed", error=str(ex))
        return

    _update_async_job(
        job_kind,
        job_id,
        status="done",
        error=None,
        result_body=body,
        content_type=content_type,
    )


def _create_async_job(job_kind: str, runner: Callable[[], tuple[bytes, str]]) -> dict[str, Any]:
    job_id = str(uuid.uuid4())
    with _ASYNC_JOB_STORE_LOCK:
        _ASYNC_JOB_STORES[job_kind][job_id] = {
            "job_id": job_id,
            "status": "queued",
            "error": None,
            "content_type": None,
            "result_body": None,
        }

    worker = threading.Thread(
        target=_run_async_job,
        args=(job_kind, job_id, runner),
        daemon=True,
    )
    worker.start()
    return {"job_id": job_id, "status": "queued"}


def _build_job_status_response(job_kind: str, job_id: str) -> JSONResponse:
    job = _get_async_job(job_kind, job_id)
    if job is None:
        return JSONResponse(content={"detail": "존재하지 않는 job_id입니다."}, status_code=404)

    return JSONResponse(
        content={
            "job_id": job_id,
            "status": job.get("status"),
            "error": job.get("error"),
        }
    )


def _build_job_result_response(job_kind: str, job_id: str) -> Response:
    job = _get_async_job(job_kind, job_id)
    if job is None:
        return JSONResponse(content={"detail": "존재하지 않는 job_id입니다."}, status_code=404)

    status = str(job.get("status") or "")
    if status in {"queued", "running"}:
        return JSONResponse(
            content={"detail": f"작업이 아직 완료되지 않았습니다. status={status}"},
            status_code=409,
        )
    if status == "failed":
        return JSONResponse(
            content={"detail": str(job.get("error") or "작업이 실패했습니다.")},
            status_code=500,
        )

    result_body = job.get("result_body")
    content_type = str(job.get("content_type") or "application/octet-stream")
    if not isinstance(result_body, bytes):
        return JSONResponse(content={"detail": "작업 결과가 없습니다."}, status_code=500)

    return Response(content=result_body, media_type=content_type)
