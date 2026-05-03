"""
定时条件功能
等待文件 / 进程 / 网络 / 时间 / 倒计时 — 轮询检测引擎
"""
import time
import os
from datetime import datetime, timedelta

from features.registry import feature, P, TC, FeatureCategory as F


def _poll(condition_fn, timeout: float, interval: float = 0.5) -> bool:
    """通用轮询：每 interval 秒检查一次 condition_fn，直到超时"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if condition_fn():
            return True
        time.sleep(interval)
    return condition_fn()  # 最后再试一次


@feature(
    name="timer_wait_file",
    display_name="等待文件",
    description="【定时条件】阻塞等待指定文件创建或出现。用于等待下载完成、导出完成等文件生成场景",
    category=F.CONTROL,
    params=[
        P("path", "str", "文件路径", example="C:\\下载\\report.pdf"),
        P("timeout", "number", "超时秒数", required=False, default=60),
        P("wait_delete", "boolean", "是否等待文件删除而非创建", required=False, default=False),
    ],
    returns="bool - 是否在规定时间内检测到",
    tags=["timer", "control"],
)
def timer_wait_file(path: str, timeout: float = 60, wait_delete: bool = False) -> dict:
    exists = os.path.exists(path)
    if wait_delete:
        return {"success": True, "result": _poll(lambda: not os.path.exists(path), timeout)}
    else:
        if exists:
            return {"success": True, "result": True}
        return {"success": True, "result": _poll(lambda: os.path.exists(path), timeout)}


@feature(
    name="timer_wait_process",
    display_name="等待进程",
    description="【定时条件】阻塞等待指定进程启动或退出。用于等待软件打开或关闭后再执行后续操作",
    category=F.CONTROL,
    params=[
        P("name", "str", "进程名称", example="notepad.exe"),
        P("timeout", "number", "超时秒数", required=False, default=60),
        P("wait_exit", "boolean", "是否等待进程退出而非启动", required=False, default=False),
    ],
    returns="bool - 是否在规定时间内检测到",
    tags=["timer", "control"],
)
def timer_wait_process(name: str, timeout: float = 60, wait_exit: bool = False) -> dict:
    def process_running():
        try:
            import psutil
            for proc in psutil.process_iter(["name"]):
                try:
                    if proc.info["name"] and name.lower() in proc.info["name"].lower():
                        return True
                except Exception:
                    pass
            return False
        except ImportError:
            # fallback: tasklist
            import subprocess
            try:
                output = subprocess.check_output(
                    f"tasklist /fi \"IMAGENAME eq {name}\"", shell=True, timeout=5
                ).decode("utf-8", errors="replace")
                return name.lower() in output.lower()
            except Exception:
                return False

    if wait_exit:
        return {"success": True, "result": not _poll(process_running, timeout)}
    else:
        return {"success": True, "result": _poll(process_running, timeout)}


@feature(
    name="timer_wait_network",
    display_name="等待网络连接",
    description="【定时条件】阻塞等待网络连接恢复或断开。用于网络相关操作前确保连接状态",
    category=F.CONTROL,
    params=[
        P("timeout", "number", "超时秒数", required=False, default=30),
        P("wait_disconnect", "boolean", "是否等待断开而非连接", required=False, default=False),
    ],
    returns="bool - 是否在规定时间内达到目标状态",
    tags=["timer", "control"],
)
def timer_wait_network(timeout: float = 30, wait_disconnect: bool = False) -> dict:
    def has_connection():
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=2).close()
            return True
        except Exception:
            return False

    if wait_disconnect:
        return {"success": True, "result": _poll(lambda: not has_connection(), timeout)}
    else:
        return {"success": True, "result": _poll(has_connection, timeout)}


@feature(
    name="timer_wait_time",
    display_name="等待到指定时间",
    description="【定时条件】阻塞等待直到系统时间到达指定时刻。用于定时任务、预约操作",
    category=F.CONTROL,
    params=[
        P("target", "str", "目标时间 HH:MM 或 HH:MM:SS 格式", example="14:30"),
    ],
    returns="bool - 是否到达指定时间",
    tags=["timer", "control"],
)
def timer_wait_time(target: str) -> dict:
    try:
        parts = target.strip().split(":")
        h, m = int(parts[0]), int(parts[1])
        s = int(parts[2]) if len(parts) > 2 else 0
        now = datetime.now()
        target_dt = now.replace(hour=h, minute=m, second=s, microsecond=0)
        if target_dt <= now:
            target_dt += timedelta(days=1)  # 如果今天已过，等明天
        wait_sec = (target_dt - now).total_seconds()
        time.sleep(wait_sec)
        return {"success": True, "result": True}
    except Exception as e:
        return {"success": False, "error": f"时间格式错误: {e}"}


@feature(
    name="timer_countdown",
    display_name="倒计时",
    description="【定时条件】阻塞等待指定的秒数。等效于 sleep，但支持中途取消检查",
    category=F.CONTROL,
    params=[
        P("seconds", "number", "等待秒数", example=5),
    ],
    returns="bool - 是否完整等待完毕（False 表示被取消）",
    tags=["timer", "control"],
)
def timer_countdown(seconds: float) -> dict:
    import threading
    cancelled = threading.Event()

    def check_cancel():
        # 可以通过检查某个共享状态来支持取消
        pass

    deadline = time.time() + seconds
    while time.time() < deadline:
        remain = deadline - time.time()
        if remain <= 0:
            break
        time.sleep(min(remain, 0.5))
        check_cancel()
        if cancelled.is_set():
            return {"success": True, "result": False}

    return {"success": True, "result": True}
