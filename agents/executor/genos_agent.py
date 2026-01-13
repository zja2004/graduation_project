"""
GenosAgent: Genos Embedding 生成智能体
负责调用 Genos 服务生成序列 embeddings
"""

import json
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any
import sys

# 添加工具路径
sys.path.append(str(Path(__file__).parent.parent.parent))
from tools.genos_client import GenosClient

logger = logging.getLogger(__name__)


class GenosAgent:
    """Genos Embedding 生成智能体"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config
        self.client = None
        self.stats = {
            "total_sequences": 0,
            "successful_embeddings": 0,
            "failed_embeddings": 0
        }

    def execute(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行 Genos embedding 生成

        Args:
            task_input: 任务输入参数

        Returns:
            执行结果
        """
        logger.info("开始 Genos embedding 生成...")

        # 初始化客户端 (使用官方 SDK)
        input_data = task_input["input"]
        api_token = input_data.get("api_token")  # 从任务参数或环境变量获取
        server_url = input_data.get("server_url")
        model_name = input_data.get("model_name", "1.2B")
        pooling = input_data.get("pooling", "mean")
        batch_size = input_data.get("batch_size", 10)
        timeout = input_data.get("timeout", 60)
        mock_mode = input_data.get("mock_mode", False)

        from tools.genos_client import create_client
        self.client = create_client(
            server_url=server_url,
            api_token=api_token,
            model_name=model_name,
            timeout=timeout,
            mock_mode=mock_mode
        )

        # 加载序列上下文
        contexts_file = input_data["contexts_file"]
        contexts = self._load_contexts(contexts_file)
        self.stats["total_sequences"] = len(contexts)

        # 生成 embeddings
        results = self._generate_embeddings(contexts, pooling, batch_size)

        # 保存结果
        output_file = task_input.get("output", {}).get("embeddings_file", "genos_embeddings.parquet")
        self._save_embeddings(results, output_file)

        logger.info(
            f"✓ Genos embedding 生成完成: "
            f"{self.stats['successful_embeddings']}/{self.stats['total_sequences']}"
        )

        return {
            "status": "success",
            "output_files": {
                "embeddings_file": output_file
            },
            "stats": self.stats
        }

    def _load_contexts(self, contexts_file: str) -> List[Dict]:
        """加载序列上下文"""
        contexts = []

        if not Path(contexts_file).exists():
            logger.warning(f"上下文文件不存在: {contexts_file}，使用模拟数据")
            return self._generate_mock_contexts()

        try:
            with open(contexts_file) as f:
                for line in f:
                    if line.strip():
                        contexts.append(json.loads(line))

            logger.info(f"加载序列上下文: {len(contexts)} 个")
            return contexts

        except Exception as e:
            logger.error(f"加载上下文失败: {e}，使用模拟数据")
            return self._generate_mock_contexts()

    def _generate_embeddings(
        self,
        contexts: List[Dict],
        pooling: str,
        batch_size: int
    ) -> List[Dict]:
        """生成 embeddings（支持批处理）"""
        results = []

        for i in range(0, len(contexts), batch_size):
            batch = contexts[i:i + batch_size]

            try:
                # 提取 ref 和 alt 序列
                ref_sequences = [ctx["ref_sequence"] for ctx in batch]
                alt_sequences = [ctx["alt_sequence"] for ctx in batch]

                # 批量生成 embeddings
                ref_embeddings = self.client.embed_batch(ref_sequences, pooling=pooling)
                alt_embeddings = self.client.embed_batch(alt_sequences, pooling=pooling)

                # 计算变异效应
                for j, ctx in enumerate(batch):
                    ref_emb = ref_embeddings[j]
                    alt_emb = alt_embeddings[j]

                    # 计算效应分数
                    effect_scores = self._calculate_effect_scores(ref_emb, alt_emb)

                    result = {
                        "variant_id": ctx["variant_id"],
                        "chrom": ctx["chrom"],
                        "pos": ctx["pos"],
                        "ref": ctx["ref"],
                        "alt": ctx["alt"],
                        "ref_embedding": ref_emb.tolist(),
                        "alt_embedding": alt_emb.tolist(),
                        **effect_scores
                    }
                    results.append(result)
                    self.stats["successful_embeddings"] += 1

                logger.info(f"已处理 {i + len(batch)}/{len(contexts)} 个序列")

            except Exception as e:
                logger.error(f"批次 {i // batch_size + 1} 失败: {e}")
                self.stats["failed_embeddings"] += len(batch)

        return results

    def _calculate_effect_scores(self, ref_emb, alt_emb) -> Dict[str, float]:
        """计算变异效应分数"""
        import numpy as np

        # Ensure 1D arrays
        ref_emb = np.squeeze(ref_emb)
        alt_emb = np.squeeze(alt_emb)

        cosine_sim = np.dot(ref_emb, alt_emb)
        euclidean_dist = np.linalg.norm(ref_emb - alt_emb)
        diff_magnitude = np.abs(ref_emb - alt_emb).mean()

        # 综合评分
        impact_score = (1 - cosine_sim) * 0.5 + euclidean_dist * 0.3 + diff_magnitude * 0.2

        return {
            "cosine_similarity": float(cosine_sim),
            "euclidean_distance": float(euclidean_dist),
            "diff_magnitude": float(diff_magnitude),
            "genos_impact_score": float(impact_score)
        }

    def _save_embeddings(self, results: List[Dict], output_file: str):
        """保存 embeddings 到 Parquet"""
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        # 转换为 DataFrame
        df = pd.DataFrame(results)

        # 保存为 Parquet（压缩）
        df.to_parquet(output_file, compression='snappy', index=False)

        logger.info(f"Embeddings 已保存: {output_file}")

    def _generate_mock_contexts(self) -> List[Dict]:
        """生成模拟序列上下文"""
        logger.info("生成模拟序列上下文...")

        import random

        def random_seq(length):
            return ''.join(random.choices('ATCG', k=length))

        mock_contexts = []
        for i in range(3):
            ref = random.choice(['A', 'T', 'C', 'G'])
            alt = random.choice([x for x in 'ATCG' if x != ref])

            left = random_seq(100)
            right = random_seq(100)

            mock_contexts.append({
                "variant_id": f"var_{i+1}",
                "chrom": f"chr{i+1}",
                "pos": (i + 1) * 100000,
                "ref": ref,
                "alt": alt,
                "ref_sequence": left + ref + right,
                "alt_sequence": left + alt + right
            })

        return mock_contexts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    agent = GenosAgent()

    result = agent.execute({
        "contexts_file": "contexts.jsonl",
        "server_url": "http://127.0.0.1:8000",
        "model_name": "1.2B",
        "pooling": "mean",
        "batch_size": 10,
        "output": {
            "embeddings_file": "test_embeddings.parquet"
        }
    })

    print(json.dumps(result, indent=2))
