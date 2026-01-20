"""
DeepSeek API Client - 增强版
支持基因变异通俗化解释生成
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
        logger.info(f"✓ DeepSeek 客户端初始化: 模型 {self.model}")

    def chat_completion(self, messages: List[Dict[str, str]], temperature: float = 0.1, max_tokens: int = 1024) -> str:
        """
        调用 DeepSeek Chat API
        """
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
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

    def generate_gene_explanation(self, gene_name: str, variant_info: Dict) -> str:
        """
        生成基因变异的通俗化解释（小白友好）

        Args:
            gene_name: 基因名称（如 BRAF, TP53）
            variant_info: 变异信息字典，包含 chrom, pos, ref, alt, impact_level 等

        Returns:
            通俗化解释文本
        """
        chrom = variant_info.get("chrom", "未知")
        pos = variant_info.get("pos", "未知")
        ref = variant_info.get("ref", "未知")
        alt = variant_info.get("alt", "未知")
        impact_level = variant_info.get("impact_level", "未知")

        prompt = f"""
请用**简单易懂**的语言解释以下基因变异信息，面向非医学专业人士：

**基因**: {gene_name}
**变异位置**: {chrom}:{pos}
**变异类型**: {ref} → {alt}
**风险等级**: {impact_level}

请按以下结构回答（每部分2-3句话，总共200字以内）：

### 1. 基因的作用
{gene_name} 基因在人体内负责什么功能？就像身体里的哪个零件？

### 2. 蛋白质的变化
这个变异可能导致什么蛋白质发生变化？这个蛋白质原本做什么工作？变异后会怎样？

### 3. 可能的健康影响
这种变异与哪些疾病或症状相关？需要注意什么？

**注意**：
- 避免专业术语，必须使用时用括号解释
- 使用类比和比喻（如：基因像"说明书"，蛋白质像"工人"）
- 保持客观，说明"可能"而非"一定"
- 如果不确定，明确说明"需要进一步检查"
"""

        try:
            messages = [
                {
                    "role": "system",
                    "content": "你是一位经验丰富的遗传咨询师，擅长用通俗易懂的语言向非专业人士解释基因检测结果。你的回答要像在跟一个没有医学背景的朋友聊天一样。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            explanation = self.chat_completion(messages, temperature=0.3, max_tokens=600)
            logger.debug(f"✓ 生成解释: {gene_name}")
            return explanation

        except Exception as e:
            logger.error(f"✗ 生成基因解释失败: {e}")
            return self._get_fallback_explanation(gene_name)

    def _get_fallback_explanation(self, gene_name: str) -> str:
        """API 失败时的后备解释"""
        return f"""
### 1. 基因的作用
{gene_name} 基因在人体内有重要作用，但具体功能信息暂时无法获取。建议咨询遗传咨询师了解更多。

### 2. 蛋白质的变化
该变异可能影响由此基因编码的蛋白质的结构或功能。蛋白质就像身体里的"工人"，基因变异可能导致"工人"工作效率降低或功能异常。

### 3. 可能的健康影响
具体健康影响需要结合临床症状和家族史进行综合评估。建议咨询专业医生或遗传咨询师进行详细解读。
"""


def create_deepseek_client(config: Dict) -> DeepSeekClient:
    """
    从配置创建 DeepSeek 客户端

    Args:
        config: 配置字典，包含 deepseek 配置

    Returns:
        DeepSeekClient 实例
    """
    deepseek_config = config.get("deepseek", {})
    return DeepSeekClient(
        api_key=deepseek_config.get("api_key"),
        model=deepseek_config.get("model", "deepseek-chat"),
        base_url=deepseek_config.get("base_url", "https://api.deepseek.com")
    )
