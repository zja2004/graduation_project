#!/usr/bin/env python3
"""
Genos 多智能体基因组分析系统 - 主入口
Planner-Executor-Critic 架构
"""

import argparse
import logging
import yaml
from pathlib import Path

import sys

# Windows console encoding fix
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

from agents.planner import PlannerAgent
from agents.scheduler import ExecutorScheduler


def setup_logging(log_level: str = "INFO", log_file: str = None):
    """配置日志系统"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    handlers = [logging.StreamHandler()]
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )




def main():
    parser = argparse.ArgumentParser(
        description="Genos 多智能体基因组分析系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行完整分析
  python main.py --vcf examples/test.vcf --output runs/test_run --sample test_sample

  # 指定表型
  python main.py --vcf data.vcf --output runs/my_run --phenotype "发育迟缓,癫痫"

  # 仅生成计划
  python main.py --vcf data.vcf --output runs/my_run --plan-only

  # 执行已有计划
  python main.py --execute-plan runs/my_run/plan.yaml
        """
    )

    parser.add_argument(
        "--vcf",
        type=str,
        help="输入 VCF 文件路径"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出目录"
    )
    parser.add_argument(
        "--sample",
        type=str,
        default="sample",
        help="样本名称 (默认: sample)"
    )
    parser.add_argument(
        "--phenotype",
        type=str,
        help="表型描述（用逗号分隔）"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/run.yaml",
        help="配置文件路径 (默认: configs/run.yaml)"
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="仅生成执行计划，不执行"
    )
    parser.add_argument(
        "--execute-plan",
        type=str,
        help="执行已有的计划文件"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别 (默认: INFO)"
    )

    args = parser.parse_args()

    # 加载配置
    with open(args.config, encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 设置日志
    log_file = None
    if args.output:
        log_file = str(Path(args.output) / "pipeline.log")
    setup_logging(args.log_level, log_file)

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Genos 多智能体基因组分析系统")
    logger.info("=" * 60)

    # 执行模式 1: 执行已有计划
    if args.execute_plan:
        logger.info(f"执行已有计划: {args.execute_plan}")
        with open(args.execute_plan, encoding='utf-8') as f:
            plan = yaml.safe_load(f)

        config_snapshot = plan["metadata"]["config_snapshot"]
        executor = ExecutorScheduler(config_snapshot)
        results = executor.execute_plan(plan)

        # 输出结果摘要
        print("\n" + "=" * 60)
        print("执行结果摘要")
        print("=" * 60)
        for task_name, result in results.items():
            status = result["status"]
            print(f"  {task_name}: {status}")

        return

    # 执行模式 2: 完整流程
    if not args.vcf or not args.output:
        parser.error("需要指定 --vcf 和 --output 参数")

    # Step 1: 创建计划
    logger.info("\n[阶段 1] Planner: 创建执行计划")
    planner = PlannerAgent(config)
    plan = planner.create_plan(
        input_vcf=args.vcf,
        output_dir=args.output,
        sample_name=args.sample,
        phenotype=args.phenotype
    )

    # 验证计划
    if not planner.validate_plan(plan):
        logger.error("执行计划验证失败")
        return

    # 保存计划
    plan_file = Path(args.output) / "plan.yaml"
    planner.save_plan(plan, str(plan_file))

    if args.plan_only:
        logger.info(f"\n✓ 执行计划已保存: {plan_file}")
        logger.info("使用 --execute-plan 参数执行该计划")
        return

    # Step 2: 执行计划
    logger.info("\n[阶段 2] Executor: 执行任务流")
    executor = ExecutorScheduler(config)
    results = executor.execute_plan(plan)

    # Step 3: 输出结果
    logger.info("\n[阶段 3] 完成")
    print("\n" + "=" * 60)
    print("分析完成")
    print("=" * 60)
    print(f"输出目录: {args.output}")
    print("\n主要输出文件:")
    print(f"  - 执行计划: {plan_file}")
    print(f"  - 过滤后变异: {Path(args.output) / 'variants.filtered.vcf'}")
    print(f"  - 序列上下文: {Path(args.output) / 'contexts.jsonl'}")
    print(f"  - Genos embeddings: {Path(args.output) / 'genos_embeddings.parquet'}")
    print(f"  - 变异评分: {Path(args.output) / 'scores.tsv'}")
    print(f"  - 证据检索: {Path(args.output) / 'evidence.json'}")
    print(f"  - 分析报告: {Path(args.output) / 'report.md'}")
    print(f"  - Critic 审校: {Path(args.output) / 'critic_report.json'}")
    print()

    # 执行结果摘要
    print("任务执行状态:")
    for task_name, result in results.items():
        status = result["status"]
        status_symbol = "✓" if status == "success" else "✗"
        print(f"  {status_symbol} {task_name}: {status}")
    print()


if __name__ == "__main__":
    main()
