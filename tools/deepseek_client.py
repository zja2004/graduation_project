"""
DeepSeek API Client
"""

import requests
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class DeepSeekClient:
    """DeepSeek API 客户端"""

    def __init__(self, api_key: str, model: str = "deepseek-chat", base_url: str = "https://api.deepseek.com"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def chat_completion(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> str:
        """
        调用 DeepSeek Chat API
        """
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 1024
            }
            
            response = requests.post(f"{self.base_url}/chat/completions", headers=self.headers, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"DeepSeek API 请求失败: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"DeepSeek API 调用错误: {e}")
            raise
