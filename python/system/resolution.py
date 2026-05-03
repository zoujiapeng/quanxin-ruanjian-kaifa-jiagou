"""Resolution adaptation — scale coordinates between screen resolutions."""
from typing import Optional
import pyautogui


class ResolutionAdapter:
    """Adapt automation coordinates to different screen resolutions."""

    def __init__(self, base_width: Optional[int] = None, base_height: Optional[int] = None):
        self.base_width = base_width
        self.base_height = base_height

    def set_base(self, width: int, height: int):
        self.base_width = width
        self.base_height = height

    @property
    def current_size(self):
        return pyautogui.size()

    @property
    def scale_x(self) -> float:
        w, _ = self.current_size
        return w / self.base_width if self.base_width else 1.0

    @property
    def scale_y(self) -> float:
        _, h = self.current_size
        return h / self.base_height if self.base_height else 1.0

    def adapt(self, x: float, y: float):
        return (x * self.scale_x, y * self.scale_y)

    def adapt_region(self, x: float, y: float, w: float, h: float):
        return (x * self.scale_x, y * self.scale_y, w * self.scale_x, h * self.scale_y)
