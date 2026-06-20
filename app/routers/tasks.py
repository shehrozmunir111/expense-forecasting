from fastapi import APIRouter

from app.core.celery_app import celery_app

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/{task_id}")
def get_task_status(task_id: str):
    """Return the state (PENDING/STARTED/SUCCESS/FAILURE) and result of a job."""
    res = celery_app.AsyncResult(task_id)
    payload = {"task_id": task_id, "status": res.status}
    if res.successful():
        payload["result"] = res.result
    elif res.failed():
        payload["error"] = str(res.result)
    return payload
