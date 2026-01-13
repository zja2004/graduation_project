"""
变异效应评分 Agent
基于 Genos embeddings 或 LLM (DeepSeek) 计算变异的致病性评分
"""

import json
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, List
import sys

# 添加工具路径
sys.path.append(str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)


class ScoringAgent:
    """变异效应评分 Agent"""

    def __init__(self, config: Dict):
        """
        初始化评分 Agent

        Args:
            config: 配置字典，包含评分方法和阈值
        """
        self.config = config
        self.scoring_config = config.get("scoring", {})
        self.method = self.scoring_config.get("method", "genos_embedding")
        self.weights = self.scoring_config.get("genos_weights", {})
        self.thresholds = self.scoring_config.get("thresholds", {})
        
        # DeepSeek Config
        self.deepseek_config = config.get("deepseek", {})
        self.deepseek_client = None

        logger.info(f"✓ 评分 Agent 初始化: method={self.method}")

    def execute(self, task: Dict) -> Dict:
        """
        执行变异效应评分任务

        Args:
            task: 任务字典，包含 embeddings_file 和 output 配置

        Returns:
            执行结果字典
        """
        try:
            embeddings_file = task["input"]["embeddings_file"]
            output_file = task["output"]["scores_file"]

            logger.info(f"→ 开始变异效应评分: {embeddings_file}")

            # 读取 embeddings 数据
            # 注意: 即使是用 LLM，我们可能也依赖 VCF 信息。
            # 这里 embeddings 文件包含了 metadata (chr, pos, ref, alt)
            embeddings_df = pd.read_parquet(embeddings_file)
            logger.info(f"  加载 {len(embeddings_df)} 个变异记录")

            # 计算评分
            scores = []
            
            # 初始化 DeepSeek 客户端 (如果需要)
            if self.method == "llm_deepseek":
                try:
                    from tools.deepseek_client import DeepSeekClient
                    self.deepseek_client = DeepSeekClient(
                        api_key=self.deepseek_config.get("api_key"),
                        model=self.deepseek_config.get("model", "deepseek-chat"),
                        base_url=self.deepseek_config.get("base_url", "https://api.deepseek.com")
                    )
                except Exception as e:
                    logger.error(f"DeepSeek 客户端初始化失败: {e}")
                    raise

            for _, row in embeddings_df.iterrows():
                if self.method == "llm_deepseek":
                    score = self._score_with_deepseek(row)
                else:
                    score = self._calculate_score(row)
                scores.append(score)

            # 保存结果
            scores_df = pd.DataFrame(scores)
            self._save_scores(scores_df, output_file)
            logger.info(f"✓ 评分完成: {len(scores_df)} 个变异 → {output_file}")

            return {
                "status": "success",
                "scores_count": len(scores_df),
                "output_file": str(output_file)
            }

        except Exception as e:
            logger.error(f"✗ 评分失败: {e}")
            raise

    def _score_with_deepseek(self, row: pd.Series) -> Dict:
        """使用 DeepSeek LLM 对变异进行评分"""
        variant_desc = f"{row['chrom']}:{row['pos']} {row['ref']}->{row['alt']}"
        
        # 构造 Prompt
        prompt = f"""
        你是一个遗传学专家。请评估以下人类基因组变异的致病性。
        
        变异: {variant_desc}
        
        请输出一个 JSON 格式的回复，包含以下字段:
        - pathogenicity_score (0-1之间的浮点数，0为良性，1为致病)
        - explanation (简短解释，不超过50字)
        - impact_level (HIGH, MODERATE, LOW)
        
        只输出 JSON，不要包含其他文本。
        """
        
        fallback_score = {
            "variant_id": row["variant_id"],
            "chrom": row["chrom"],
            "pos": row["pos"],
            "ref": row["ref"],
            "alt": row["alt"],
            "final_score": 0.5,
            "impact_level": "MODERATE",
            "explanation": "LLM 调用失败，使用默认值"
        }

        try:
            logger.info(f"DeepSeek 评分: {variant_desc}")
            response = self.deepseek_client.chat_completion([
                {"role": "user", "content": prompt}
            ])
            
            # 解析 JSON
            # 简单的清理逻辑，防止 Markdown 代码块干扰
            content = response.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            result = json.loads(content)
            
            score = float(result.get("pathogenicity_score", 0.5))
            impact = result.get("impact_level", "MODERATE").upper()
            
            if impact not in ["HIGH", "MODERATE", "LOW"]:
                 # 重新根据分数校准
                 if score >= 0.7: impact = "HIGH"
                 elif score >= 0.4: impact = "MODERATE"
                 else: impact = "LOW"

            return {
                "variant_id": row["variant_id"],
                "chrom": row["chrom"],
                "pos": row["pos"],
                "ref": row["ref"],
                "alt": row["alt"],
                "final_score": score,
                "impact_level": impact,
                "explanation": result.get("explanation", "")
            }

        except Exception as e:
            logger.warning(f"DeepSeek 评分失败 ({variant_desc}): {e}")
            return fallback_score

    def _calculate_score(self, row: pd.Series) -> Dict:
        """计算单个变异的综合评分 (Genos Embedding 方法)"""
        # 提取 embedding 差异指标
        cosine_sim = row.get("cosine_similarity", 0.0)
        euclidean_dist = row.get("euclidean_distance", 0.0)
        diff_magnitude = row.get("diff_magnitude", 0.0)
        impact_score = row.get("impact_score", 0.0)

        # 使用配置的权重计算综合评分
        w_cos = self.weights.get("cosine_similarity", -0.5)
        w_euc = self.weights.get("euclidean_distance", 0.3)
        w_diff = self.weights.get("diff_magnitude", 0.2)

        # 综合评分
        combined_score = (
            w_cos * (1 - cosine_sim) +  # 相似度越低，影响越大
            w_euc * euclidean_dist +
            w_diff * diff_magnitude
        )

        # 归一化到 [0, 1]
        final_score = min(max(combined_score, 0.0), 1.0)

        # 分类
        impact_level = self._classify_impact(final_score)

        return {
            "variant_id": row["variant_id"],
            "chrom": row["chrom"],
            "pos": row["pos"],
            "ref": row["ref"],
            "alt": row["alt"],
            "cosine_similarity": cosine_sim,
            "euclidean_distance": euclidean_dist,
            "diff_magnitude": diff_magnitude,
            "raw_impact_score": impact_score,
            "combined_score": combined_score,
            "final_score": final_score,
            "impact_level": impact_level
        }

    def _classify_impact(self, score: float) -> str:
        """根据评分分类影响等级"""
        high = self.thresholds.get("high_impact", 0.7)
        moderate = self.thresholds.get("moderate_impact", 0.4)

        if score >= high:
            return "HIGH"
        elif score >= moderate:
            return "MODERATE"
        else:
            return "LOW"

    def _save_scores(self, scores_df: pd.DataFrame, output_file: str):
        """保存评分结果"""
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        scores_df.to_csv(output_file, sep='\t', index=False)
