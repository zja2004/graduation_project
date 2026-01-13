# 测试数据说明

## test.vcf

包含 10 个测试变异的 VCF 文件，用于演示系统功能。

### 变异列表

| ID | 位置 | Ref→Alt | 功能 | 频率 | 质量 |
|----|------|---------|------|------|------|
| rs1 | chr1:100001 | A→G | missense | 0.001 | 50 |
| rs2 | chr1:200002 | C→T | missense | 0.005 | 60 |
| rs3 | chr1:300003 | G→A | synonymous | 0.002 | 45 |
| rs4 | chr6:51484075 | T→G | missense | 0.0001 | 70 |
| rs5 | chr6:51484100 | A→T | stop_gained | 0.003 | 55 |
| rs6 | chr7:117559590 | C→G | frameshift | 0.0005 | 65 |
| rs7 | chr7:117559600 | G→C | missense | 0.008 | 48 |
| rs8 | chr1:400004 | TG→T | frameshift | 0.006 | 40 |
| rs9 | chr1:500005 | A→ACG | inframe_insertion | 0.004 | 35 |
| rs10 | chr6:51484200 | ATCG→A | inframe_deletion | 0.007 | 30 |

### 特点

- 包含不同类型的变异: SNV、Indel
- 包含不同功能影响: 错义、无义、移码、同义
- 覆盖不同染色体: chr1, chr6, chr7
- 频率范围: 0.0001 - 0.008
- 质量分数范围: 30 - 70

## 使用方法

```bash
# 基本测试
python main.py --vcf examples/test.vcf --output runs/test --sample demo

# 带表型
python main.py --vcf examples/test.vcf --output runs/test --phenotype "发育迟缓"

# 仅生成计划
python main.py --vcf examples/test.vcf --output runs/test --plan-only
```

## 预期结果

系统会筛选出高质量、低频率的功能性变异，预计保留 6-8 个变异进行后续分析。

高影响变异（预期）:
- rs5 (stop_gained)
- rs6 (frameshift)
- rs8 (frameshift)
