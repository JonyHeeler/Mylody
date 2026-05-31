"""测试日志路由：暴露后端日志尾部内容给本地 Web UI。"""

from collections import deque

from fastapi import APIRouter, Query

from mylody.utils.paths import get_log_dir

router = APIRouter()


@router.get("/api/logs")
async def get_logs(lines: int = Query(default=80, ge=1, le=300)) -> dict:
    """返回后端日志文件尾部内容。"""
    log_file = get_log_dir() / "mylody.log"
    if not log_file.exists():
        return {"status": "ok", "path": str(log_file), "lines": []}

    tail: deque[str] = deque(maxlen=lines)
    with log_file.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            tail.append(line.rstrip("\n"))

    return {"status": "ok", "path": str(log_file), "lines": list(tail)}
