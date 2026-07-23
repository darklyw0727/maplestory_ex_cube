import argparse
import logging
import sys
import time
from pathlib import Path

from .config import load_config
from .controller import AbortError, Controller
from .window import FailSafeAbort, GameWindow
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
    parser = argparse.ArgumentParser(description="自動洗珍貴/絕對附加方塊")
    parser.add_argument("--config", default="config.json", help="設定檔路徑")
    parser.add_argument("--yes", action="store_true", help="略過開始前的確認提示")
    args = parser.parse_args()

    cfg = load_config(args.config)

    log_path = setup_logging(cfg)
    log = logging.getLogger("auto_shine_cube")

    ocr.configure(cfg.ocr_lang)

    log.info("設定: 目標潛能=%s, 方塊上限=%s, dry_run=%s", cfg.target_potentials, cfg.max_cubes or "不限制", cfg.dry_run)
    log.info("Log 檔案: %s", log_path)

    if not args.yes:
        print("=" * 60)
        print("即將開始自動操作滑鼠使用珍貴附加方塊或絕對附加方塊。")
        print("請確認遊戲已開啟、已進入潛在能力面板並選擇了珍貴附加方塊或絕對附加方塊。")
        print("執行期間若要緊急中止，將滑鼠移到螢幕左上角，或按 Ctrl+C。")
        print("=" * 60)
        resp = input("輸入 y 開始執行: ").strip().lower()
        if resp != "y":
            print("已取消")
            return

    for i in range(3, 0, -1):
        print(f"{i}...")
        time.sleep(1)

    window = GameWindow(cfg.window_title)
    controller = Controller(cfg, window)

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


if __name__ == "__main__":
    main()
