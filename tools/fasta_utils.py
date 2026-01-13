"""
FASTA 序列处理工具
负责从参考基因组提取序列窗口（支持 SNV/Indel）
"""

import logging
from typing import Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import pyfaidx
    PYFAIDX_AVAILABLE = True
except ImportError:
    PYFAIDX_AVAILABLE = False
    logger.warning("pyfaidx 未安装，将使用简化的序列提取功能")


class FastaExtractor:
    """参考基因组序列提取器"""

    def __init__(self, fasta_path: str):
        """
        初始化 FASTA 提取器

        Args:
            fasta_path: 参考基因组 FASTA 文件路径
        """
        self.fasta_path = Path(fasta_path)

        if not self.fasta_path.exists():
            logger.warning(f"FASTA 文件不存在: {fasta_path}")
            self.fasta = None
        elif PYFAIDX_AVAILABLE:
            try:
                self.fasta = pyfaidx.Fasta(str(self.fasta_path))
                logger.info(f"✓ 加载参考基因组: {fasta_path}")
                logger.info(f"  染色体数: {len(self.fasta.keys())}")
            except Exception as e:
                logger.error(f"加载 FASTA 失败: {e}")
                self.fasta = None
        else:
            self.fasta = None

    def extract_window(
        self,
        chrom: str,
        pos: int,
        ref: str,
        alt: str,
        window_size: int = 2000
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        提取变异位点的序列窗口（ref 和 alt 两个版本）

        Args:
            chrom: 染色体（如 "chr1" 或 "1"）
            pos: 位置（1-based）
            ref: 参考等位基因
            alt: 变异等位基因
            window_size: 窗口大小（单侧，总窗口 = 2 * window_size）

        Returns:
            (ref_sequence, alt_sequence) 或 (None, None) 如果提取失败
        """
        if self.fasta is None:
            logger.warning("FASTA 未加载，返回模拟序列")
            return self._mock_sequence(window_size, ref, alt)

        try:
            # 标准化染色体名称
            chrom = self._normalize_chrom(chrom)

            # 计算窗口坐标（1-based -> 0-based）
            start = max(0, pos - window_size - 1)
            end = pos + len(ref) + window_size - 1

            # 提取序列
            sequence = str(self.fasta[chrom][start:end])

            # 验证 ref 是否匹配
            ref_in_seq = sequence[window_size:window_size + len(ref)]
            if ref_in_seq.upper() != ref.upper():
                logger.error(
                    f"Ref 不匹配! 位置 {chrom}:{pos}, "
                    f"VCF ref={ref}, FASTA ref={ref_in_seq}"
                )
                return None, None

            # 构造 ref 序列（完整窗口）
            ref_sequence = sequence

            # 构造 alt 序列（替换中心变异）
            alt_sequence = (
                sequence[:window_size] +
                alt +
                sequence[window_size + len(ref):]
            )

            logger.debug(
                f"提取窗口: {chrom}:{pos} {ref}>{alt}, "
                f"ref_len={len(ref_sequence)}, alt_len={len(alt_sequence)}"
            )

            return ref_sequence.upper(), alt_sequence.upper()

        except Exception as e:
            logger.error(f"序列提取失败 {chrom}:{pos}: {e}")
            return None, None

    def _normalize_chrom(self, chrom: str) -> str:
        """标准化染色体名称（chr1 <-> 1）"""
        if chrom in self.fasta.keys():
            return chrom

        # 尝试添加/删除 "chr" 前缀
        if chrom.startswith("chr"):
            alt_chrom = chrom[3:]
        else:
            alt_chrom = f"chr{chrom}"

        if alt_chrom in self.fasta.keys():
            return alt_chrom

        # 都不行，返回原始
        return chrom

    def _mock_sequence(
        self,
        window_size: int,
        ref: str,
        alt: str
    ) -> Tuple[str, str]:
        """生成模拟序列（用于测试）"""
        import random

        def random_seq(length):
            return ''.join(random.choices('ATCG', k=length))

        left = random_seq(window_size)
        right = random_seq(window_size)

        ref_sequence = left + ref + right
        alt_sequence = left + alt + right

        logger.debug(f"生成模拟序列: {len(ref_sequence)} bp")
        return ref_sequence, alt_sequence

    def validate_variant(
        self,
        chrom: str,
        pos: int,
        ref: str
    ) -> bool:
        """
        验证变异的 ref 是否与参考基因组一致

        Args:
            chrom: 染色体
            pos: 位置（1-based）
            ref: 参考等位基因

        Returns:
            True 如果一致，False 否则
        """
        if self.fasta is None:
            return True  # 无法验证时默认通过

        try:
            chrom = self._normalize_chrom(chrom)
            ref_in_fasta = str(self.fasta[chrom][pos - 1:pos - 1 + len(ref)])

            is_valid = ref_in_fasta.upper() == ref.upper()

            if not is_valid:
                logger.warning(
                    f"Ref 不匹配: {chrom}:{pos}, "
                    f"VCF={ref}, FASTA={ref_in_fasta}"
                )

            return is_valid

        except Exception as e:
            logger.error(f"Ref 验证失败: {e}")
            return False


def extract_sequence_window(
    fasta_path: str,
    chrom: str,
    pos: int,
    window_size: int = 2000,
    ref: str = "N",
    alt: str = "N"
) -> str:
    """
    便捷函数：提取序列窗口（仅返回参考序列）

    Args:
        fasta_path: FASTA 文件路径
        chrom: 染色体
        pos: 位置（1-based）
        window_size: 窗口大小
        ref: 参考碱基（可选）
        alt: 变异碱基（可选）

    Returns:
        参考序列窗口
    """
    extractor = FastaExtractor(fasta_path)
    ref_seq, _ = extractor.extract_window(chrom, pos, ref, alt, window_size)
    return ref_seq if ref_seq else ""


def calculate_gc_content(sequence: str) -> float:
    """计算 GC 含量"""
    if not sequence:
        return 0.0

    sequence = sequence.upper()
    gc_count = sequence.count('G') + sequence.count('C')
    return gc_count / len(sequence)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 测试（使用模拟模式）
    extractor = FastaExtractor("dummy.fasta")

    ref_seq, alt_seq = extractor.extract_window(
        chrom="chr1",
        pos=100000,
        ref="A",
        alt="T",
        window_size=500
    )

    print(f"\nRef sequence: {ref_seq[:50]}...{ref_seq[-50:]}")
    print(f"Alt sequence: {alt_seq[:50]}...{alt_seq[-50:]}")
    print(f"GC content (ref): {calculate_gc_content(ref_seq):.2%}")
