"""
Critic - 一致性检查模块
负责交叉验证注释、证据、评分之间的一致性
"""

import json
import logging
from typing import Dict, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class ConsistencyChecker:
    """一致性检查器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.issues = []

    def check(
        self,
        annotation: Dict,
        scores: Dict,
        evidence: Dict
    ) -> Dict[str, Any]:
        """
        执行一致性检查

        Args:
            annotation: 注释数据
            scores: 评分数据
            evidence: 证据数据

        Returns:
            检查结果
        """
        logger.info("开始一致性检查...")

        self.issues = []

        # 1. 检查注释一致性
        if self.config.get("check_annotation", True):
            self._check_annotation_consistency(annotation, evidence)

        # 2. 检查频率一致性
        if self.config.get("check_frequency", True):
            self._check_frequency_consistency(annotation, evidence)

        # 3. 检查证据一致性
        if self.config.get("check_evidence", True):
            self._check_evidence_consistency(scores, evidence)

        # 生成报告
        report = {
            "status": "pass" if len(self.issues) == 0 else "warning",
            "total_issues": len(self.issues),
            "issues": self.issues,
            "checks_performed": {
                "annotation": self.config.get("check_annotation", True),
                "frequency": self.config.get("check_frequency", True),
                "evidence": self.config.get("check_evidence", True)
            }
        }

        if len(self.issues) == 0:
            logger.info("✓ 一致性检查通过，未发现问题")
        else:
            logger.warning(f"⚠ 一致性检查发现 {len(self.issues)} 个问题")

        return report

    def _check_annotation_consistency(self, annotation: Dict, evidence: Dict):
        """检查注释与证据是否一致"""
        # 示例：检查基因功能类型是否与 ClinVar 记录一致
        gene = annotation.get("gene", "")
        consequence = annotation.get("consequence", "")

        clinvar_evidence = evidence.get("clinvar", {})
        clinvar_consequence = clinvar_evidence.get("consequence", "")

        if clinvar_consequence and consequence != clinvar_consequence:
            self.issues.append({
                "type": "annotation_mismatch",
                "severity": "warning",
                "message": f"注释后果 ({consequence}) 与 ClinVar ({clinvar_consequence}) 不一致",
                "gene": gene,
                "expected": clinvar_consequence,
                "actual": consequence
            })

    def _check_frequency_consistency(self, annotation: Dict, evidence: Dict):
        """检查频率数据一致性"""
        # 示例：检查 gnomAD 频率是否合理
        gnomad_af = annotation.get("gnomad_af", 0)
        max_expected_af = 0.01  # 病原变异通常 < 1%

        if gnomad_af > max_expected_af:
            self.issues.append({
                "type": "high_frequency",
                "severity": "warning",
                "message": f"变异频率 ({gnomad_af:.4f}) 高于预期 ({max_expected_af})",
                "gnomad_af": gnomad_af,
                "threshold": max_expected_af
            })

    def _check_evidence_consistency(self, scores: Dict, evidence: Dict):
        """检查评分与证据一致性"""
        # 示例：高分变异应该有强证据支持
        genos_score = scores.get("genos_impact_score", 0)
        evidence_count = len(evidence.get("supporting_evidence", []))

        if genos_score > 0.7 and evidence_count == 0:
            self.issues.append({
                "type": "score_evidence_mismatch",
                "severity": "warning",
                "message": f"高影响评分 ({genos_score:.2f}) 但缺乏证据支持",
                "genos_score": genos_score,
                "evidence_count": evidence_count
            })

        # 低分但有病原性证据
        clinvar_sig = evidence.get("clinvar", {}).get("significance", "")
        if genos_score < 0.3 and "pathogenic" in clinvar_sig.lower():
            self.issues.append({
                "type": "score_evidence_conflict",
                "severity": "error",
                "message": f"低影响评分 ({genos_score:.2f}) 但 ClinVar 标记为病原性",
                "genos_score": genos_score,
                "clinvar_significance": clinvar_sig
            })


class GroundingValidator:
    """证据归因验证器"""

    def __init__(self):
        self.grounding_issues = []

    def validate(self, report: str, evidence: Dict) -> Dict[str, Any]:
        """
        验证报告中的每条结论是否有证据支持

        Args:
            report: 报告文本
            evidence: 证据数据

        Returns:
            验证结果
        """
        logger.info("开始证据归因验证...")

        self.grounding_issues = []

        # 提取报告中的关键结论
        conclusions = self._extract_conclusions(report)

        # 验证每条结论
        for conclusion in conclusions:
            if not self._has_evidence_support(conclusion, evidence):
                self.grounding_issues.append({
                    "conclusion": conclusion,
                    "issue": "缺乏证据支持"
                })

        result = {
            "status": "pass" if len(self.grounding_issues) == 0 else "fail",
            "total_conclusions": len(conclusions),
            "unsupported_conclusions": len(self.grounding_issues),
            "issues": self.grounding_issues
        }

        if len(self.grounding_issues) == 0:
            logger.info("✓ 证据归因验证通过")
        else:
            logger.warning(f"⚠ 发现 {len(self.grounding_issues)} 条无证据支持的结论")

        return result

    def _extract_conclusions(self, report: str) -> List[str]:
        """从报告中提取关键结论"""
        # 简化版：提取包含"致病"、"良性"等关键词的句子
        keywords = ["致病", "良性", "可能", "预测", "影响"]
        conclusions = []

        for line in report.split('\n'):
            if any(kw in line for kw in keywords):
                conclusions.append(line.strip())

        return conclusions

    def _has_evidence_support(self, conclusion: str, evidence: Dict) -> bool:
        """检查结论是否有证据支持"""
        # 简化版：检查证据字典是否非空
        return len(evidence.get("supporting_evidence", [])) > 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 测试一致性检查
    checker = ConsistencyChecker({
        "check_annotation": True,
        "check_frequency": True,
        "check_evidence": True
    })

    test_annotation = {
        "gene": "BRCA1",
        "consequence": "missense_variant",
        "gnomad_af": 0.0001
    }

    test_scores = {
        "genos_impact_score": 0.85
    }

    test_evidence = {
        "clinvar": {
            "consequence": "missense_variant",
            "significance": "Pathogenic"
        },
        "supporting_evidence": [
            {"source": "ClinVar", "text": "已知致病变异"}
        ]
    }

    result = checker.check(test_annotation, test_scores, test_evidence)
    print(json.dumps(result, indent=2, ensure_ascii=False))


class ConsistencyAgent:
    """Critic 审校智能体 adapter"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.checker = ConsistencyChecker(config.get("critic", {}))
        self.validator = GroundingValidator()

    def execute(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行审校任务

        Args:
            task_input: 任务输入

        Returns:
            执行结果
        """
        logger.info("开始 Critic 审校...")
        
        # 1. 获取输入文件路径
        input_data = task_input["input"]
        artifacts = input_data.get("all_artifacts", {})
        scores_file = artifacts.get("scores")
        evidence_file = artifacts.get("evidence")
        report_file = artifacts.get("report")
        
        output_file = task_input.get("output", {}).get("critic_report")
        
        # 2. 加载数据
        scores_data = self._load_scores(scores_file)
        evidence_data = self._load_evidence(evidence_file)
        report_text = self._load_report(report_file)
        
        # 3. 执行检查
        # 注意: 这里假设 scores_data 包含部分 annotation 信息，或者只检查 evidence
        # 实际情况可能需要更复杂的加载逻辑来获取 annotation
        # 为简单起见，这里传入空 annotation 或从 scores 提取
        annotation = {} 
        
        consistency_result = self.checker.check(annotation, scores_data, evidence_data)
        grounding_result = self.validator.validate(report_text, evidence_data)
        
        final_report = {
            "consistency": consistency_result,
            "grounding": grounding_result,
            "overall_status": "pass" if consistency_result["status"] == "pass" and grounding_result["status"] == "pass" else "warning"
        }
        
        # 4. 保存报告
        self._save_report(final_report, output_file)
        
        logger.info(f"✓ Panic 审校完成，状态: {final_report['overall_status']}")
        
        return {
            "status": "success",
            "output_files": {
                "critic_report": output_file
            },
            "report": final_report
        }

    def _load_scores(self, file_path: str) -> Dict:
        """加载评分文件 (Mock)"""
        # 实际应读取 TSV，这里简单返回 Mock 或尝试读取
        if not file_path or not Path(file_path).exists():
            return {}
        try:
            # 简单读取第一行数据作为示例
            with open(file_path, 'r', encoding='utf-8') as f:
                header = f.readline().strip().split('\t')
                first_line = f.readline().strip().split('\t')
                if len(header) == len(first_line):
                    return dict(zip(header, first_line))
        except Exception:
            pass
        return {}

    def _load_evidence(self, file_path: str) -> Dict:
        """加载证据文件"""
        if not file_path or not Path(file_path).exists():
            return {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def _load_report(self, file_path: str) -> str:
        """加载报告文件"""
        if not file_path or not Path(file_path).exists():
            return ""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ""

    def _save_report(self, report: Dict, file_path: str):
        """保存审校报告"""
        if not file_path:
            return
        
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
