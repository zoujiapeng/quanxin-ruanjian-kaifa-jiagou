"""
功能模块共享工具函数
"""
from typing import Optional, Tuple
import random
import time


def parse_region(region_str: str) -> Optional[Tuple[int, int, int, int]]:
    """解析 'x,y,w,h' 格式的区域字符串"""
    if not region_str or not region_str.strip():
        return None
    try:
        parts = [int(x) for x in region_str.strip().split(",")]
        return tuple(parts) if len(parts) == 4 else None
    except Exception:
        return None


def resolve_coord(target: str) -> Tuple[int, int]:
    """解析 'x,y' 坐标"""
    try:
        parts = target.strip().split(",")
        return int(parts[0]), int(parts[1])
    except Exception:
        return 0, 0


def sim_delay(min_s: float = 0.1, max_s: float = 0.3):
    """模拟模式下的随机延迟"""
    time.sleep(random.uniform(min_s, max_s))
