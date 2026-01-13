# 快速开始指南

## 测试 VCF 文件位置

测试数据已准备好在 `examples/test.vcf`，包含 10 个模拟变异。

## 三种运行方式

### 方式 1: 一键测试脚本（推荐）

**Windows:**
```bash
run_test.bat
```

**Linux/Mac:**
```bash
./run_test.sh
```

### 方式 2: 命令行直接运行

```bash
# 基本测试
python main.py --vcf examples/test.vcf --output runs/test --sample demo

# 带表型信息
python main.py --vcf examples/test.vcf --output runs/phenotype_test --phenotype "发育迟缓,癫痫"

# 调试模式
python main.py --vcf examples/test.vcf --output runs/debug --log-level DEBUG
```

### 方式 3: 分步执行（用于学习流程）

```bash
# 步骤 1: 仅生成执行计划
python main.py --vcf examples/test.vcf --output runs/my_run --plan-only

# 查看计划
cat runs/my_run/plan.yaml  # Linux/Mac
type runs\my_run\plan.yaml  # Windows

# 步骤 2: 执行计划
python main.py --execute-plan runs/my_run/plan.yaml
```

## 预期输出

运行成功后，会在输出目录生成以下文件:

```
runs/test/
├── plan.yaml                    # 执行计划（DAG 定义）
├── variants.filtered.vcf        # 筛选后的变异（6-8个）
├── contexts.jsonl               # 序列上下文（ref/alt 窗口）
├── genos_embeddings.parquet     # Genos embedding 结果
├── scores.tsv                   # 变异效应评分
├── evidence.json                # 证据检索结果
├── report.md                    # 📊 分析报告（主要结果）
├── critic_report.json           # Critic 审校报告
└── pipeline.log                 # 运行日志
```

## 查看结果

### 1. 查看分析报告

```bash
# Windows
notepad runs\test\report.md

# Linux/Mac
cat runs/test/report.md
```

### 2. 查看执行日志

```bash
# Windows
type runs\test\pipeline.log

# Linux/Mac
tail -f runs/test/pipeline.log
```

### 3. 查看变异评分

```bash
# 使用 Excel/LibreOffice 打开
runs/test/scores.tsv

# 或使用 pandas
python -c "import pandas as pd; print(pd.read_csv('runs/test/scores.tsv', sep='\t'))"
```

## 常见问题

### Q1: 提示找不到 VCF 文件

确保使用正确的路径:
```bash
# 相对路径
python main.py --vcf examples/test.vcf --output runs/test

# 绝对路径
python main.py --vcf E:\desktop\Graduation_Project\genos\genos-agentic-pipeline\examples\test.vcf --output runs/test
```

### Q2: Genos 服务连接失败

检查 `configs/run.yaml` 的 `genos.server_url` 或 `GENOS_SERVER_URL`:
```python
server_url: str = "http://127.0.0.1:8000"  # 确认服务是否运行
```

测试连接:
```bash
curl http://127.0.0.1:8000/health  # Linux/Mac
```

### Q3: 缺少依赖包

```bash
# 核心依赖
pip install pyyaml numpy pandas requests pyarrow

# 可选依赖（用于真实基因组）
pip install pysam pyfaidx  # 可能需要 WSL 或 Conda
```

### Q4: 想使用自己的 VCF 文件

```bash
python main.py --vcf /path/to/your.vcf --output runs/my_analysis --sample patient001
```

## 下一步

1. **查看报告**: 打开 `runs/test/report.md` 了解分析结果
2. **理解流程**: 查看 `runs/test/plan.yaml` 了解任务 DAG
3. **自定义配置**: 编辑 `configs/run.yaml` 调整筛选参数
4. **使用真实数据**: 准备自己的 VCF 和参考基因组

## 技术支持

- 查看完整文档: [README.md](README.md)
- 查看示例说明: [examples/README.md](examples/README.md)
- 查看配置文件: [configs/run.yaml](configs/run.yaml)
