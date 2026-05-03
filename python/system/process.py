"""Process detection — check if programs are running."""
from typing import Optional


class ProcessDetector:
    """Detect and interact with running system processes using psutil."""

    def __init__(self):
        self._psutil_available = False
        try:
            import psutil
            self._psutil = psutil
            self._psutil_available = True
        except ImportError:
            pass

    def is_running(self, process_name: str, exact: bool = False) -> bool:
        if not self._psutil_available:
            return False
        for proc in self._psutil.process_iter(['name']):
            try:
                name = proc.info['name']
                if name is None:
                    continue
                if exact:
                    if name.lower() == process_name.lower():
                        return True
                else:
                    if process_name.lower() in name.lower():
                        return True
            except (self._psutil.NoSuchProcess, self._psutil.AccessDenied):
                continue
        return False

    def find_processes(self, process_name: str) -> list[dict]:
        if not self._psutil_available:
            return []
        results = []
        for proc in self._psutil.process_iter(['pid', 'name', 'create_time',
                                                'cpu_percent', 'memory_percent']):
            try:
                if process_name.lower() in (proc.info['name'] or '').lower():
                    results.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'create_time': proc.info['create_time'],
                        'cpu_percent': proc.info['cpu_percent'],
                        'memory_percent': proc.info['memory_percent'],
                    })
            except (self._psutil.NoSuchProcess, self._psutil.AccessDenied):
                continue
        return results

    def wait_for_process(self, process_name: str, timeout: float = 30.0, poll_interval: float = 0.5) -> bool:
        import time
        start = time.time()
        while time.time() - start < timeout:
            if self.is_running(process_name):
                return True
            time.sleep(poll_interval)
        return False

    def get_foreground_process(self) -> Optional[str]:
        try:
            import psutil
            import os
            if os.name == 'nt':
                import win32gui
                import win32process
                hwnd = win32gui.GetForegroundWindow()
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc = psutil.Process(pid)
                return proc.name()
            else:
                from subprocess import check_output
                output = check_output(['xdotool', 'getactivewindow', 'getpid']).strip()
                pid = int(output)
                proc = psutil.Process(pid)
                return proc.name()
        except Exception:
            return None
