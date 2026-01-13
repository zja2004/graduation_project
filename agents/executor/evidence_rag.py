"""
证据检索 Agent (RAG)
从知识库中检索变异相关的临床证据和文献支持
"""

import json
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

logger = logging.getLogger(__name__)


class EvidenceRAGAgent:
    """证据检索 Agent (基于 RAG)"""

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

        # 加载知识库
        self._load_knowledge_bases()
        logger.info(f"✓ 证据检索 Agent 初始化: top_k={self.top_k}")

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

            logger.info(f"→ 开始检索证据: {scores_file}")

            # 读取评分结果
            scores_df = pd.read_csv(scores_file, sep='\t')
            logger.info(f"  加载 {len(scores_df)} 个变异评分")

            # 为每个变异检索证据
            all_evidence = {}
            for _, variant in scores_df.iterrows():
                evidence = self._retrieve_evidence(variant)
                all_evidence[variant["variant_id"]] = evidence

            # 保存结果
            self._save_evidence(all_evidence, output_file)
            logger.info(f"✓ 证据检索完成: {len(all_evidence)} 个变异 → {output_file}")

            return {
                "status": "success",
                "variants_count": len(all_evidence),
                "output_file": str(output_file)
            }

        except Exception as e:
            logger.error(f"✗ 证据检索失败: {e}")
            raise

    def _retrieve_evidence(self, variant: pd.Series) -> Dict:
        """为单个变异检索证据"""
        evidence = {
            "variant_id": variant["variant_id"],
            "chrom": variant["chrom"],
            "pos": variant["pos"],
            "ref": variant["ref"],
            "alt": variant["alt"],
            "sources": []
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

        return evidence

    def _search_clinvar(self, variant: pd.Series) -> Optional[Dict]:
        """在 ClinVar 中搜索变异"""
        if self.db_conn is None:
            # Fallback to simulation if DB missing
            return {
                "found": False,
                "significance": "Simulated",
                "review_status": "Simulated"
            }

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
            else:
                return {
                    "found": False,
                    "message": "Not found in local ClinVar DB"
                }
        except Exception as e:
            logger.error(f"ClinVar 查询失败: {e}")
            return None

    def _search_gnomad(self, variant: pd.Series) -> Optional[Dict]:
        """在 gnomAD 中搜索频率"""
        if self.gnomad_db is None:
            # 模拟数据
            return {
                "found": False,
                "allele_frequency": 0.0
            }

        match = self.gnomad_db[
            (self.gnomad_db["chrom"] == variant["chrom"]) &
            (self.gnomad_db["pos"] == variant["pos"])
        ]

        if not match.empty:
            return {
                "found": True,
                "allele_frequency": float(match.iloc[0].get("AF", 0.0))
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

    def _save_evidence(self, evidence: Dict, output_file: str):
        """保存证据到 JSON 文件"""
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(evidence, f, indent=2, ensure_ascii=False)
