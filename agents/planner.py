"""
Planner 智能体
负责将用户需求拆解为可执行的 DAG 任务流
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class PlannerAgent:
    """规划智能体：将任务拆解为执行计划"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化 Planner

        Args:
            config: 系统配置字典
        """
        self.config = config

    def create_plan(
        self,
        input_vcf: str,
        output_dir: str,
        sample_name: str = "sample",
        phenotype: str = None
    ) -> Dict[str, Any]:
        """
        创建执行计划

        Args:
            input_vcf: 输入 VCF 文件路径
            output_dir: 输出目录
            sample_name: 样本名称
            phenotype: 表型描述（可选）

        Returns:
            执行计划字典
        """
        logger.info(f"创建执行计划: {sample_name}")

        # 创建输出目录
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 定义任务 DAG
        plan = {
            "metadata": {
                "sample_name": sample_name,
                "input_vcf": input_vcf,
                "phenotype": phenotype,
                "output_dir": str(output_path),
                "created_at": datetime.now().isoformat(),
                "config_snapshot": self.config
            },
            "tasks": [
                {
                    "step": 1,
                    "name": "variant_filter",
                    "description": "候选变异筛选（质量、频率、功能类型）",
                    "agent": "VariantFilterAgent",
                    "input": {
                        "vcf_file": input_vcf,
                        "min_quality": self.config["variant_filter"]["min_quality"],
                        "max_pop_freq": self.config["variant_filter"]["max_population_freq"],
                        "consequence_types": self.config["variant_filter"]["consequence_types"]
                    },
                    "output": {
                        "filtered_vcf": str(output_path / "variants.filtered.vcf"),
                        "filter_stats": str(output_path / "filter_stats.json")
                    },
                    "validation": {
                        "check_file_exists": True,
                        "min_variants": 0
                    }
                },
                {
                    "step": 2,
                    "name": "sequence_context",
                    "description": "序列上下文构造（ref/alt 窗口）",
                    "agent": "SequenceContextAgent",
                    "depends_on": ["variant_filter"],
                    "input": {
                        "variants_file": "${output.variant_filter.filtered_vcf}"
                    },
                    "output": {
                        "contexts_file": str(output_path / "contexts.jsonl")
                    },
                    "validation": {
                        "check_file_exists": True,
                        "check_ref_validation": True
                    }
                },
                {
                    "step": 3,
                    "name": "genos_embedding",
                    "description": "Genos embedding 生成",
                    "agent": "GenosAgent",
                    "depends_on": ["sequence_context"],
                    "input": {
                        "contexts_file": "${output.sequence_context.contexts_file}",
                        "server_url": self.config["genos"].get("server_url"),
                        "model_name": self.config["genos"]["model_name"],
                        "pooling": self.config["genos"]["pooling"],
                        "timeout": self.config["genos"]["timeout"],
                        "batch_size": self.config["performance"]["batch_size"],
                        "mock_mode": self.config["genos"].get("mock_mode", False)
                    },
                    "output": {
                        "embeddings_file": str(output_path / "genos_embeddings.parquet")
                    },
                    "validation": {
                        "check_file_exists": True,
                        "check_embedding_dim": True
                    }
                },
                {
                    "step": 4,
                    "name": "scoring",
                    "description": "变异效应打分",
                    "agent": "ScoringAgent",
                    "depends_on": ["genos_embedding"],
                    "input": {
                        "embeddings_file": "${output.genos_embedding.embeddings_file}",
                        "contexts_file": "${output.sequence_context.contexts_file}"  # 添加 contexts 以提取基因信息
                    },
                    "output": {
                        "scores_file": str(output_path / "scores.tsv")
                    },
                    "validation": {
                        "check_file_exists": True,
                        "check_score_range": [0, 1]
                    }
                },
                {
                    "step": 5,
                    "name": "evidence_rag",
                    "description": "证据检索与归因（RAG）",
                    "agent": "EvidenceRAGAgent",
                    "depends_on": ["scoring"],
                    "input": {
                        "scores_file": "${output.scoring.scores_file}"
                    },
                    "output": {
                        "evidence_file": str(output_path / "evidence.json")
                    },
                    "validation": {
                        "check_file_exists": True,
                        "check_evidence_grounding": True
                    }
                },
                {
                    "step": 6,
                    "name": "report_generation",
                    "description": "报告生成",
                    "agent": "ReportAgent",
                    "depends_on": ["evidence_rag"],
                    "input": {
                        "scores_file": "${output.scoring.scores_file}",
                        "evidence_file": "${output.evidence_rag.evidence_file}"
                    },
                    "output": {
                        "report_file": str(output_path / "report.md")
                    },
                    "validation": {
                        "check_file_exists": True
                    }
                },
                {
                    "step": 7,
                    "name": "critic_review",
                    "description": "Critic 审校与验证",
                    "agent": "ConsistencyAgent",
                    "depends_on": ["report_generation"],
                    "input": {
                        "all_artifacts": {
                            "scores": "${output.scoring.scores_file}",
                            "evidence": "${output.evidence_rag.evidence_file}",
                            "report": "${output.report_generation.report_file}"
                        }
                    },
                    "output": {
                        "critic_report": str(output_path / "critic_report.json")
                    },
                    "validation": {
                        "check_file_exists": True,
                        "check_consistency": True
                    }
                }
            ]
        }

        logger.info(f"执行计划已创建: {len(plan['tasks'])} 个任务")
        return plan

    def save_plan(self, plan: Dict[str, Any], output_path: str):
        """保存执行计划到 YAML 文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(plan, f, default_flow_style=False, allow_unicode=True)
        logger.info(f"执行计划已保存: {output_path}")

    def resolve_dependencies(self, plan: Dict[str, Any]) -> List[str]:
        """
        解析任务依赖关系，返回执行顺序

        Args:
            plan: 执行计划

        Returns:
            任务名称列表（按执行顺序）
        """
        tasks = plan["tasks"]
        execution_order = []

        # 简单的拓扑排序（假设 step 已排序）
        for task in sorted(tasks, key=lambda x: x["step"]):
            execution_order.append(task["name"])

        logger.debug(f"执行顺序: {' -> '.join(execution_order)}")
        return execution_order

    def validate_plan(self, plan: Dict[str, Any]) -> bool:
        """验证执行计划的合法性"""
        try:
            # 检查必需字段
            assert "metadata" in plan
            assert "tasks" in plan
            assert len(plan["tasks"]) > 0

            # 检查任务依赖
            task_names = {task["name"] for task in plan["tasks"]}
            for task in plan["tasks"]:
                if "depends_on" in task:
                    for dep in task["depends_on"]:
                        assert dep in task_names, f"未知依赖: {dep}"

            logger.info("✓ 执行计划验证通过")
            return True

        except AssertionError as e:
            logger.error(f"✗ 执行计划验证失败: {e}")
            return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 加载配置
    with open("configs/run.yaml") as f:
        config = yaml.safe_load(f)

    # 创建 Planner
    planner = PlannerAgent(config)

    # 创建执行计划
    plan = planner.create_plan(
        input_vcf="examples/test.vcf",
        output_dir="runs/test_run",
        sample_name="test_sample",
        phenotype="发育迟缓, 癫痫"
    )

    # 验证计划
    planner.validate_plan(plan)

    # 保存计划
    planner.save_plan(plan, "runs/test_run/plan.yaml")

    print("\n=== 执行顺序 ===")
    for task_name in planner.resolve_dependencies(plan):
        print(f"  → {task_name}")
