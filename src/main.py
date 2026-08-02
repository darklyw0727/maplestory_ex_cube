import argparse
import logging
import sys
import threading
import time
from pathlib import Path

from . import hotkey as hotkey_mod
from .config import load_config
from .controller import AbortError, Controller
from .window import FailSafeAbort, GameWindow, ensure_dpi_aware
from . import ocr


def setup_logging(cfg):
    if cfg.log_lv == "debug":
        log_lv=logging.DEBUG
    else:
        log_lv=logging.INFO

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / time.strftime("run_%Y%m%d_%H%M%S.log")
    logging.basicConfig(
        level=log_lv,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )
    return log_path


def main():
    ensure_dpi_aware()

    parser = argparse.ArgumentParser(description="自動洗珍貴/絕對/萌獸/恢復附加方塊")
    parser.add_argument("--config", default="config.json", help="設定檔路徑")
    parser.add_argument("--yes", action="store_true", help="略過開始前的確認提示")
    args = parser.parse_args()

    cfg = load_config(args.config)

    log_path = setup_logging(cfg)
    log = logging.getLogger("auto_ex_cube")

    ocr.configure(cfg.ocr_lang)

    log.info("設定: 目標潛能=%s, 方塊上限=%s, dry_run=%s", cfg.target_potentials, cfg.max_cubes or "不限制", cfg.dry_run)
    log.info("Log 檔案: %s", log_path)

    if not args.yes:
        print("=" * 60)
        print("即將開始自動操作滑鼠使用方塊。")
        print("請確認遊戲已開啟、已進入潛在能力面板並選擇了「珍貴附加方塊」「絕對附加方塊」")
        print("「萌獸方塊」或「恢復附加方塊」其中一種，程式會自動判斷走哪個流程。")
        print("執行期間若要緊急中止，將滑鼠移到螢幕左上角、按 Ctrl+C，")
        if cfg.stop_hotkey:
            print(f"或按下熱鍵 {cfg.stop_hotkey}(不用切換視窗，將於這一輪結束後停止)。")
        print("=" * 60)
        resp = input("輸入 y 開始執行: ").strip().lower()
        if resp != "y":
            print("已取消")
            return

    for i in range(3, 0, -1):
        print(f"{i}...")
        time.sleep(1)

    stop_event = threading.Event()

    def _on_hotkey():
        log.info("偵測到停止熱鍵「%s」，將於這一輪結束後停止", cfg.stop_hotkey)
        stop_event.set()

    hotkey_handle = hotkey_mod.register(cfg.stop_hotkey, _on_hotkey)
    if hotkey_handle is not None:
        log.info("執行期間按下 %s 可請求停止(不用切換視窗，將於目前這輪結束後收尾)", cfg.stop_hotkey)

    window = GameWindow(cfg.window_title)
    controller = Controller(cfg, window, stop_event=stop_event)

    try:
        result = controller.run()
        log.info("流程結束，結果: %s，共使用 %d 個方塊", result, controller.used_cubes)
    except FailSafeAbort as e:
        log.warning("使用者中止: %s", e)
    except AbortError as e:
        log.error("流程中止: %s", e)
    except KeyboardInterrupt:
        log.warning("使用者按下 Ctrl+C，已中止")
    except Exception:
        log.exception("發生未預期錯誤")
        raise
    finally:
        hotkey_mod.unregister(hotkey_handle)


if __name__ == "__main__":
    main()
