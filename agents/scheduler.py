"""
Executor 智能体调度器
负责执行 Planner 生成的任务计划
"""

import logging
import yaml
from typing import Dict, Any
from pathlib import Path

from agents.executor import (
    VariantFilterAgent,
    GenosAgent,
    SequenceContextAgent,
    ScoringAgent,
    EvidenceRAGAgent,
    ReportAgent
)
from agents.critic import ConsistencyAgent

logger = logging.getLogger(__name__)


class ExecutorScheduler:
    """Executor 调度器：执行任务计划"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化 Executor 调度器

        Args:
            config: 系统配置字典
        """
        self.config = config
        self.agents = {}
        self._initialize_agents()

    def _initialize_agents(self):
        """初始化所有 executor agents"""
        try:
            self.agents["VariantFilterAgent"] = VariantFilterAgent(self.config)
            self.agents["SequenceContextAgent"] = SequenceContextAgent(self.config)
            self.agents["GenosAgent"] = GenosAgent(self.config)
            self.agents["ScoringAgent"] = ScoringAgent(self.config)
            self.agents["EvidenceRAGAgent"] = EvidenceRAGAgent(self.config)
            self.agents["ReportAgent"] = ReportAgent(self.config)
            self.agents["ConsistencyAgent"] = ConsistencyAgent(self.config)

            logger.info(f"✓ 初始化 {len(self.agents)} 个 executor agents")
        except Exception as e:
            logger.error(f"✗ 初始化 agents 失败: {e}")
            raise

    def execute_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行任务计划

        Args:
            plan: 执行计划字典

        Returns:
            执行结果字典
        """
        logger.info("=" * 60)
        logger.info("开始执行任务计划")
        logger.info("=" * 60)

        results = {}
        tasks = plan["tasks"]

        for task in sorted(tasks, key=lambda x: x["step"]):
            try:
                logger.info(f"\n[Step {task['step']}] {task['name']}: {task['description']}")

                # 解析依赖的输出
                resolved_input = self._resolve_inputs(task["input"], results)
                task["input"] = resolved_input

                # 执行任务
                agent_name = task["agent"]
                if agent_name not in self.agents:
                    raise ValueError(f"未知的 agent: {agent_name}")

                agent = self.agents[agent_name]
                result = agent.execute(task)

                # 保存结果
                results[task["name"]] = {
                    "status": result.get("status", "unknown"),
                    "output": task["output"],
                    "result": result
                }

                logger.info(f"✓ {task['name']} 完成")

            except Exception as e:
                logger.error(f"✗ {task['name']} 失败: {e}")
                results[task["name"]] = {
                    "status": "failed",
                    "error": str(e)
                }
                # 继续执行或中断
                if self.config.get("execution", {}).get("stop_on_error", True):
                    logger.error("执行中断")
                    break

        logger.info("\n" + "=" * 60)
        logger.info("任务计划执行完成")
        logger.info("=" * 60)

        return results

    def _resolve_inputs(self, task_input: Dict, results: Dict) -> Dict:
        """
        解析任务输入中的依赖引用

        Args:
            task_input: 任务输入字典
            results: 之前任务的执行结果

        Returns:
            解析后的输入字典
        """
        resolved = {}

        for key, value in task_input.items():
            if isinstance(value, str) and value.startswith("${output."):
                # 解析引用：${output.task_name.output_key}
                ref = value[9:-1]  # 移除 ${output. 和 }
                parts = ref.split(".")
                task_name = parts[0]
                output_key = parts[1]

                if task_name in results:
                    resolved[key] = results[task_name]["output"][output_key]
                else:
                    raise ValueError(f"未找到依赖任务的输出: {task_name}")
            elif isinstance(value, dict):
                resolved[key] = self._resolve_inputs(value, results)
            else:
                resolved[key] = value

        return resolved


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 2:
        print("用法: python agents/executor.py <plan.yaml>")
        sys.exit(1)

    plan_file = sys.argv[1]

    # 加载计划
    with open(plan_file) as f:
        plan = yaml.safe_load(f)

    # 加载配置
    config_snapshot = plan["metadata"]["config_snapshot"]

    # 执行计划
    executor = ExecutorScheduler(config_snapshot)
    results = executor.execute_plan(plan)

    # 输出结果
    print("\n=== 执行结果 ===")
    for task_name, result in results.items():
        status = result["status"]
        print(f"  {task_name}: {status}")
