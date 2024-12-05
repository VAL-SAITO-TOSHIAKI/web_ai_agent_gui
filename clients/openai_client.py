# clients/openai_client.py

import logging
from typing import List, Tuple

from .claude_client import ClaudeClient
from .gpt4_client import GPT4Client
from config import Config

class OpenAIClient:
    def __init__(self, config: Config):
        self.claude_client = ClaudeClient(api_key=config.ANTHROPIC_API_KEY)
        self.gpt4_client = GPT4Client(
            api_key=config.AZURE_OPENAI_API_KEY,
            api_base=config.AZURE_OPENAI_API_BASE,
            api_version=config.AZURE_OPENAI_API_VERSION,
            deployment_name=config.DEPLOYMENT_GPT_NAME
        )

    def generate_actions(self, model: str, user_instruction: str, dom_elements: list = None) -> Tuple[List[dict], str]:
        if model == "Claude":
            return self.claude_client.generate_actions(user_instruction, dom_elements)
        elif model == "GPT4o":
            return self.gpt4_client.generate_actions(user_instruction, dom_elements)
        else:
            logging.error(f"サポートされていないモデル: {model}")
            return [], ""
