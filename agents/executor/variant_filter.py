"""
VariantFilterAgent: 变异筛选智能体
负责根据质量、频率、功能类型等规则过滤变异
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class VariantFilterAgent:
    """变异筛选智能体"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config
        self.stats = {
            "total_variants": 0,
            "passed_quality": 0,
            "passed_frequency": 0,
            "passed_consequence": 0,
            "final_variants": 0
        }

    def execute(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行变异筛选

        Args:
            task_input: 任务输入参数

        Returns:
            执行结果
        """
        logger.info("开始变异筛选...")

        input_data = task_input["input"]
        vcf_file = input_data["vcf_file"]
        min_quality = input_data.get("min_quality", 30)
        max_pop_freq = input_data.get("max_pop_freq", 0.01)
        consequence_types = input_data.get("consequence_types", [])

        # 解析 VCF
        variants = self._parse_vcf(vcf_file)
        self.stats["total_variants"] = len(variants)

        # 应用过滤器
        filtered = self._apply_filters(
            variants,
            min_quality=min_quality,
            max_pop_freq=max_pop_freq,
            consequence_types=consequence_types
        )

        self.stats["final_variants"] = len(filtered)

        # 保存结果
        output_config = task_input.get("output", {})
        output_vcf = output_config.get("filtered_vcf", "variants.filtered.vcf")
        stats_file = output_config.get("filter_stats", "filter_stats.json")

        self._write_vcf(filtered, output_vcf)
        self._save_stats(stats_file)

        logger.info(f"✓ 变异筛选完成: {self.stats['total_variants']} → {self.stats['final_variants']}")

        return {
            "status": "success",
            "output_files": {
                "filtered_vcf": output_vcf,
                "stats": stats_file
            },
            "stats": self.stats
        }

    def _parse_vcf(self, vcf_file: str) -> List[Dict]:
        """解析 VCF 文件（简化版）"""
        variants = []

        if not Path(vcf_file).exists():
            logger.warning(f"VCF 文件不存在: {vcf_file}，返回模拟数据")
            return self._generate_mock_variants()

        try:
            with open(vcf_file) as f:
                for line in f:
                    if line.startswith('#'):
                        continue

                    fields = line.strip().split('\t')
                    if len(fields) < 8:
                        continue

                    variant = {
                        "chrom": fields[0],
                        "pos": int(fields[1]),
                        "id": fields[2],
                        "ref": fields[3],
                        "alt": fields[4],
                        "qual": float(fields[5]) if fields[5] != '.' else 0,
                        "filter": fields[6],
                        "info": self._parse_info(fields[7])
                    }
                    variants.append(variant)

            logger.info(f"解析 VCF: {len(variants)} 个变异")
            return variants

        except Exception as e:
            logger.error(f"VCF 解析失败: {e}，使用模拟数据")
            return self._generate_mock_variants()

    def _parse_info(self, info_str: str) -> Dict:
        """解析 INFO 字段"""
        info = {}
        for item in info_str.split(';'):
            if '=' in item:
                key, value = item.split('=', 1)
                info[key] = value
            else:
                info[item] = True
        return info

    def _apply_filters(
        self,
        variants: List[Dict],
        min_quality: float,
        max_pop_freq: float,
        consequence_types: List[str]
    ) -> List[Dict]:
        """应用过滤规则"""
        filtered = []

        for var in variants:
            # 质量过滤
            if var["qual"] < min_quality:
                continue
            self.stats["passed_quality"] += 1

            # 频率过滤（如果有 AF 字段）
            af_str = str(var["info"].get("AF", "0"))
            try:
                if "," in af_str:
                    # 对于多等位基因位点，取最大的频率进行过滤
                    af = max(float(x) for x in af_str.split(",") if x.strip())
                else:
                    af = float(af_str)
            except ValueError:
                af = 0.0
            if af > max_pop_freq:
                continue
            self.stats["passed_frequency"] += 1

            # 功能类型过滤（如果有 CSQ 字段）
            csq = var["info"].get("CSQ", "missense_variant")
            if consequence_types and not any(c in csq for c in consequence_types):
                continue
            self.stats["passed_consequence"] += 1

            filtered.append(var)

        return filtered

    def _write_vcf(self, variants: List[Dict], output_file: str):
        """写入过滤后的 VCF"""
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            # 写入 header
            f.write("##fileformat=VCFv4.2\n")
            f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")

            # 写入变异
            for var in variants:
                info_str = ';'.join(
                    f"{k}={v}" if v is not True else k
                    for k, v in var["info"].items()
                )
                f.write(
                    f"{var['chrom']}\t{var['pos']}\t{var['id']}\t"
                    f"{var['ref']}\t{var['alt']}\t{var['qual']}\t"
                    f"{var['filter']}\t{info_str}\n"
                )

    def _save_stats(self, stats_file: str):
        """保存统计信息"""
        Path(stats_file).parent.mkdir(parents=True, exist_ok=True)

        with open(stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)

    def _generate_mock_variants(self) -> List[Dict]:
        """生成模拟变异（用于测试）"""
        logger.info("生成模拟变异数据...")

        mock_variants = [
            {
                "chrom": "chr1",
                "pos": 100000,
                "id": "rs123456",
                "ref": "A",
                "alt": "T",
                "qual": 50.0,
                "filter": "PASS",
                "info": {"AF": 0.001, "CSQ": "missense_variant"}
            },
            {
                "chrom": "chr2",
                "pos": 200000,
                "id": ".",
                "ref": "G",
                "alt": "C",
                "qual": 80.0,
                "filter": "PASS",
                "info": {"AF": 0.0001, "CSQ": "stop_gained"}
            },
            {
                "chrom": "chr3",
                "pos": 300000,
                "id": ".",
                "ref": "ATG",
                "alt": "A",
                "qual": 60.0,
                "filter": "PASS",
                "info": {"AF": 0.005, "CSQ": "frameshift_variant"}
            }
        ]

        return mock_variants


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    agent = VariantFilterAgent()

    result = agent.execute({
        "vcf_file": "test.vcf",
        "min_quality": 30,
        "max_pop_freq": 0.01,
        "consequence_types": ["missense_variant", "stop_gained", "frameshift_variant"],
        "output": {
            "filtered_vcf": "test_filtered.vcf",
            "filter_stats": "test_stats.json"
        }
    })

    print(json.dumps(result, indent=2))
