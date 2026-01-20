# Genos DCS API 配置指南

## ✅ 已完成的改造

项目已从**本地 HTTP 服务**切换到**华大基因官方 DCS 云 API**。

### 改造内容

1. **tools/genos_client.py** - 完全重写
   - ✅ 使用官方 Genos SDK (`../Genos/sdk/genos`)
   - ✅ 调用 DCS 云 API (`https://cloud.stomics.tech`)
   - ✅ 支持 API Token 认证
   - ✅ 保留模拟模式用于测试

2. **configs/run.yaml** - 更新配置
   - ✅ 移除本地服务器地址
   - ✅ 添加 API Token 配置
   - ✅ 模型名称改为官方格式 (`Genos-1.2B`)

## 🔑 获取 API Token

### 方法 1: 从华大基因官网获取

1. 访问 [https://cloud.stomics.tech](https://cloud.stomics.tech)
2. 注册/登录账号
3. 进入 API 管理页面
4. 创建新的 API Token
5. 复制 Token (格式类似: `sk-xxxxxxxxxxxxx`)

### 方法 2: 使用已有 Token

如果您已经有 Token，请跳过上述步骤。

## ⚙️ 配置 API Token

### 方式 1: 环境变量（推荐）

**Windows (PowerShell)**:
```powershell
# 临时设置（当前会话有效）
$env:GENOS_API_TOKEN="your_token_here"

# 永久设置（系统环境变量）
[System.Environment]::SetEnvironmentVariable("GENOS_API_TOKEN", "your_token_here", "User")
```

**Windows (CMD)**:
```cmd
set GENOS_API_TOKEN=your_token_here
```

**Linux/Mac**:
```bash
export GENOS_API_TOKEN=your_token_here

# 永久设置（添加到 ~/.bashrc 或 ~/.zshrc）
echo 'export GENOS_API_TOKEN=your_token_here' >> ~/.bashrc
source ~/.bashrc
```

### 方式 2: 直接在配置文件中设置（不推荐）

编辑 `configs/run.yaml`:

```yaml
genos:
  api_token: "your_token_here"  # 直接填写 Token
```

⚠️ **安全警告**: 不要将 Token 提交到 Git 仓库！

## 🧪 测试 API 连接

### 测试脚本

运行客户端测试:

```powershell
cd genos-agentic-pipeline\tools
python genos_client.py
```

预期输出:

```
=== 测试模拟模式 ===
✓ Genos 模拟模式已启用

=== 测试 Embedding (Mock) ===
Embedding shape: (1024,)
Embedding mean: 0.5001

=== 测试变异效应 (Mock) ===
cosine_similarity: 0.9876
euclidean_distance: 0.2341
...

=== 测试官方 DCS API ===
✓ Genos DCS 客户端初始化成功: 模型 Genos-1.2B

测试真实 Embedding...
⏱️  Embedding extraction completed in 1.2345s (sequence_length=400)
Real embedding shape: (4096,)
Real embedding mean: 0.0012
```

### 快速验证

```powershell
# 方法 1: Python 命令行
python -c "import os; from tools.genos_client import create_client; client = create_client(); print('✓ API 配置成功' if client.api_token else '✗ 未找到 Token')"

# 方法 2: 检查环境变量
echo $env:GENOS_API_TOKEN  # PowerShell
echo %GENOS_API_TOKEN%     # CMD
```

## 🚀 使用 DCS API 运行分析

### 启用真实 API 模式

确保 `configs/run.yaml` 中 `mock_mode: false`:

```yaml
genos:
  api_token: null  # 从环境变量读取
  model_name: "Genos-1.2B"
  mock_mode: false  # 使用真实 API
```

### 运行完整流程

```powershell
# 设置 Token
$env:GENOS_API_TOKEN="your_token_here"

# 运行分析
python main.py --vcf examples\test.vcf --output runs\dcs_test --sample demo
```

### 运行日志示例

```
============================================================
Genos 多智能体基因组分析系统
============================================================

[阶段 1] Planner: 创建执行计划
  ✓ 创建 7 步任务 DAG
  ✓ 保存计划: runs/dcs_test/plan.yaml

[阶段 2] Executor: 执行任务流
  Step 1/7: variant_filter
    ✓ 过滤 10 个变异，保留 8 个高质量变异

  Step 2/7: sequence_context
    ✓ 提取 8 个变异的序列上下文 (窗口: 2000bp)

  Step 3/7: genos_embedding
    ✓ Genos DCS 客户端初始化成功: 模型 Genos-1.2B
    ⏱️  Embedding extraction completed in 0.8234s (sequence_length=2001)
    ⏱️  Embedding extraction completed in 0.7821s (sequence_length=2001)
    ...
    ✓ 生成 16 个 embeddings (ref + alt)

  Step 4/7: scoring
    ✓ 计算变异效应评分

  Step 5/7: evidence_rag
    ✓ 检索证据

  Step 6/7: report_generation
    ✓ 生成报告: runs/dcs_test/report.md

  Step 7/7: critic_review
    ✓ Critic 审校完成

[阶段 3] 完成
============================================================
```

## 📊 API 使用统计

官方 SDK 提供的 API:

### 1. Embedding Extraction API

```python
client.get_embedding(
    sequence="ATCGATCG...",
    model_name="Genos-1.2B",  # 或 "Genos-10B"
    pooling_method="mean"     # mean/max/last/none
)
```

**响应格式**:
```json
{
  "status": 200,
  "message": "Success",
  "result": {
    "token_count": 512,
    "embedding_shape": [4096],
    "embedding_dim": 4096,
    "embedding": [0.001, 0.002, ...]
  }
}
```

### 2. Variant Prediction API

```python
client.variant_predict(
    assembly="hg38",    # 或 "hg19"
    chrom="chr7",
    pos=140753336,
    ref="A",
    alt="T"
)
```

**响应格式**:
```json
{
  "variant": "chr7:140753336A>T",
  "prediction": "Pathogenic",
  "score_Benign": 0.05,
  "score_Pathogenic": 0.95
}
```

### 3. RNA Coverage Prediction API

```python
client.rna_coverage_track_pred(
    chrom="chr6",
    start_pos=51484075
)
```

## 🔧 常见问题

### Q1: 提示 "官方 Genos SDK 未找到"

**原因**: SDK 路径不正确

**解决方案**:
```powershell
# 检查 SDK 是否存在
ls ..\Genos\sdk\genos

# 如果不存在，确保项目结构:
E:\desktop\Graduation_Project\genos\
├── Genos\
│   └── sdk\
│       └── genos\
│           ├── __init__.py
│           ├── client.py
│           └── ...
└── genos-agentic-pipeline\
    └── tools\
        └── genos_client.py
```

### Q2: API 请求失败 "Authentication failed"

**原因**: Token 无效或未设置

**解决方案**:
```powershell
# 1. 检查 Token 是否设置
echo $env:GENOS_API_TOKEN

# 2. 重新设置 Token
$env:GENOS_API_TOKEN="your_correct_token"

# 3. 测试连接
python tools\genos_client.py
```

### Q3: 想切换回模拟模式测试

**方法 1**: 修改配置文件

编辑 `configs/run.yaml`:
```yaml
genos:
  mock_mode: true  # 启用模拟模式
```

**方法 2**: 临时移除 Token
```powershell
$env:GENOS_API_TOKEN=""  # 清空 Token 会自动启用模拟模式
```

### Q4: Embedding 维度不一致

**问题**: 真实 API 返回 4096 维，模拟模式返回 1024 维

**说明**:
- **Genos-1.2B**: embedding 维度 = 4096
- **Genos-10B**: embedding 维度 = 更高
- **模拟模式**: 固定 1024 维（用于快速测试）

**影响**: 不影响功能，后续计算会自动适配

## 📈 性能优化建议

### 1. 批量处理

目前实现是逐个序列调用 API，可优化为批量:

```python
# 当前（逐个）
for seq in sequences:
    emb = client.embed(seq)

# 优化（批量）
embs = client.embed_batch(sequences)  # 需实现批量 API
```

### 2. 缓存 Embeddings

配置文件中已启用:
```yaml
performance:
  cache_embeddings: true
```

相同序列不会重复调用 API。

### 3. 并行请求

```yaml
performance:
  max_workers: 4  # 调整并行数
```

## 🎯 下一步

### 立即运行

```powershell
# 1. 设置 Token
$env:GENOS_API_TOKEN="your_token_here"

# 2. 运行测试
.\run_fixed_test.bat

# 3. 检查输出
type runs\test\report.md
```

### 生产环境部署

1. **永久设置环境变量**:
   ```powershell
   [System.Environment]::SetEnvironmentVariable("GENOS_API_TOKEN", "your_token", "User")
   ```

2. **配置文件锁定**:
   ```yaml
   genos:
     mock_mode: false  # 禁用模拟模式
   ```

3. **监控 API 用量**:
   - 登录华大云平台查看 API 调用统计
   - 设置用量告警

---

**配置状态**: ✅ 已完成 DCS API 集成
**版本**: v2.0 (DCS API Edition)
**更新时间**: 2026-01-08
