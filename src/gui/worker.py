"""在背景執行緒跑自動化流程(Controller.run())，並把 log 訊息橋接到 Qt signal。"""
import logging
import threading

from PyQt6.QtCore import QThread, pyqtSignal

from src.config import load_config
from src.controller import AbortError, Controller
from src.window import FailSafeAbort, GameWindow


class _QtLogHandler(logging.Handler):
    def __init__(self, emit_fn):
        super().__init__()
        self._emit_fn = emit_fn

    def emit(self, record):
        self._emit_fn(self.format(record))


class AutomationWorker(QThread):
    log_line = pyqtSignal(str)
    finished_run = pyqtSignal(str)  # "success" / "limit_reached" / "empty" / "stopped" / "failsafe"
    failed = pyqtSignal(str)

    def __init__(self, config_path="config.json", parent=None):
        super().__init__(parent)
        self.config_path = config_path
        self.stop_event = threading.Event()

    def request_stop(self):
        self.stop_event.set()

    def run(self):
        logger = logging.getLogger("auto_ex_cube")
        handler = _QtLogHandler(self.log_line.emit)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(handler)
        prev_level = logger.level
        try:
            cfg = load_config(self.config_path)
            logger.setLevel(logging.DEBUG if cfg.log_lv == "debug" else logging.INFO)

            window = GameWindow(cfg.window_title)
            controller = Controller(cfg, window, stop_event=self.stop_event)
            result = controller.run()
            self.finished_run.emit(result)
        except FailSafeAbort as e:
            logger.warning("使用者中止: %s", e)
            self.finished_run.emit("failsafe")
        except AbortError as e:
            logger.error("流程中止: %s", e)
            self.failed.emit(str(e))
        except Exception as e:  # noqa: BLE001 - 需要把任何未預期例外都回報到UI
            logger.exception("發生未預期錯誤")
            self.failed.emit(str(e))
        finally:
            logger.removeHandler(handler)
            logger.setLevel(prev_level)
