import logging
from config import Config
from clients.openai_client import OpenAIClient
from controllers.playwright_controller import PlaywrightController
from gui.web_agent_gui import WebAgentGUI
from utils.logger import setup_logging

def main():
    try:
        config = Config()
    except ValueError as e:
        print(f"設定エラー: {e}")
        return

    setup_logging()

    openai_client = OpenAIClient(config)

    try:
        playwright_controller = PlaywrightController()
    except Exception as e:
        logging.error(f"Playwrightの初期化に失敗しました: {e}")
        print(f"Playwrightの初期化に失敗しました: {e}")
        return

    gui = WebAgentGUI(openai_client, playwright_controller)
    gui.start()

if __name__ == "__main__":
    main()
