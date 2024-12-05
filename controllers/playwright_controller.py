# controllers/playwright_controller.py

import logging
import subprocess
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from typing import List, Callable, Optional

class PlaywrightController:
    def __init__(self):
        self.install_browsers()

    def install_browsers(self):
        try:
            subprocess.run(["playwright", "install"], check=True)
            logging.info("Playwrightのブラウザをインストールしました。")
        except subprocess.CalledProcessError as e:
            logging.error(f"Playwrightブラウザのインストールに失敗しました: {e}")
            raise

    def perform_actions(self, actions: List[dict], url: Optional[str] = None, callback: Optional[Callable] = None):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            try:
                if url:
                    logging.info(f"URLにアクセスします: {url}")
                    page.goto(url, timeout=60000)
                    page.wait_for_load_state('networkidle', timeout=60000)
                    logging.info(f"URLにアクセスしました: {url}")
            
                for index, action in enumerate(actions, start=1):
                    act = action.get("action")
                    sel = action.get("selector")
                    val = action.get("value")
                    code_snippet = ""

                    try:
                        if act == "NAVIGATE" and val:
                            logging.info(f"ナビゲートします: {val}")
                            page.goto(val, timeout=60000)
                            page.wait_for_load_state('networkidle', timeout=60000)
                            logging.info(f"ナビゲートしました: {val}")
                            time.sleep(2)
                            code_snippet = f'page.goto("{val}")'
                            if callback:
                                callback(index, act, sel, val, code_snippet, success=True)
                        elif act == "CLICK" and sel:
                            logging.info(f"クリックします: {sel}")
                            page.wait_for_selector(sel, timeout=60000)
                            page.click(sel, timeout=60000)
                            logging.info(f"クリックしました: {sel}")
                            time.sleep(1)
                            code_snippet = f'page.click("{sel}")'
                            if callback:
                                callback(index, act, sel, val, code_snippet, success=True)
                        elif act == "TYPE" and sel:
                            logging.info(f"タイプします: '{val}' into {sel}")
                            page.wait_for_selector(sel, timeout=60000)
                            page.fill(sel, val, timeout=60000)
                            logging.info(f"タイプしました: '{val}' into {sel}")
                            time.sleep(1)
                            code_snippet = f'page.fill("{sel}", "{val}")'
                            if callback:
                                callback(index, act, sel, val, code_snippet, success=True)
                        elif act == "SCREENSHOT":
                            path = val or "screenshot.png"
                            page.screenshot(path=path)
                            logging.info(f"スクリーンショットを保存しました: {path}")
                            code_snippet = f'page.screenshot(path="{path}")'
                            if callback:
                                callback(index, act, sel, val, code_snippet, success=True)
                        else:
                            logging.warning(f"未知のアクション: {action}")
                            if callback:
                                callback(index, act, sel, val, code_snippet, success=False)
                    except PlaywrightTimeoutError:
                        logging.error(f"タイムアウトエラー: アクション '{act}' のセレクタ '{sel}' が見つかりませんでした。")
                        if callback:
                            callback(index, act, sel, val, code_snippet, success=False)
                    except Exception as e:
                        logging.error(f"{act} エラー: {e}")
                        if callback:
                            callback(index, act, sel, val, code_snippet, success=False)
            finally:
                browser.close()
                logging.info("ブラウザを閉じました。")
