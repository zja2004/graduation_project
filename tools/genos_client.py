"""
Genos 客户端工具
默认连接本地 Genos 服务 (http://127.0.0.1:8000)，
可通过环境变量 GENOS_SERVER_URL 覆盖。
"""

import os
import requests
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)
DEFAULT_SERVER_URL = os.environ.get("GENOS_SERVER_URL", "http://127.0.0.1:8000")


class GenosClient:
    """Genos 本地服务客户端"""

    def __init__(self, server_url: str = DEFAULT_SERVER_URL, model_name: str = "1.2B", timeout: int = 60, mock_mode: bool = False, api_token: str = None, **kwargs):
        """
        初始化 Genos 客户端

        Args:
            server_url: Genos 服务地址
            model_name: 模型名称 (1.2B 或 10B)
            timeout: 请求超时时间
            mock_mode: 是否使用模拟模式 (默认 False)
            api_token: API Token
        """
        self.server_url = server_url.rstrip('/')
        self.model_name = model_name
        self.timeout = timeout
        self.mock_mode = mock_mode
        self.api_token = api_token
        self.session = requests.Session()

        logger.info(f"✓ Genos 客户端初始化: {self.server_url}, 模型: {self.model_name}, 模拟模式: {self.mock_mode}")

    def embed(
        self,
        sequence: str,
        pooling: str = "mean",
        normalize: bool = True
    ) -> np.ndarray:
        """
        生成序列的 embedding

        Args:
            sequence: DNA 序列
            pooling: 池化方法 (mean/max/last/none)
            normalize: 是否归一化

        Returns:
            embedding 向量 (numpy array)
        """
        if self.mock_mode:
            # 返回随机 embedding (维度 1024 用作测试)
            # 使用 seed 以保证确定性? 不用了，随机即可
            emb = np.random.rand(1024).astype(np.float32)
            if normalize:
                emb = emb / np.linalg.norm(emb)
            return emb

        try:
            payload = {
                "sequence": sequence,
                "model_name": self.model_name,
                "pooling_method": pooling
            }

            response = self.session.post(
                f"{self.server_url}/extract",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()

            # 提取 embedding
            if result.get("success"):
                embedding = np.array(result["result"]["embedding"])
            else:
                raise ValueError(f"API 返回错误: {result.get('error', 'Unknown error')}")

            # 归一化
            if normalize and embedding.size > 0:
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = embedding / norm

            logger.debug(f"生成 embedding: shape={embedding.shape}, mean={embedding.mean():.4f}")
            return embedding

        except Exception as e:
            logger.error(f"Embedding 生成失败: {e}")
            raise

    def embed_batch(
        self,
        sequences: List[str],
        pooling: str = "mean",
        normalize: bool = True
    ) -> np.ndarray:
        """
        批量生成 embeddings

        Args:
            sequences: DNA 序列列表
            pooling: 池化方法
            normalize: 是否归一化

        Returns:
            embeddings 矩阵 (num_sequences, embedding_dim)
        """
        embeddings = []
        for seq in sequences:
            try:
                emb = self.embed(seq, pooling=pooling, normalize=normalize)
                embeddings.append(emb)
            except Exception as e:
                logger.warning(f"序列 embedding 失败: {e}")
                # 使用零向量填充
                if len(embeddings) > 0:
                    embeddings.append(np.zeros_like(embeddings[0]))
                else:
                    embeddings.append(np.zeros(1024)) # fallback dimension

        embeddings = np.array(embeddings)
        logger.info(f"批量生成 {len(embeddings)} 个 embeddings")
        return embeddings

    def predict_variant_effect(
        self,
        ref_sequence: str,
        alt_sequence: str,
        pooling: str = "mean"
    ) -> Dict[str, float]:
        """
        预测变异效应（通过 embedding 差异）

        Args:
            ref_sequence: 参考序列
            alt_sequence: 变异序列
            pooling: 池化方法

        Returns:
            效应分数字典
        """
        try:
            # 生成两个 embeddings
            ref_emb = self.embed(ref_sequence, pooling=pooling, normalize=True)
            alt_emb = self.embed(alt_sequence, pooling=pooling, normalize=True)

            # 计算多种距离度量
            cosine_sim = np.dot(ref_emb, alt_emb)
            euclidean_dist = np.linalg.norm(ref_emb - alt_emb)
            diff_magnitude = np.abs(ref_emb - alt_emb).mean()

            # 综合评分（距离越大，影响越大）
            impact_score = (1 - cosine_sim) * 0.5 + euclidean_dist * 0.3 + diff_magnitude * 0.2

            return {
                "cosine_similarity": float(cosine_sim),
                "euclidean_distance": float(euclidean_dist),
                "diff_magnitude": float(diff_magnitude),
                "impact_score": float(impact_score),
                "ref_embedding_mean": float(ref_emb.mean()),
                "alt_embedding_mean": float(alt_emb.mean())
            }

        except Exception as e:
            logger.error(f"变异效应预测失败: {e}")
            raise

    def predict_next_bases(
        self,
        sequence: str,
        predict_length: int = 100
    ) -> Dict:
        """
        预测 DNA 序列的下游碱基

        Args:
            sequence: 输入序列
            predict_length: 预测长度

        Returns:
            预测结果字典
        """
        if self.mock_mode:
            return {
                "predicted_sequence": "A" * predict_length,
                "probabilities": []
            }

        try:
            payload = {
                "sequence": sequence,
                "model_name": self.model_name,
                "predict_length": predict_length
            }

            response = self.session.post(
                f"{self.server_url}/predict",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()

            if result.get("success"):
                return result["result"]
            else:
                raise ValueError(f"API 返回错误: {result.get('error', 'Unknown error')}")

        except Exception as e:
            logger.error(f"碱基预测失败: {e}")
            raise


def create_client(
    server_url: Optional[str] = None,
    model_name: str = "1.2B",
    timeout: int = 60,
    **kwargs  # 兼容旧参数，包含 mock_mode
) -> GenosClient:
    """
    创建 Genos 客户端实例

    Args:
        server_url: Genos 服务地址
        model_name: 模型名称 (1.2B 或 10B)
        timeout: 超时时间

    Returns:
        GenosClient 实例
    """
    resolved_url = server_url or DEFAULT_SERVER_URL
    return GenosClient(server_url=resolved_url, model_name=model_name, timeout=timeout, **kwargs)


if __name__ == "__main__":
    # 测试
    logging.basicConfig(level=logging.INFO)

    client = create_client(mock_mode=True)

    # 测试序列
    test_seq = "ATCGATCGATCGATCG" * 10

    print("\n=== 测试 Embedding (Mock) ===")
    emb = client.embed(test_seq)
    print(f"Embedding shape: {emb.shape}")
    print(f"Embedding mean: {emb.mean():.4f}")

    print("\n=== 测试变异效应 (Mock) ===")
    ref_seq = "ATCGATCGATCG" * 20
    alt_seq = "ATCGTTCGATCG" * 20  # 有一个 A->T 变异

    effect = client.predict_variant_effect(ref_seq, alt_seq)
    for key, value in effect.items():
        print(f"{key}: {value:.4f}")
