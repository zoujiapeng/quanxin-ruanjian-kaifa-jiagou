"""
共享运行时状态（日志缓存等）
供 server.py 写入，features 读取
"""
import time

_executor_logs: list[dict] = []
_MAX_LOGS = 1000


def push_log(message: str):
    _executor_logs.append({"ts": time.time(), "msg": message})
    if len(_executor_logs) > _MAX_LOGS:
        _executor_logs.pop(0)


def get_logs(count: int = 50) -> list[dict]:
    return _executor_logs[-count:]
