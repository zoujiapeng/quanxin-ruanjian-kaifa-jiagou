"""Bezier curve generation for human-like mouse movement."""
import math
import random


class BezierCurve:
    """Generate Bezier curve paths for human-like mouse movement."""

    @staticmethod
    def cubic_bezier(t: float, p0, p1, p2, p3):
        u = 1 - t
        x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
        y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
        return (x, y)

    @staticmethod
    def generate_path(start_x, start_y, end_x, end_y, num_points=None, smoothness=0.4, randomness=0.2):
        if num_points is None:
            dist = math.hypot(end_x - start_x, end_y - start_y)
            num_points = max(10, min(100, int(dist / 5)))
        start = (float(start_x), float(start_y))
        end = (float(end_x), float(end_y))
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        offset_mag = math.hypot(dx, dy) * smoothness
        r1, r2 = random.uniform(-randomness, randomness), random.uniform(-randomness, randomness)
        r3, r4 = random.uniform(-randomness, randomness), random.uniform(-randomness, randomness)
        cp1 = (start[0] + dx * 0.25 + offset_mag * (0.3 * r1 + 0.2),
               start[1] + dy * 0.25 + offset_mag * (0.3 * r2 + 0.2))
        cp2 = (end[0] - dx * 0.25 + offset_mag * (0.3 * r3 - 0.1),
               end[1] - dy * 0.25 + offset_mag * (0.3 * r4 - 0.1))
        path = []
        for i in range(num_points):
            t = i / (num_points - 1)
            t = 1 - (1 - t) ** 1.5
            x, y = BezierCurve.cubic_bezier(t, start, cp1, cp2, end)
            path.append((x, y))
        return path

    @staticmethod
    def generate_with_overshoot(start_x, start_y, end_x, end_y, overshoot_px=15.0, num_points=50):
        start = (float(start_x), float(start_y))
        end = (float(end_x), float(end_y))
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dist = math.hypot(dx, dy)
        if dist < overshoot_px * 2:
            return BezierCurve.generate_path(start_x, start_y, end_x, end_y, num_points)
        nx, ny = dx / dist, dy / dist
        overshoot = (end[0] + nx * overshoot_px, end[1] + ny * overshoot_px)
        cp1 = (start[0] + dx * 0.3 + ny * random.uniform(10, 30),
               start[1] + dy * 0.3 - nx * random.uniform(10, 30))
        cp2 = (overshoot[0] + nx * random.uniform(5, 15) + ny * random.uniform(2, 8),
               overshoot[1] + ny * random.uniform(5, 15) - nx * random.uniform(2, 8))
        path = []
        for i in range(num_points):
            t = i / (num_points - 1)
            x, y = BezierCurve.cubic_bezier(t, start, cp1, cp2, overshoot)
            path.append((x, y))
        return path

    @staticmethod
    def compute_delays(path_length, base_duration=0.3, jitter=0.1):
        if path_length <= 1:
            return [base_duration]
        phases = [i / (path_length - 1) for i in range(path_length)]
        speed_mult = [1.0 + 0.5 * math.sin(p * math.pi) for p in phases]
        total_time = base_duration * path_length / 10
        delays = [total_time * m / sum(speed_mult) for m in speed_mult]
        delays = [d * (1 + random.uniform(-jitter, jitter)) for d in delays]
        return delays
