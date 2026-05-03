"""
感知层: 图像识别模块
- 模板匹配（多尺度）
- 多目标检测
- 区域变化检测（帧差/SSIM）
- 颜色检测
- 进度条识别
- 截图缓存
"""

from __future__ import annotations
import time
import hashlib
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

import cv2
import numpy as np
from PIL import Image
import mss

try:
    from skimage.metrics import structural_similarity as ssim
    HAS_SKIMAGE = True
except ImportError:
    HAS_SKIMAGE = False


BBox = Tuple[int, int, int, int]   # x, y, w, h
Point = Tuple[int, int]            # x, y


class ScreenCapture:
    """截图工具，支持全屏和区域截图，带缓存"""

    _cache: Dict[str, tuple] = {}    # hash → (timestamp, img)
    _cache_ttl: float = 0.1          # 100ms 缓存

    @classmethod
    def capture(cls, region: Optional[BBox] = None) -> np.ndarray:
        """截图，返回 BGR numpy array"""
        with mss.mss() as sct:
            if region:
                x, y, w, h = region
                monitor = {"left": x, "top": y, "width": w, "height": h}
            else:
                monitor = sct.monitors[0]
            shot = sct.grab(monitor)
            img = np.array(shot)
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    @classmethod
    def capture_cached(cls, region: Optional[BBox] = None) -> np.ndarray:
        key = str(region)
        now = time.time()
        if key in cls._cache:
            ts, img = cls._cache[key]
            if now - ts < cls._cache_ttl:
                return img
        img = cls.capture(region)
        cls._cache[key] = (now, img)
        return img

    @classmethod
    def clear_cache(cls):
        cls._cache.clear()


class TemplateMatcher:
    """
    模板匹配器
    - 多尺度匹配
    - 多目标检测
    - 相似度阈值
    """

    def __init__(self, template_dir: str = "templates"):
        self._template_dir = Path(template_dir)
        self._cache: Dict[str, np.ndarray] = {}

    def load_template(self, name: str) -> Optional[np.ndarray]:
        if name in self._cache:
            return self._cache[name]
        for ext in [".png", ".jpg", ".bmp"]:
            path = self._template_dir / (name + ext)
            if path.exists():
                tmpl = cv2.imread(str(path))
                self._cache[name] = tmpl
                return tmpl
        return None

    def preload_all(self):
        """预加载所有模板"""
        for f in self._template_dir.glob("*.*"):
            if f.suffix.lower() in {".png", ".jpg", ".bmp"}:
                name = f.stem
                if name not in self._cache:
                    self._cache[name] = cv2.imread(str(f))

    def find(
        self,
        template: np.ndarray | str,
        screen: Optional[np.ndarray] = None,
        threshold: float = 0.8,
        region: Optional[BBox] = None,
    ) -> Optional[Tuple[Point, float]]:
        """
        查找单个目标，返回 (center_point, confidence) 或 None
        """
        if isinstance(template, str):
            tmpl = self.load_template(template)
            if tmpl is None:
                return None
        else:
            tmpl = template

        if screen is None:
            screen = ScreenCapture.capture_cached(region)

        result = self._match_multiscale(screen, tmpl, threshold)
        return result

    def find_all(
        self,
        template: np.ndarray | str,
        screen: Optional[np.ndarray] = None,
        threshold: float = 0.8,
        region: Optional[BBox] = None,
        max_results: int = 10,
    ) -> List[Tuple[Point, float]]:
        """查找所有目标"""
        if isinstance(template, str):
            tmpl = self.load_template(template)
            if tmpl is None:
                return []
        else:
            tmpl = template

        if screen is None:
            screen = ScreenCapture.capture_cached(region)

        return self._match_all(screen, tmpl, threshold, max_results)

    def _match_multiscale(
        self, screen: np.ndarray, template: np.ndarray, threshold: float
    ) -> Optional[Tuple[Point, float]]:
        """多尺度模板匹配"""
        h, w = template.shape[:2]
        best_val = 0.0
        best_loc = None
        best_scale = 1.0

        for scale in np.linspace(0.5, 1.5, 13):
            tw = int(w * scale)
            th = int(h * scale)
            if tw < 10 or th < 10:
                continue
            resized = cv2.resize(template, (tw, th))
            if resized.shape[0] > screen.shape[0] or resized.shape[1] > screen.shape[1]:
                continue

            result = cv2.matchTemplate(screen, resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val > best_val:
                best_val = max_val
                best_loc = max_loc
                best_scale = scale

        if best_val < threshold or best_loc is None:
            return None

        tw = int(w * best_scale)
        th = int(h * best_scale)
        cx = best_loc[0] + tw // 2
        cy = best_loc[1] + th // 2
        return (cx, cy), best_val

    def _match_all(
        self,
        screen: np.ndarray,
        template: np.ndarray,
        threshold: float,
        max_results: int,
    ) -> List[Tuple[Point, float]]:
        """非极大值抑制查找所有目标"""
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        h, w = template.shape[:2]
        locations = np.where(result >= threshold)
        matches = []

        for pt in zip(*locations[::-1]):
            score = result[pt[1], pt[0]]
            cx = pt[0] + w // 2
            cy = pt[1] + h // 2
            matches.append(((cx, cy), float(score)))

        # NMS: 合并相近点
        return self._nms(matches, min_dist=w // 2)[:max_results]

    def _nms(self, matches: list, min_dist: int = 20) -> list:
        if not matches:
            return []
        matches.sort(key=lambda x: -x[1])
        kept = []
        for pt, score in matches:
            too_close = False
            for kpt, _ in kept:
                dist = ((pt[0] - kpt[0]) ** 2 + (pt[1] - kpt[1]) ** 2) ** 0.5
                if dist < min_dist:
                    too_close = True
                    break
            if not too_close:
                kept.append((pt, score))
        return kept


class ChangeDetector:
    """区域变化检测"""

    def __init__(self):
        self._prev_frame: Optional[np.ndarray] = None

    def has_changed(
        self,
        region: Optional[BBox] = None,
        method: str = "ssim",
        threshold: float = 0.95,
    ) -> bool:
        """检测区域是否发生变化"""
        curr = ScreenCapture.capture(region)
        if self._prev_frame is None:
            self._prev_frame = curr
            return False

        if method == "ssim" and HAS_SKIMAGE:
            gray_prev = cv2.cvtColor(self._prev_frame, cv2.COLOR_BGR2GRAY)
            gray_curr = cv2.cvtColor(curr, cv2.COLOR_BGR2GRAY)
            score, _ = ssim(gray_prev, gray_curr, full=True)
            changed = score < threshold
        else:
            # 帧差法
            diff = cv2.absdiff(self._prev_frame, curr)
            changed = np.mean(diff) > (1 - threshold) * 255

        self._prev_frame = curr
        return changed

    def is_stable(self, region: Optional[BBox] = None, duration: float = 1.0) -> bool:
        """等待区域稳定"""
        end = time.time() + duration
        while time.time() < end:
            if self.has_changed(region):
                end = time.time() + duration
            time.sleep(0.1)
        return True


class ColorDetector:
    """颜色检测 + 进度条识别"""

    @staticmethod
    def detect_color(
        color_hsv: Tuple[int, int, int],
        tolerance: Tuple[int, int, int] = (10, 50, 50),
        region: Optional[BBox] = None,
    ) -> float:
        """返回指定颜色在区域内的占比"""
        img = ScreenCapture.capture_cached(region)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        h, s, v = color_hsv
        tol_h, tol_s, tol_v = tolerance
        lower = np.array([max(0, h - tol_h), max(0, s - tol_s), max(0, v - tol_v)])
        upper = np.array([min(179, h + tol_h), min(255, s + tol_s), min(255, v + tol_v)])
        mask = cv2.inRange(hsv, lower, upper)
        ratio = np.sum(mask > 0) / mask.size
        return float(ratio)

    @staticmethod
    def detect_progress_bar(
        region: BBox,
        fg_color_hsv: Optional[Tuple] = None,
        direction: str = "auto",
    ) -> float:
        """
        进度条识别，返回 0.0~1.0
        算法: HSV饱和度加权 + 逐行/列找填充端 → 平均填充比例
        direction: 'horizontal' | 'vertical' | 'auto'
        """
        img = ScreenCapture.capture(region)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        s = hsv[:, :, 1].astype(np.float32)
        v = hsv[:, :, 2].astype(np.float32)

        # 饱和度加权亮度: 彩色(已填充)区域分数高，灰色(未填充)区域分数低
        filled_score = s * (v / 255.0)
        score_u8 = filled_score.astype(np.uint8)
        mask = cv2.threshold(score_u8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

        # Otsu 单峰回退：全黑或全白则用固定阈值 30
        white_px = np.sum(mask > 0)
        if white_px == 0 or white_px == mask.size:
            mask = cv2.threshold(score_u8, 30, 255, cv2.THRESH_BINARY)[1]

        h, w = mask.shape
        if direction == "auto":
            direction = "horizontal" if w > h else "vertical"

        if direction == "horizontal":
            row_fills = []
            for r in range(mask.shape[0]):
                filled = np.where(mask[r, :] > 0)[0]
                if len(filled) > 0:
                    row_fills.append((filled[-1] + 1) / mask.shape[1])
            return float(np.mean(row_fills)) if row_fills else 0.0
        else:
            col_fills = []
            for c in range(mask.shape[1]):
                filled = np.where(mask[:, c] > 0)[0]
                if len(filled) > 0:
                    col_fills.append((filled[-1] + 1) / mask.shape[0])
            return float(np.mean(col_fills)) if col_fills else 0.0


class SceneClassifier:
    """场景识别（基于特征哈希）"""

    def __init__(self):
        self._scenes: Dict[str, np.ndarray] = {}

    def register_scene(self, name: str, image: np.ndarray):
        self._scenes[name] = self._hash(image)

    def identify(self, screen: Optional[np.ndarray] = None) -> Optional[str]:
        if screen is None:
            screen = ScreenCapture.capture()
        h = self._hash(screen)
        best_name = None
        best_sim = 0.0
        for name, ref_hash in self._scenes.items():
            sim = self._similarity(h, ref_hash)
            if sim > best_sim:
                best_sim = sim
                best_name = name
        if best_sim > 0.85:
            return best_name
        return None

    def _hash(self, img: np.ndarray, size: int = 16) -> np.ndarray:
        """感知哈希"""
        small = cv2.resize(img, (size, size))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        mean = gray.mean()
        return (gray >= mean).flatten()

    def _similarity(self, h1: np.ndarray, h2: np.ndarray) -> float:
        return float(np.sum(h1 == h2)) / len(h1)
