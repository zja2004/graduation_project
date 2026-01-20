"""
序列上下文提取 Agent
从参考基因组中提取变异位点的序列窗口
"""

import json
import logging
from pathlib import Path
from typing import Dict, List
from tools.fasta_utils import extract_sequence_window

logger = logging.getLogger(__name__)


class SequenceContextAgent:
    """序列上下文提取 Agent"""

    def __init__(self, config: Dict):
        """
        初始化序列上下文提取 Agent

        Args:
            config: 配置字典，包含参考基因组路径和窗口大小
        """
        self.config = config
        self.reference = config.get("reference", {})
        self.context_config = config.get("sequence_context", {})
        self.window_size = self.context_config.get("window_size", 2000)
        self.validate_ref = self.context_config.get("validate_ref", True)

        logger.info(f"✓ 序列上下文提取 Agent 初始化: window_size={self.window_size}")

    def execute(self, task: Dict) -> Dict:
        """
        执行序列上下文提取任务

        Args:
            task: 任务字典，包含 variants_file 和 output 配置

        Returns:
            执行结果字典
        """
        try:
            variants_file = task["input"]["variants_file"]
            output_file = task["output"]["contexts_file"]

            logger.info(f"→ 开始提取序列上下文: {variants_file}")

            # 读取变异数据
            variants = self._load_variants(variants_file)
            logger.info(f"  加载 {len(variants)} 个变异")

            # 提取序列上下文
            contexts = []
            fasta_path = self.reference.get("fasta")

            for variant in variants:
                try:
                    context = self._extract_context(variant, fasta_path)
                    contexts.append(context)
                except Exception as e:
                    logger.warning(f"  提取序列失败 {variant.get('id', 'unknown')}: {e}")

            # 保存结果
            self._save_contexts(contexts, output_file)
            logger.info(f"✓ 序列上下文提取完成: {len(contexts)} 个序列 → {output_file}")

            return {
                "status": "success",
                "contexts_count": len(contexts),
                "output_file": str(output_file)
            }

        except Exception as e:
            logger.error(f"✗ 序列上下文提取失败: {e}")
            raise

    def _load_variants(self, variants_file: str) -> List[Dict]:
        """加载变异数据"""
        variants = []
        with open(variants_file, 'r') as f:
            for line in f:
                if line.startswith('#'):
                    continue
                parts = line.strip().split('\t')
                if len(parts) >= 8:
                    variants.append({
                        "chrom": parts[0],
                        "pos": int(parts[1]),
                        "id": parts[2] if parts[2] != '.' else f"{parts[0]}:{parts[1]}",
                        "ref": parts[3],
                        "alt": parts[4],
                        "qual": float(parts[5]) if parts[5] != '.' else 0,
                        "info": parts[7]
                    })
        return variants

    def _extract_context(self, variant: Dict, fasta_path: str) -> Dict:
        """提取单个变异的序列上下文"""
        chrom = variant["chrom"]
        pos = variant["pos"]
        ref = variant["ref"]
        alt = variant["alt"]

        # 提取参考序列
        ref_sequence = extract_sequence_window(
            fasta_path=fasta_path,
            chrom=chrom,
            pos=pos,
            window_size=self.window_size,
            ref=ref,
            alt=alt
        )

        # 构建变异序列（简单替换中心位置）
        center = self.window_size
        alt_sequence = ref_sequence[:center] + alt + ref_sequence[center + len(ref):]

        # 验证参考碱基
        extracted_ref = ref_sequence[center:center + len(ref)]
        if self.validate_ref and extracted_ref != ref:
            logger.warning(
                f"  参考碱基不匹配 {variant['id']}: "
                f"VCF={ref}, FASTA={extracted_ref}"
            )

        return {
            "variant_id": variant["id"],
            "chrom": chrom,
            "pos": pos,
            "ref": ref,
            "alt": alt,
            "info": variant.get("info", ""),
            "ref_sequence": ref_sequence,
            "alt_sequence": alt_sequence,
            "window_size": self.window_size
        }

    def _save_contexts(self, contexts: List[Dict], output_file: str):
        """保存序列上下文到 JSONL 文件"""
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            for ctx in contexts:
                f.write(json.dumps(ctx, ensure_ascii=False) + '\n')
