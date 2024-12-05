# utils/logger.py

import logging

def setup_logging():
    logging.basicConfig(
        filename='web_agent.log',
        level=logging.DEBUG,  # デバッグレベルに設定
        format='%(asctime)s:%(levelname)s:%(message)s'
    )
    logging.info("WebAgentAIアプリケーションが起動しました。")
