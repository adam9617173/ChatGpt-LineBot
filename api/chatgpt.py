from api.prompt import Prompt

import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

class ChatGPT:
    def __init__(self):
        self.prompt = Prompt()

        # 設定模型，預設使用最新的 GPT-4o
        self.model = "gpt-4o"  # 🚀 預設使用 GPT-4o（最強最快）

        # 👇 以下舊模型已註解，僅供參考
        # self.model = os.getenv("OPENAI_MODEL", default="text-davinci-003")  # GPT-3
        # self.model = os.getenv("OPENAI_MODEL", default="gpt-3.5-turbo")  # GPT-3.5
        # self.model = os.getenv("OPENAI_MODEL", default="gpt-4")  # 舊版 GPT-4

        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", default=0))
        self.frequency_penalty = float(os.getenv("OPENAI_FREQUENCY_PENALTY", default=0))
        self.presence_penalty = float(os.getenv("OPENAI_PRESENCE_PENALTY", default=0.6))
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", default=2000))

        # 🚀 顯示當前使用的 GPT 模型
        print(f"🚀 當前使用的 GPT 模型: {self.model}")

    def get_response(self):
        """使用 OpenAI API 取得 AI 回應"""
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[{"role": "user", "content": self.prompt.generate_prompt()}],
            temperature=self.temperature,
            frequency_penalty=self.frequency_penalty,
            presence_penalty=self.presence_penalty,
            max_tokens=self.max_tokens
        )
        return response['choices'][0]['message']['content'].strip()

    def add_msg(self, text):
        """新增訊息到對話記錄"""
        self.prompt.add_msg(text)
