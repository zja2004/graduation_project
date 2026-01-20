# 📚 知识库部署快速指南

## 🚀 快速开始（推荐）

### 一键部署

```powershell
.\一键部署完整知识库.bat
```

这个脚本会自动：
1. ✅ 下载所有必需的知识库数据（~3.3 GB）
2. ✅ 构建 SQLite 索引数据库
3. ✅ 验证数据完整性
4. ✅ 运行测试用例

**预计时间**: 20-40 分钟（取决于网速）

---

## 📋 分步部署

如果一键部署失败，或想自定义配置，可以分步执行：

### 步骤 1: 下载数据

```powershell
# 方式 1: 使用脚本（推荐）
.\下载知识库.bat

# 方式 2: 使用 Python
python tools/download_knowledge_bases.py

# 方式 3: 手动下载（见下方链接）
```

### 步骤 2: 构建索引

```powershell
# 方式 1: 使用脚本（推荐）
.\构建知识库索引.bat

# 方式 2: 使用 Python
python tools/build_knowledge_index_enhanced.py --chromosomes 22
```

### 步骤 3: 验证

```powershell
# 查看数据库统计
python -c "import sqlite3; conn=sqlite3.connect('data/knowledge/knowledge.db'); c=conn.cursor(); tables=['clinvar','gnomad','gene_info','pharmgkb_genes']; [c.execute(f'SELECT COUNT(*) FROM {t}') or print(f'{t}: {c.fetchone()[0]:,}') for t in tables]"
```

### 步骤 4: 测试

```powershell
$env:GENOS_API_TOKEN="sk-NSsjvPwgyb0KhiDA7uaiXVsnKaz_4mryvt530EFS5SqcI8o-"
python main.py --vcf examples\test_with_genes.vcf --output runs\test
start runs\test\report.html
```

---

## 📊 数据源说明

| 数据源 | 大小 | 自动下载 | 说明 |
|--------|------|----------|------|
| **ClinVar** | 2 GB | ✅ 是 | 临床验证的变异数据库 |
| **gnomAD chr22** | 1.2 GB | ✅ 是 | 人群频率数据（测试用） |
| **Gene Info** | 50 MB | ✅ 是 | 基因功能注释 |
| **PharmGKB** | 15 MB | ✅ 是 | 药物基因组学数据 |
| **OMIM** | 100 MB | ❌ 需授权 | 遗传疾病数据库 |
| **COSMIC** | 500 MB | ❌ 需授权 | 癌症突变数据库 |

---

## 🔗 手动下载链接

### ClinVar (必需)
```
https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz
```
保存到: `data/knowledge/raw/clinvar.vcf.gz`

### gnomAD (推荐)
```
# chr22 (测试用)
https://gnomad-public-us-east-1.s3.amazonaws.com/release/3.1.2/vcf/genomes/gnomad.genomes.v3.1.2.sites.chr22.vcf.bgz

# 完整基因组 (生产用，89 GB)
https://gnomad-public-us-east-1.s3.amazonaws.com/release/3.1.2/vcf/genomes/gnomad.genomes.v3.1.2.sites.vcf.bgz
```
保存到: `data/knowledge/raw/gnomad.chr22.vcf.bgz`

### Gene Info (推荐)
```
https://ftp.ncbi.nlm.nih.gov/gene/DATA/GENE_INFO/Mammalia/Homo_sapiens.gene_info.gz
```
保存到: `data/knowledge/raw/Homo_sapiens.gene_info.gz`

### PharmGKB (可选)
```
https://api.pharmgkb.org/v1/download/file/data/genes.zip
https://api.pharmgkb.org/v1/download/file/data/clinicalVariants.zip
```
保存到: `data/knowledge/raw/pharmgkb_*.zip`

### OMIM (需要授权)
1. 访问: https://www.omim.org/
2. 注册并申请学术访问
3. 下载数据文件
4. 保存到: `data/knowledge/raw/omim.txt`

### COSMIC (需要授权)
1. 访问: https://cancer.sanger.ac.uk/cosmic
2. 注册免费学术账号
3. 下载 VCF 文件
4. 保存到: `data/knowledge/raw/cosmic.vcf.gz`

---

## 💾 磁盘空间需求

### 测试模式（默认）
- 下载: ~3.3 GB
- 索引: ~50 MB
- **总计**: ~3.4 GB

### 生产模式（完整）
- 下载: ~92 GB
- 索引: ~5 GB
- **总计**: ~97 GB

---

## ⚙️ 自定义配置

### 仅下载特定染色体

```powershell
# 常见癌症相关染色体
python tools/build_knowledge_index_enhanced.py --chromosomes 7 13 17 22
```

### 使用本地已下载的文件

```powershell
python tools/build_knowledge_index_enhanced.py \
    --clinvar path/to/clinvar.vcf.gz \
    --gnomad path/to/gnomad.vcf.bgz \
    --gene-info path/to/gene_info.gz
```

### 增量更新（定期）

ClinVar 每月更新，建议定期重新下载：

```powershell
# 备份旧数据库
copy data\knowledge\knowledge.db data\knowledge\knowledge.db.bak

# 重新下载和构建
python tools/download_knowledge_bases.py
python tools/build_knowledge_index_enhanced.py --chromosomes 22
```

---

## 🔧 故障排除

### 问题 1: 下载失败

**症状**: `ConnectionError` 或超时

**解决方案**:
```powershell
# 使用下载工具重试
aria2c -x 16 -s 16 <URL>

# 或使用浏览器手动下载后放到 data/knowledge/raw/
```

### 问题 2: 磁盘空间不足

**解决方案**:
```powershell
# 仅下载必需数据
python tools/download_knowledge_bases.py

# 构建后删除原始文件
del data\knowledge\raw\*.vcf.gz
```

### 问题 3: 内存不足

**解决方案**:
编辑 `tools/build_knowledge_index_enhanced.py`:
```python
BATCH_SIZE = 500  # 从 1000 降低
```

### 问题 4: 数据库查询慢

**解决方案**:
```powershell
# 重建索引
python -c "import sqlite3; conn=sqlite3.connect('data/knowledge/knowledge.db'); c=conn.cursor(); c.execute('VACUUM'); c.execute('ANALYZE'); conn.commit()"
```

---

## 📈 性能优化

### 使用 SSD

将 `data/knowledge/` 移动到 SSD 分区可显著提升查询速度。

### 分批构建

对于大规模数据：
```powershell
# 逐染色体构建
for ($i=1; $i -le 22; $i++) {
    python tools/build_knowledge_index_enhanced.py --chromosomes $i
}
```

### 内存优化

如果内存充足（>16GB），可以增加批处理大小：
```python
BATCH_SIZE = 5000  # 默认 1000
```

---

## ✅ 验证数据完整性

### 查看表结构

```python
import sqlite3
conn = sqlite3.connect('data/knowledge/knowledge.db')
c = conn.cursor()

# 列出所有表
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("数据库表:", [row[0] for row in c.fetchall()])

# 查看表结构
c.execute("PRAGMA table_info(clinvar)")
print("ClinVar 表结构:", c.fetchall())
```

### 查询示例数据

```python
# ClinVar 致病变异
c.execute("SELECT * FROM clinvar WHERE clnsig LIKE '%Pathogenic%' LIMIT 5")
for row in c.fetchall():
    print(row)

# gnomAD 罕见变异
c.execute("SELECT * FROM gnomad WHERE af < 0.001 LIMIT 5")
for row in c.fetchall():
    print(row)
```

### 统计信息

```python
tables = ['clinvar', 'gnomad', 'gene_info', 'pharmgkb_genes']
for table in tables:
    c.execute(f"SELECT COUNT(*) FROM {table}")
    count = c.fetchone()[0]
    print(f"{table}: {count:,} 条记录")
```

---

## 🎯 使用示例

### 完整分析流程

```powershell
# 1. 设置 API Token
$env:GENOS_API_TOKEN="sk-NSsjvPwgyb0KhiDA7uaiXVsnKaz_4mryvt530EFS5SqcI8o-"

# 2. 运行分析
python main.py \
    --vcf your_variants.vcf \
    --output runs/analysis \
    --sample patient_001

# 3. 查看报告
start runs/analysis/report.html
```

### 批量分析

```powershell
$samples = @("sample1", "sample2", "sample3")
foreach ($sample in $samples) {
    python main.py \
        --vcf "vcf/${sample}.vcf" \
        --output "runs/${sample}" \
        --sample $sample
}
```

---

## 📞 获取帮助

### 查看日志

```powershell
# 下载日志
type logs\download.log

# 构建日志
type logs\build.log

# 分析日志
type runs\test\pipeline.log
```

### 详细文档

- [知识库下载指南.md](知识库下载指南.md) - 完整文档
- [AI解释功能使用指南.md](AI解释功能使用指南.md) - AI 功能说明
- [修复基因字段.md](修复基因字段.md) - 故障排除

---

## 🎉 部署成功！

完成部署后，您将拥有：

✅ **多源知识库**: ClinVar + gnomAD + Gene Info + PharmGKB
✅ **快速查询**: SQLite 索引优化
✅ **AI 解释**: DeepSeek LLM 通俗化说明
✅ **美观报告**: 渐变样式 HTML 输出

现在可以分析您的基因组数据了！

```powershell
python main.py --vcf your_data.vcf --output runs/result
```

---

**版本**: v3.0
**更新时间**: 2026-01-15
**支持**: GitHub Issues
