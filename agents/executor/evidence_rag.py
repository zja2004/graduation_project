"""
证据检索 Agent (RAG) - 增强版
从知识库中检索变异相关的临床证据和文献支持
新增功能：集成 DeepSeek LLM 生成通俗化基因解释
"""

import json
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

import numpy as np

# Add remote client
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from tools.remote_knowledge import RemoteKnowledgeClient

logger = logging.getLogger(__name__)


class EvidenceRAGAgent:
    """证据检索 Agent (基于 RAG) - 增强版"""

    def __init__(self, config: Dict):
        """
        初始化证据检索 Agent

        Args:
            config: 配置字典，包含知识库路径和检索参数
        """
        self.config = config
        self.knowledge = config.get("knowledge", {})
        self.rag_config = config.get("evidence_rag", {})
        self.top_k = self.rag_config.get("top_k", 5)
        self.min_similarity = self.rag_config.get("min_similarity", 0.3)
        self.source_weights = self.rag_config.get("source_weights", {})

        # 初始化 DeepSeek 客户端（用于生成通俗化解释）
        self.deepseek_client = None
        self._init_deepseek_client()

        # 加载知识库
        self._load_knowledge_bases()
        
        # 初始化远程客户端
        self.knowledge_mode = self.knowledge.get("mode", "local")
        self.remote_client = None
        self.remote_cache = {}
        
        if self.knowledge_mode in ["hybrid", "remote"]:
            try:
                self.remote_client = RemoteKnowledgeClient(
                    timeout=self.knowledge.get("remote_timeout", 5)
                )
                logger.info("✓ 远程知识库客户端已初始化 (Mode: Hybrid)")
            except Exception as e:
                logger.warning(f"远程客户端初始化失败: {e}")

        logger.info(f"✓ 证据检索 Agent 初始化: top_k={self.top_k}")

    def _init_deepseek_client(self):
        """初始化 DeepSeek 客户端"""
        try:
            from tools.deepseek_client import create_deepseek_client
            self.deepseek_client = create_deepseek_client(self.config)
            logger.info("✓ DeepSeek 客户端初始化成功（用于生成基因解释）")
        except Exception as e:
            logger.warning(f"⚠️  DeepSeek 客户端初始化失败: {e}，将不生成AI解释")
            self.deepseek_client = None

    def _load_knowledge_bases(self):
        """加载各种知识库"""
        # Connect to SQLite DB if exists
        import sqlite3
        db_path = "data/knowledge/knowledge.db"

        self.db_conn = None
        # Initialize others to None to prevent errors
        self.gnomad_db = None
        self.omim_db = None
        self.gene_info_db = None

        if Path(db_path).exists():
            try:
                self.db_conn = sqlite3.connect(db_path, check_same_thread=False)
                logger.info(f"✓ 知识库连接成功: {db_path}")
            except Exception as e:
                logger.error(f"知识库连接失败: {e}")
        else:
            logger.warning(f"本地知识库未找到: {db_path} (请运行 tools/build_knowledge_index.py)")

    def execute(self, task: Dict) -> Dict:
        """
        执行证据检索任务

        Args:
            task: 任务字典，包含 scores_file 和 output 配置

        Returns:
            执行结果字典
        """
        try:
            scores_file = task["input"]["scores_file"]
            output_file = task["output"]["evidence_file"]

            logger.info(f"→ 开始检索证据并生成基因解释: {scores_file}")

            # 读取评分结果
            scores_df = pd.read_csv(scores_file, sep='\t')
            logger.info(f"  加载 {len(scores_df)} 个变异评分")

            # 为每个变异检索证据 + 生成AI解释
            all_evidence = {}
            for idx, variant in scores_df.iterrows():
                logger.info(f"  [{idx+1}/{len(scores_df)}] 处理变异: {variant['variant_id']}")
                evidence = self._retrieve_evidence(variant)
                all_evidence[variant["variant_id"]] = evidence

            # 保存结果
            self._save_evidence(all_evidence, output_file)
            logger.info(f"✓ 证据检索完成: {len(all_evidence)} 个变异 → {output_file}")

            # 统计生成了多少个AI解释
            explained_count = sum(1 for e in all_evidence.values() if e.get("gene_explanation"))
            logger.info(f"✓ AI通俗化解释生成: {explained_count}/{len(all_evidence)} 个变异")

            return {
                "status": "success",
                "variants_count": len(all_evidence),
                "explained_count": explained_count,
                "output_file": str(output_file)
            }

        except Exception as e:
            logger.error(f"✗ 证据检索失败: {e}")
            raise

    def _retrieve_evidence(self, variant: pd.Series) -> Dict:
        """为单个变异检索证据（增强版：包含AI生成的通俗化解释）"""
        evidence = {
            "variant_id": variant["variant_id"],
            "chrom": variant["chrom"],
            "pos": variant["pos"],
            "ref": variant["ref"],
            "alt": variant["alt"],
            "sources": [],
            "gene_explanation": None  # 新增：基因通俗化解释
        }

        # 1. ClinVar 证据
        clinvar_evidence = self._search_clinvar(variant)
        if clinvar_evidence:
            evidence["sources"].append({
                "source": "ClinVar",
                "weight": self.source_weights.get("clinvar", 1.0),
                "data": clinvar_evidence
            })

        # 2. gnomAD 频率证据
        gnomad_evidence = self._search_gnomad(variant)
        if gnomad_evidence:
            evidence["sources"].append({
                "source": "gnomAD",
                "weight": self.source_weights.get("gnomad", 0.8),
                "data": gnomad_evidence
            })

        # 3. OMIM 证据
        omim_evidence = self._search_omim(variant)
        if omim_evidence:
            evidence["sources"].append({
                "source": "OMIM",
                "weight": self.source_weights.get("omim", 0.8),
                "data": omim_evidence
            })

        # 4. 预测证据（使用评分）
        evidence["sources"].append({
            "source": "Prediction",
            "weight": self.source_weights.get("prediction", 0.4),
            "data": {
                "final_score": float(variant["final_score"]),
                "impact_level": variant["impact_level"]
            }
        })

        # 5. 【新增】生成基因通俗化解释（使用 DeepSeek AI）
        if self.deepseek_client and variant.get("gene"):
            try:
                gene_name = variant["gene"]
                variant_info = {
                    "chrom": variant["chrom"],
                    "pos": variant["pos"],
                    "ref": variant["ref"],
                    "alt": variant["alt"],
                    "impact_level": variant["impact_level"]
                }
                explanation = self.deepseek_client.generate_gene_explanation(gene_name, variant_info)
                evidence["gene_explanation"] = explanation
                logger.debug(f"✓ 生成基因解释: {gene_name}")
            except Exception as e:
                logger.warning(f"⚠️  生成基因解释失败 ({variant.get('gene')}): {e}")
                evidence["gene_explanation"] = None

        return evidence

    def _search_clinvar(self, variant: pd.Series) -> Optional[Dict]:
        """在 ClinVar 中搜索变异"""
        if self.db_conn:
            try:
                c = self.db_conn.cursor()
                # Normalize chr prefix
                chrom = str(variant["chrom"]).replace("chr", "")

                c.execute(
                    "SELECT variant_id, clnsig, clndn FROM clinvar WHERE chrom=? AND pos=? AND ref=? AND alt=?",
                    (chrom, int(variant["pos"]), variant["ref"], variant["alt"])
                )
                row = c.fetchone()

                if row:
                    return {
                        "found": True,
                        "variant_id": row[0],
                        "clinical_significance": row[1],
                        "disease_name": row[2]
                    }
            except Exception as e:
                logger.error(f"ClinVar 查询失败: {e}")

        # 如果本地未找到或数据库不可用，尝试远程查询
        if self.remote_client:
            remote_data = self._fetch_remote_evidence(variant)
            if remote_data and "clinvar" in remote_data:
                return remote_data["clinvar"]
        
        # Fallback if both fail
        if self.db_conn is None:
             return {
                "found": False,
                "significance": "Simulated",
                "review_status": "Simulated"
            }
            
        return {
            "found": False,
            "message": "Not found in local ClinVar DB or remote API"
        }

    def _search_gnomad(self, variant: pd.Series) -> Optional[Dict]:
        """在 gnomAD 中搜索频率"""
        if self.gnomad_db is not None:
             match = self.gnomad_db[
                (self.gnomad_db["chrom"] == variant["chrom"]) &
                (self.gnomad_db["pos"] == variant["pos"])
            ]

             if not match.empty:
                return {
                    "found": True,
                    "allele_frequency": float(match.iloc[0].get("AF", 0.0))
                }
            
        # 远程查询 Fallback
        if self.remote_client:
            remote_data = self._fetch_remote_evidence(variant)
            if remote_data and "gnomad" in remote_data:
                return remote_data["gnomad"]

        if self.gnomad_db is None:
            # 模拟数据
            return {
                "found": False,
                "allele_frequency": 0.0
            }
                
        return None

    def _search_omim(self, variant: pd.Series) -> Optional[Dict]:
        """在 OMIM 中搜索相关疾病"""
        if self.omim_db is None:
            # 模拟数据
            return {
                "found": False,
                "diseases": []
            }

        # 简化搜索：基于染色体区域
        relevant = [
            entry for entry in self.omim_db
            if entry.get("chrom") == variant["chrom"]
        ]

        if relevant:
            return {
                "found": True,
                "diseases": [entry.get("disease", "Unknown") for entry in relevant[:3]]
            }
        return None

    def _fetch_remote_evidence(self, variant: pd.Series) -> Optional[Dict]:
        """从远程 API 获取证据（带缓存）"""
        vid = variant["variant_id"]
        if vid in self.remote_cache:
            return self.remote_cache[vid]
            
        try:
            # 这里的 batch 优化暂未实现，先单个查询
            # 注意：MyVariant.info 使用 hg38
            data = self.remote_client.query_variant(
                chrom=variant["chrom"],
                pos=int(variant["pos"]),
                ref=variant["ref"],
                alt=variant["alt"],
                assembly="hg38"
            )
            self.remote_cache[vid] = data
            return data
        except Exception as e:
            logger.warning(f"远程查询失败 {vid}: {e}")
            return None

    def _save_evidence(self, evidence: Dict, output_file: str):
        """保存证据到 JSON 文件"""
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(evidence, f, indent=2, ensure_ascii=False)
