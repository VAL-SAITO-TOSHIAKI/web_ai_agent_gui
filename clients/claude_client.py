# clients/claude_client.py

import json
import re
import logging
import anthropic
from typing import List, Tuple

class ClaudeClient:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate_actions(self, user_instruction: str, dom_elements: list = None) -> Tuple[List[dict], str]:
        dom_elements_str = json.dumps(dom_elements, ensure_ascii=False) if dom_elements else 'なし'

        prompt = f"""
        以下のユーザー指示に基づいて、必要なウェブ操作を純粋なJSON形式で出力してください。コードブロック（```json と ```）は使用しないでください。
        ユーザー指示: {user_instruction}
        DOM要素:
        {dom_elements_str}
        出力形式は直接オブジェクトのリストで、各オブジェクトは辞書型であることを保証してください。
        [
            {{"action": "ACTION_TYPE", "selector": "CSS_SELECTOR", "value": "VALUE"}}
        ]
        ACTION_TYPEは "CLICK", "TYPE", "NAVIGATE", "SCREENSHOT" のいずれかとします。
        """

        try:
            logging.debug("Claude APIへのリクエストを送信します。")
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=5000,
                temperature=0.0,
                system="あなたはウェブ操作を生成するアシスタントです。",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            logging.debug(f"Claude APIからのレスポンス: {response}")

            if isinstance(response.content, list) and len(response.content) > 0:
                gpt_response = response.content[0].text.strip()
            else:
                logging.error("予期しないレスポンス形式です。")
                return [], ""

            logging.debug(f"Claude APIからの生のレスポンステキスト: {gpt_response}")

            if not gpt_response:
                logging.error("Claude APIからの応答が空です。")
                return [], ""

            gpt_response = re.sub(r'^```json\s*', '', gpt_response)
            gpt_response = re.sub(r'```$', '', gpt_response).strip()

            actions = json.loads(gpt_response)
            logging.debug(f"生成されたアクション: {actions}")

            if isinstance(actions, list) and all(isinstance(action, dict) for action in actions):
                return actions, gpt_response
            else:
                logging.error("アクションの形式が不正です。期待する形式はリスト内の辞書です。")
                return [], ""

        except json.JSONDecodeError:
            logging.error(f"JSON解析エラー: {gpt_response}")
            return [], ""
        except Exception as e:
            logging.error(f"Claude API エラー: {e}")
            return [], ""
