# clients/gpt4_client.py

import json
import re
import logging
from langchain.chat_models import AzureChatOpenAI
from langchain.schema import HumanMessage
from typing import List, Tuple

class GPT4Client:
    def __init__(self, api_key: str, api_base: str, api_version: str, deployment_name: str):
        self.llm = AzureChatOpenAI(
            deployment_name=deployment_name,
            openai_api_key=api_key,
            openai_api_base=api_base,
            openai_api_version=api_version,
        )

    def generate_actions(self, user_instruction: str, dom_elements: list = None) -> Tuple[List[dict], str]:
        dom_elements_str = json.dumps(dom_elements, ensure_ascii=False) if dom_elements else 'なし'
        
        prompt = f"""
        以下のユーザー指示に基づいて、必要なウェブ操作を純粋なJSON形式で出力してください。コードブロック（```json と ```）は使用しないでください。
        ユーザー指示: {user_instruction}
        DOM要素:
        {dom_elements_str}
        出力形式:
        [
            {{"action": "ACTION_TYPE", "selector": "CSS_SELECTOR", "value": "VALUE"}}
        ]
        ACTION_TYPEは "CLICK", "TYPE", "NAVIGATE", "SCREENSHOT" のいずれかとします。
        """

        messages = [HumanMessage(content=prompt)]
        try:
            logging.debug("Azure OpenAIへのリクエストを送信します。")
            response = self.llm(messages)
            gpt_response = response.content.strip()
            logging.debug(f"Azure OpenAIからの生のレスポンステキスト: {gpt_response}")
            if not gpt_response:
                logging.error("Azure OpenAIからの応答が空です。")
                return [], ""
            gpt_response = re.sub(r'^```json\s*', '', gpt_response)
            gpt_response = re.sub(r'```$', '', gpt_response).strip()
            actions = json.loads(gpt_response)
            logging.debug(f"生成されたアクション: {actions}")
            return actions, gpt_response
        except json.JSONDecodeError:
            logging.error(f"JSON解析エラー: {gpt_response}")
            return [], ""
        except Exception as e:
            logging.error(f"Azure OpenAI エラー: {e}")
            return [], ""
