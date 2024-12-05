import os
from dotenv import load_dotenv

class Config:
    def __init__(self, env_path='.env'):
        load_dotenv(env_path)
        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
        self.AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
        self.AZURE_OPENAI_API_BASE = os.getenv("AZURE_OPENAI_API_BASE")
        self.AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
        self.DEPLOYMENT_GPT_NAME = os.getenv("DEPLOYMENT_GPT_NAME")

        self.validate()

    def validate(self):
        missing = [var for var in ["ANTHROPIC_API_KEY", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_API_BASE", 
                                   "AZURE_OPENAI_API_VERSION", "DEPLOYMENT_GPT_NAME"]
                   if not getattr(self, var)]
        if missing:
            raise ValueError(f"必要な環境変数が設定されていません: {', '.join(missing)}")
