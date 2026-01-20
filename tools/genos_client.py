"""
Genos 客户端工具 - 官方 DCS API 封装
使用华大基因官方云 API (https://cloud.stomics.tech)
需要 API Token 认证
"""

import os
import sys
import numpy as np
from typing import Dict, List, Optional
import logging

# 导入官方 Genos SDK
genos_sdk_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../Genos/sdk'))
if os.path.exists(genos_sdk_path) and genos_sdk_path not in sys.path:
    sys.path.insert(0, genos_sdk_path)

try:
    from genos import create_client as create_official_client
    from genos.client import GenosClient as OfficialGenosClient
    OFFICIAL_SDK_AVAILABLE = True
except ImportError:
    OFFICIAL_SDK_AVAILABLE = False
    logging.warning("⚠️  官方 Genos SDK 未找到，仅支持模拟模式")

logger = logging.getLogger(__name__)


class GenosClient:
    """Genos 官方 DCS API 客户端封装"""

    def __init__(self, server_url: str = None, model_name: str = "Genos-1.2B", timeout: int = 60, mock_mode: bool = False, api_token: str = None, **kwargs):
        """
        初始化 Genos 客户端

        Args:
            server_url: (已废弃) 保留参数用于兼容性
            model_name: 模型名称 ("Genos-1.2B" 或 "Genos-10B")
            timeout: 请求超时时间
            mock_mode: 是否使用模拟模式 (默认 False)
            api_token: DCS API Token (必需，除非设置环境变量 GENOS_API_TOKEN)
        """
        self.model_name = model_name
        self.timeout = timeout
        self.mock_mode = mock_mode

        # 获取 API Token
        self.api_token = api_token or os.getenv("GENOS_API_TOKEN")

        if not OFFICIAL_SDK_AVAILABLE:
            logger.warning("⚠️  官方 SDK 不可用，强制使用模拟模式")
            self.mock_mode = True

        if not self.mock_mode and not self.api_token:
            logger.warning("⚠️  未提供 API Token，将使用模拟模式")
            self.mock_mode = True

        # 初始化官方客户端
        if not self.mock_mode and OFFICIAL_SDK_AVAILABLE:
            try:
                self.official_client: OfficialGenosClient = create_official_client(
                    token=self.api_token,
                    timeout=self.timeout
                )
                logger.info(f"✓ Genos DCS 客户端初始化成功: 模型 {self.model_name}")
            except Exception as e:
                logger.error(f"✗ Genos DCS 客户端初始化失败: {e}")
                logger.warning("⚠️  切换到模拟模式")
                self.mock_mode = True
                self.official_client = None
        else:
            self.official_client = None
            logger.info(f"✓ Genos 模拟模式已启用")

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
            # 返回随机 embedding (维度 1024 用于测试)
            emb = np.random.rand(1024).astype(np.float32)
            if normalize:
                norm = np.linalg.norm(emb)
                if norm > 0:
                    emb = emb / norm
            return emb

        try:
            # 调用官方 SDK
            response = self.official_client.get_embedding(
                sequence=sequence,
                model_name=self.model_name,
                pooling_method=pooling
            )

            # 从响应中提取 embedding
            if response.get("status") == 200:
                result = response.get("result", {})
                embedding_data = result.get("embedding")

                # 转换为 numpy array
                if hasattr(embedding_data, 'numpy'):
                    # 如果是 PyTorch tensor
                    embedding = embedding_data.cpu().numpy()
                elif isinstance(embedding_data, list):
                    embedding = np.array(embedding_data, dtype=np.float32)
                elif isinstance(embedding_data, np.ndarray):
                    embedding = embedding_data
                else:
                    raise ValueError(f"未知的 embedding 类型: {type(embedding_data)}")

                # 归一化
                if normalize and embedding.size > 0:
                    norm = np.linalg.norm(embedding)
                    if norm > 0:
                        embedding = embedding / norm

                logger.debug(f"生成 embedding: shape={embedding.shape}, mean={embedding.mean():.4f}")
                return embedding
            else:
                error_msg = response.get("message", "Unknown error")
                raise ValueError(f"API 返回错误 (status={response.get('status')}): {error_msg}")

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
                    embeddings.append(np.zeros(1024))  # fallback dimension

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
            cosine_sim = float(np.dot(ref_emb, alt_emb))
            euclidean_dist = float(np.linalg.norm(ref_emb - alt_emb))
            diff_magnitude = float(np.abs(ref_emb - alt_emb).mean())

            # 综合评分（距离越大，影响越大）
            impact_score = (1 - cosine_sim) * 0.5 + euclidean_dist * 0.3 + diff_magnitude * 0.2

            return {
                "cosine_similarity": cosine_sim,
                "euclidean_distance": euclidean_dist,
                "diff_magnitude": diff_magnitude,
                "impact_score": impact_score,
                "ref_embedding_mean": float(ref_emb.mean()),
                "alt_embedding_mean": float(alt_emb.mean())
            }

        except Exception as e:
            logger.error(f"变异效应预测失败: {e}")
            raise

    def variant_predict(self, assembly: str, chrom: str, pos: int, ref: str, alt: str) -> Dict:
        """
        使用官方 Variant Predictor API 预测变异致病性

        Args:
            assembly: 参考基因组版本 ('hg38' 或 'hg19')
            chrom: 染色体 (如 'chr6')
            pos: 位置 (1-based)
            ref: 参考碱基
            alt: 变异碱基

        Returns:
            预测结果字典
        """
        if self.mock_mode:
            return {
                "variant": f"{chrom}:{pos}{ref}>{alt}",
                "prediction": "Benign",
                "score_Benign": 0.75,
                "score_Pathogenic": 0.25
            }

        try:
            result = self.official_client.variant_predict(
                assembly=assembly,
                chrom=chrom,
                pos=pos,
                ref=ref,
                alt=alt
            )
            return result
        except Exception as e:
            logger.error(f"变异预测失败: {e}")
            raise


def create_client(
    server_url: Optional[str] = None,
    model_name: str = "Genos-1.2B",
    timeout: int = 60,
    api_token: Optional[str] = None,
    **kwargs
) -> GenosClient:
    """
    创建 Genos 客户端实例

    Args:
        server_url: (已废弃) 保留用于兼容性
        model_name: 模型名称 ("Genos-1.2B" 或 "Genos-10B")
        timeout: 超时时间
        api_token: DCS API Token

    Returns:
        GenosClient 实例
    """
    return GenosClient(
        server_url=server_url,
        model_name=model_name,
        timeout=timeout,
        api_token=api_token,
        **kwargs
    )


if __name__ == "__main__":
    # 测试
    logging.basicConfig(level=logging.INFO)

    print("\n=== 测试模拟模式 ===")
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

    # 如果有 API Token，测试真实 API
    api_token = os.getenv("GENOS_API_TOKEN")
    if api_token:
        print("\n=== 测试官方 DCS API ===")
        real_client = create_client(api_token=api_token)

        print("\n测试真实 Embedding...")
        real_emb = real_client.embed("ATCGATCG" * 50)
        print(f"Real embedding shape: {real_emb.shape}")
        print(f"Real embedding mean: {real_emb.mean():.4f}")
    else:
        print("\n⚠️  未设置 GENOS_API_TOKEN 环境变量，跳过真实 API 测试")
