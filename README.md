# Genos 多智能体基因组分析系统

基于本地部署 Genos 服务的端到端变异解读系统，采用 **Planner-Executor-Critic** 多智能体架构。

## ⚡ 一键运行

```powershell
.\run_fixed_test.bat
```

该脚本会自动清理缓存、运行分析流程并显示报告。详细配置说明请查看 [环境配置指南.md](环境配置指南.md)

## 🖥️ 启动 Web 界面 (New!)

本项目提供了交互式的 Web 界面，方便非技术人员使用：

```bash
streamlit run app.py
```

启动后访问: `http://localhost:8501`

## 快速开始

### 1. 安装依赖

```bash
# 使用 uv 安装依赖（推荐）
uv pip install -r requirements.txt

# 或使用 pip
pip install -r requirements.txt
```

**注意**: `pysam` 和 `pybigwig` 在 Windows 上需要编译环境，如果安装失败系统会使用模拟数据。

### 2. 配置 Genos 服务

本系统采用 **Server-Client** 架构：
*   **服务端**: 部署在高性能计算节点 (`172.16.227.27`)，运行 **Genos-10B** (百亿参数级生物大模型)。
*   **客户端**: 本地运行 Agentic Pipeline，通过 HTTP 请求调用远程算力。

默认配置 (`configs/run.yaml`):
```yaml
genos:
  server_url: "http://172.16.227.27:8010"
  model_name: "10B"
```

这种架构使得用户可以在普通笔记本上运行复杂的基因组分析，将计算负载卸载到远程服务器。

```bash
cd ..\genos-server
python genos_server.py --model_path_prefix "E:\path\to\models\BGI-HangzhouAI\"
```

如需修改，编辑 `configs/run.yaml` 或设置环境变量 `GENOS_SERVER_URL`:

```python
def create_client(
    server_url: str = "http://your-server:port",  # 或使用 GENOS_SERVER_URL
    model_name: str = "1.2B",
    timeout: int = 60
) -> GenosClient:
    return GenosClient(server_url=server_url, model_name=model_name, timeout=timeout)
```

### 3. 运行分析

```bash
# 完整分析流程
python main.py --vcf examples/test.vcf --output runs/test_run --sample test_sample

# 指定表型信息
python main.py --vcf data.vcf --output runs/my_run --phenotype "发育迟缓,癫痫"

# 仅生成执行计划（不执行）
python main.py --vcf data.vcf --output runs/my_run --plan-only

# 执行已有计划
python main.py --execute-plan runs/my_run/plan.yaml
```

## 系统架构

```
Planner (规划智能体)
    ↓ 生成任务 DAG
Executor (执行智能体)
    ├─ Step 1: 变异筛选 (VariantFilterAgent)
    ├─ Step 2: 序列上下文提取 (SequenceContextAgent)
    ├─ Step 3: Genos Embedding 生成 (GenosAgent)
    ├─ Step 4: 变异效应评分 (ScoringAgent)
    ├─ Step 5: 证据检索 RAG (EvidenceRAGAgent)
    └─ Step 6: 报告生成 (ReportAgent)
    ↓
Critic (审校智能体)
    └─ 一致性验证 & 证据归因 (ConsistencyAgent)
```

## 项目结构

```
genos-agentic-pipeline/
├── agents/
│   ├── planner.py               # Planner: 任务规划与 DAG 生成
│   ├── executor.py              # Executor: 调度器
│   ├── executor/
│   │   ├── variant_filter.py   # 变异筛选
│   │   ├── sequence_context.py # 序列上下文提取
│   │   ├── genos_agent.py      # Genos embedding 生成
│   │   ├── scoring.py          # 变异效应评分
│   │   ├── evidence_rag.py     # 证据检索 (RAG)
│   │   └── report.py           # 报告生成
│   └── critic/
│       └── consistency.py      # Critic: 一致性检查
├── tools/
│   ├── genos_client.py          # Genos 本地服务客户端
│   └── fasta_utils.py           # FASTA 序列处理
├── configs/
│   └── run.yaml                 # 系统配置
├── main.py                      # 主入口程序
└── README.md
```

## 配置说明

编辑 `configs/run.yaml`:

```yaml
# Genos 模型配置 (连接本地服务)
genos:
  server_url: "http://127.0.0.1:8000"
  model_name: "1.2B"     # 或 "10B"
  pooling: "mean"        # mean/max/last/none
  timeout: 60

# 变异筛选参数
variant_filter:
  min_quality: 30
  max_population_freq: 0.01
  consequence_types:
    - "stop_gained"
    - "frameshift_variant"
    - "missense_variant"
    # ... 其他功能类型

# 序列窗口配置
sequence_context:
  window_size: 2000      # 单侧窗口大小 (bp)
  validate_ref: true     # 验证参考碱基

# 评分配置
scoring:
  method: "genos_embedding"
  genos_weights:
    cosine_similarity: -0.5
    euclidean_distance: 0.3
    diff_magnitude: 0.2
  thresholds:
    high_impact: 0.7
    moderate_impact: 0.4
    low_impact: 0.2
```

## 核心功能

### 1. Planner Agent (规划)
- 根据输入 VCF 和配置生成任务 DAG
- 定义任务依赖关系和执行顺序
- 保存执行计划供后续使用

### 2. Executor Agents (执行)

#### VariantFilterAgent
- 基于质量、频率、功能类型筛选变异
- 支持自定义筛选规则

#### SequenceContextAgent
- 从参考基因组提取变异位点的序列窗口
- 构建 ref/alt 序列对

#### GenosAgent
- 调用本地 Genos 服务生成 embedding
- 计算 ref/alt embedding 差异
- 支持批量处理

#### ScoringAgent
- 基于 embedding 差异计算变异效应评分
- 使用余弦相似度、欧氏距离等多种指标
- 分类变异影响等级 (HIGH/MODERATE/LOW)

#### EvidenceRAGAgent
- 从 ClinVar、gnomAD、OMIM 等知识库检索证据
- 基于 RAG 框架进行证据归因
- 支持多来源证据整合

#### ReportAgent
- 生成 Markdown 格式分析报告
- 包含摘要、Top 变异、证据汇总和建议

### 3. Critic Agent (审校)

#### ConsistencyAgent
- 检查注释、评分、证据间的一致性
- 验证数据完整性和逻辑正确性
- 生成审校报告

## 使用示例

### 命令行使用

```bash
# 基本用法
python main.py --vcf examples/test.vcf --output runs/test --sample patient001

# 带表型
python main.py --vcf data.vcf --output runs/run001 --phenotype "发育迟缓,智力障碍"

# 调试模式
python main.py --vcf data.vcf --output runs/debug --log-level DEBUG
```

### Python API 使用

```python
from tools.genos_client import create_client

# 创建客户端 (连接本地服务)
client = create_client(
    server_url="http://127.0.0.1:8000",
    model_name="1.2B",
    timeout=60
)

# 生成 embedding
sequence = "ATCGATCGATCG" * 100
embedding = client.embed(sequence, pooling="mean", normalize=True)
print(f"Embedding shape: {embedding.shape}")

# 预测变异效应
ref_seq = "ATCGATCG" * 50
alt_seq = "ATCGTTCG" * 50  # 中间有一个 A→T 变异
effect = client.predict_variant_effect(ref_seq, alt_seq)
print(f"Impact score: {effect['impact_score']:.4f}")
print(f"Cosine similarity: {effect['cosine_similarity']:.4f}")

# 批量处理
sequences = [seq1, seq2, seq3, ...]
embeddings = client.embed_batch(sequences)
```

## 输出文件说明

运行完成后会在输出目录生成以下文件:

```
runs/test_run/
├── plan.yaml                    # 执行计划
├── variants.filtered.vcf        # 筛选后的变异
├── contexts.jsonl               # 序列上下文 (ref/alt 窗口)
├── genos_embeddings.parquet     # Genos embedding 结果
├── scores.tsv                   # 变异效应评分
├── evidence.json                # 证据检索结果
├── report.md                    # 分析报告
├── critic_report.json           # Critic 审校报告
└── pipeline.log                 # 运行日志
```

## Windows 用户注意

`pysam` 和 `pyfaidx` 在 Windows 上需要 C 编译器，如果安装失败：

1. **使用 WSL (推荐)**
   ```bash
   wsl
   cd /mnt/e/desktop/Graduation_Project/genos/genos-agentic-pipeline
   uv pip install -r requirements.txt
   ```

2. **使用 Conda**
   ```bash
   conda install -c bioconda pysam pyfaidx
   uv pip install -r requirements.txt
   ```

3. **跳过可选依赖**
   系统会在缺少这些包时自动使用模拟数据，不影响核心功能测试

## 常见问题

### Q: 如何连接到自己部署的 Genos 服务?
A: 修改 `tools/genos_client.py` 中的 `server_url` 参数，或在代码中直接指定

### Q: 没有参考基因组怎么办?
A: 系统支持模拟数据模式，会自动生成测试序列用于演示

### Q: 如何自定义筛选规则?
A: 编辑 `configs/run.yaml` 中的 `variant_filter` 部分

### Q: 支持哪些基因组版本?
A: 默认支持 hg38 和 hg19，可在配置文件中指定

## 技术细节

### Genos Embedding 变异效应评分

系统使用 Genos 基础模型生成参考序列和变异序列的 embedding，然后计算：

1. **余弦相似度** (Cosine Similarity): 衡量两个 embedding 的方向相似性
2. **欧氏距离** (Euclidean Distance): 衡量 embedding 空间中的直接距离
3. **差异幅度** (Diff Magnitude): embedding 向量逐元素差异的平均值

综合评分公式:
```
impact_score = -0.5 * (1 - cosine_sim) + 0.3 * euclidean_dist + 0.2 * diff_magnitude
```

### 多智能体协作流程

```
1. Planner 分析任务需求
   ↓
2. 生成 7 步任务 DAG
   ↓
3. Executor 按依赖顺序执行
   - 每步完成后输出可被下一步引用
   - 支持 ${output.task_name.output_key} 语法
   ↓
4. Critic 验证所有输出
   - 检查数据一致性
   - 验证证据归因
   ↓
5. 生成最终报告
```

## 参考资料

- [Genos GitHub](https://github.com/BGI-HangzhouAI/Genos)
- [Genos 论文](https://doi.org/10.1093/gigascience/giaf132)
- [本地部署服务代码](../Genos/Adaptation/genos_server.py)

## 许可证

MIT License
