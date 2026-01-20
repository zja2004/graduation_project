"""
增强版知识库索引构建工具
支持 ClinVar, gnomAD, Gene Info, PharmGKB 等多源数据集成
"""

import os
import sqlite3
import gzip
import json
import logging
import argparse
import zipfile
from pathlib import Path
from typing import Dict, Any
try:
    from tqdm import tqdm as tqdm_bar
except ImportError:
    def tqdm_bar(iterable, desc="Processing", unit="items"):
        return iterable

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 确保输出目录存在
os.makedirs("data/knowledge", exist_ok=True)

RAW_DATA_DIR = Path("data/knowledge/raw")


def setup_db(db_path: str):
    """创建 SQLite 表结构"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # 1. ClinVar 表
    c.execute('''
        CREATE TABLE IF NOT EXISTS clinvar (
            chrom TEXT,
            pos INTEGER,
            ref TEXT,
            alt TEXT,
            variant_id TEXT,
            clnsig TEXT,      -- Clinical Significance
            clndn TEXT,       -- Disease Name
            clnrevstat TEXT,  -- Review Status
            info TEXT,        -- Full INFO string
            PRIMARY KEY (chrom, pos, ref, alt)
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_clinvar_pos ON clinvar (chrom, pos)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_clinvar_gene ON clinvar (variant_id)')

    # 2. gnomAD 表
    c.execute('''
        CREATE TABLE IF NOT EXISTS gnomad (
            chrom TEXT,
            pos INTEGER,
            ref TEXT,
            alt TEXT,
            af REAL,          -- Allele Frequency
            ac INTEGER,       -- Allele Count
            an INTEGER,       -- Allele Number
            nhomalt INTEGER,  -- Number of Homozygous Alternates
            PRIMARY KEY (chrom, pos, ref, alt)
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_gnomad_pos ON gnomad (chrom, pos)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_gnomad_af ON gnomad (af)')

    # 3. Gene Info 表
    c.execute('''
        CREATE TABLE IF NOT EXISTS gene_info (
            gene_id INTEGER PRIMARY KEY,
            symbol TEXT,
            description TEXT,
            chromosome TEXT,
            map_location TEXT,
            type_of_gene TEXT,
            synonyms TEXT
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_gene_symbol ON gene_info (symbol)')

    # 4. PharmGKB 表
    c.execute('''
        CREATE TABLE IF NOT EXISTS pharmgkb_genes (
            pharmgkb_id TEXT PRIMARY KEY,
            symbol TEXT,
            name TEXT,
            alternate_names TEXT,
            alternate_symbols TEXT,
            is_vip INTEGER,   -- Very Important Pharmacogene
            has_variant_annotation INTEGER
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_pharmgkb_symbol ON pharmgkb_genes (symbol)')

    c.execute('''
        CREATE TABLE IF NOT EXISTS pharmgkb_variants (
            variant_id TEXT,
            gene TEXT,
            chromosome TEXT,
            position INTEGER,
            rsid TEXT,
            genotype TEXT,
            clinical_annotation TEXT,
            level_of_evidence TEXT,
            phenotype TEXT,
            PRIMARY KEY (variant_id, gene)
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_pharmgkb_var_pos ON pharmgkb_variants (chromosome, position)')

    conn.commit()
    conn.close()
    logger.info("✓ 数据库表结构创建完成")


def parse_clinvar_vcf(vcf_path: Path, db_path: str, chromosomes: list = None):
    """解析 ClinVar VCF 并导入数据库"""
    if not vcf_path.exists():
        logger.error(f"ClinVar 文件未找到: {vcf_path}")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    open_func = gzip.open if str(vcf_path).endswith('.gz') else open
    mode = 'rt' if str(vcf_path).endswith('.gz') else 'r'

    count = 0
    batch = []
    BATCH_SIZE = 1000

    logger.info(f"解析 ClinVar: {vcf_path}")

    try:
        with open_func(vcf_path, mode, encoding='utf-8', errors='ignore') as f:
            for line in tqdm_bar(f, desc="导入 ClinVar", unit=" variants"):
                if line.startswith('#'):
                    continue

                parts = line.strip().split('\t')
                if len(parts) < 8:
                    continue

                chrom = parts[0].replace('chr', '')  # 标准化染色体名称

                # 过滤染色体
                if chromosomes and chrom not in chromosomes:
                    continue

                try:
                    pos = int(parts[1])
                except ValueError:
                    continue

                ref = parts[3]
                alt = parts[4]
                variant_id = parts[2]
                info_str = parts[7]

                # 解析 INFO 字段
                info_dict = {}
                for item in info_str.split(';'):
                    if '=' in item:
                        k, v = item.split('=', 1)
                        info_dict[k] = v

                clnsig = info_dict.get('CLNSIG', '')
                clndn = info_dict.get('CLNDN', '').replace('_', ' ')
                clnrevstat = info_dict.get('CLNREVSTAT', '')

                batch.append((chrom, pos, ref, alt, variant_id, clnsig, clndn, clnrevstat, info_str))
                count += 1

                if len(batch) >= BATCH_SIZE:
                    c.executemany(
                        'INSERT OR REPLACE INTO clinvar VALUES (?,?,?,?,?,?,?,?,?)',
                        batch
                    )
                    batch = []

        # 插入剩余数据
        if batch:
            c.executemany('INSERT OR REPLACE INTO clinvar VALUES (?,?,?,?,?,?,?,?,?)', batch)

        conn.commit()
        logger.info(f"✓ ClinVar 导入完成: {count:,} 条记录")

    except Exception as e:
        logger.error(f"✗ ClinVar 解析失败: {e}")
    finally:
        conn.close()


def parse_gnomad_vcf(vcf_path: Path, db_path: str, chromosomes: list = None):
    """解析 gnomAD VCF 并导入数据库"""
    if not vcf_path.exists():
        logger.error(f"gnomAD 文件未找到: {vcf_path}")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    open_func = gzip.open if str(vcf_path).endswith(('.gz', '.bgz')) else open
    mode = 'rt' if str(vcf_path).endswith(('.gz', '.bgz')) else 'r'

    count = 0
    batch = []
    BATCH_SIZE = 1000

    logger.info(f"解析 gnomAD: {vcf_path}")

    try:
        with open_func(vcf_path, mode, encoding='utf-8', errors='ignore') as f:
            for line in tqdm_bar(f, desc="导入 gnomAD", unit=" variants"):
                if line.startswith('#'):
                    continue

                parts = line.strip().split('\t')
                if len(parts) < 8:
                    continue

                chrom = parts[0].replace('chr', '')

                if chromosomes and chrom not in chromosomes:
                    continue

                try:
                    pos = int(parts[1])
                except ValueError:
                    continue

                ref = parts[3]
                alt = parts[4]
                info_str = parts[7]

                # 解析频率信息
                info_dict = {}
                for item in info_str.split(';'):
                    if '=' in item:
                        k, v = item.split('=', 1)
                        info_dict[k] = v

                try:
                    af = float(info_dict.get('AF', 0))
                    ac = int(info_dict.get('AC', 0))
                    an = int(info_dict.get('AN', 0))
                    nhomalt = int(info_dict.get('nhomalt', 0))
                except (ValueError, TypeError):
                    continue

                batch.append((chrom, pos, ref, alt, af, ac, an, nhomalt))
                count += 1

                if len(batch) >= BATCH_SIZE:
                    c.executemany(
                        'INSERT OR REPLACE INTO gnomad VALUES (?,?,?,?,?,?,?,?)',
                        batch
                    )
                    batch = []

        if batch:
            c.executemany('INSERT OR REPLACE INTO gnomad VALUES (?,?,?,?,?,?,?,?)', batch)

        conn.commit()
        logger.info(f"✓ gnomAD 导入完成: {count:,} 条记录")

    except Exception as e:
        logger.error(f"✗ gnomAD 解析失败: {e}")
    finally:
        conn.close()


def parse_gene_info(gene_info_path: Path, db_path: str):
    """解析 NCBI Gene Info 文件"""
    if not gene_info_path.exists():
        logger.error(f"Gene Info 文件未找到: {gene_info_path}")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    open_func = gzip.open if str(gene_info_path).endswith('.gz') else open
    mode = 'rt' if str(gene_info_path).endswith('.gz') else 'r'

    count = 0
    batch = []
    BATCH_SIZE = 1000

    logger.info(f"解析 Gene Info: {gene_info_path}")

    try:
        with open_func(gene_info_path, mode, encoding='utf-8', errors='ignore') as f:
            header = next(f).strip().split('\t')

            for line in tqdm_bar(f, desc="导入 Gene Info", unit=" genes"):
                parts = line.strip().split('\t')
                if len(parts) < 15:
                    continue

                try:
                    gene_id = int(parts[1])
                    symbol = parts[2]
                    description = parts[8]
                    chromosome = parts[6]
                    map_location = parts[7]
                    type_of_gene = parts[9]
                    synonyms = parts[4]

                    batch.append((gene_id, symbol, description, chromosome, map_location, type_of_gene, synonyms))
                    count += 1

                    if len(batch) >= BATCH_SIZE:
                        c.executemany(
                            'INSERT OR REPLACE INTO gene_info VALUES (?,?,?,?,?,?,?)',
                            batch
                        )
                        batch = []
                except (ValueError, IndexError):
                    continue

        if batch:
            c.executemany('INSERT OR REPLACE INTO gene_info VALUES (?,?,?,?,?,?,?)', batch)

        conn.commit()
        logger.info(f"✓ Gene Info 导入完成: {count:,} 条记录")

    except Exception as e:
        logger.error(f"✗ Gene Info 解析失败: {e}")
    finally:
        conn.close()


def parse_pharmgkb_genes(zip_path: Path, db_path: str):
    """解析 PharmGKB 基因数据"""
    if not zip_path.exists():
        logger.warning(f"PharmGKB 基因文件未找到: {zip_path}")
        return

    logger.info(f"解析 PharmGKB 基因: {zip_path}")

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # 查找 genes.tsv 文件
            genes_file = [f for f in zf.namelist() if 'genes.tsv' in f.lower()][0]

            with zf.open(genes_file) as f:
                lines = f.read().decode('utf-8').split('\n')
                header = lines[0].strip().split('\t')

                count = 0
                batch = []

                for line in tqdm_bar(lines[1:], desc="导入 PharmGKB 基因"):
                    if not line.strip():
                        continue

                    parts = line.strip().split('\t')
                    if len(parts) < 5:
                        continue

                    pharmgkb_id = parts[0]
                    symbol = parts[1] if len(parts) > 1 else ''
                    name = parts[2] if len(parts) > 2 else ''
                    alternate_names = parts[3] if len(parts) > 3 else ''
                    alternate_symbols = parts[4] if len(parts) > 4 else ''
                    is_vip = 1 if len(parts) > 5 and 'VIP' in parts[5] else 0
                    has_variant = 1 if len(parts) > 6 and parts[6] == 'Y' else 0

                    batch.append((pharmgkb_id, symbol, name, alternate_names, alternate_symbols, is_vip, has_variant))
                    count += 1

                    if len(batch) >= 1000:
                        c.executemany(
                            'INSERT OR REPLACE INTO pharmgkb_genes VALUES (?,?,?,?,?,?,?)',
                            batch
                        )
                        batch = []

                if batch:
                    c.executemany('INSERT OR REPLACE INTO pharmgkb_genes VALUES (?,?,?,?,?,?,?)', batch)

                conn.commit()
                logger.info(f"✓ PharmGKB 基因导入完成: {count:,} 条记录")

    except Exception as e:
        logger.error(f"✗ PharmGKB 基因解析失败: {e}")
    finally:
        conn.close()


def build_full_index(args):
    """构建完整的知识库索引"""
    db_path = args.db

    logger.info("=" * 60)
    logger.info("开始构建知识库索引")
    logger.info("=" * 60)

    # 1. 创建数据库结构
    setup_db(db_path)

    # 2. 导入 ClinVar
    clinvar_file = RAW_DATA_DIR / "clinvar.vcf.gz"
    if clinvar_file.exists() or args.clinvar:
        parse_clinvar_vcf(
            Path(args.clinvar) if args.clinvar else clinvar_file,
            db_path,
            chromosomes=args.chromosomes
        )

    # 3. 导入 gnomAD
    gnomad_file = RAW_DATA_DIR / "gnomad.chr22.vcf.bgz"
    if gnomad_file.exists() or args.gnomad:
        parse_gnomad_vcf(
            Path(args.gnomad) if args.gnomad else gnomad_file,
            db_path,
            chromosomes=args.chromosomes
        )

    # 4. 导入 Gene Info
    gene_info_file = RAW_DATA_DIR / "Homo_sapiens.gene_info.gz"
    if gene_info_file.exists() or args.gene_info:
        parse_gene_info(
            Path(args.gene_info) if args.gene_info else gene_info_file,
            db_path
        )

    # 5. 导入 PharmGKB
    pharmgkb_file = RAW_DATA_DIR / "pharmgkb_genes.zip"
    if pharmgkb_file.exists() or args.pharmgkb:
        parse_pharmgkb_genes(
            Path(args.pharmgkb) if args.pharmgkb else pharmgkb_file,
            db_path
        )

    # 6. 统计信息
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    logger.info("\n" + "=" * 60)
    logger.info("知识库统计")
    logger.info("=" * 60)

    tables = ['clinvar', 'gnomad', 'gene_info', 'pharmgkb_genes', 'pharmgkb_variants']
    for table in tables:
        try:
            c.execute(f"SELECT COUNT(*) FROM {table}")
            count = c.fetchone()[0]
            logger.info(f"{table:20s}: {count:,} 条记录")
        except:
            logger.info(f"{table:20s}: 表不存在")

    conn.close()

    db_size_mb = Path(db_path).stat().st_size / (1024 * 1024)
    logger.info(f"\n数据库大小: {db_size_mb:.1f} MB")
    logger.info(f"数据库位置: {db_path}")
    logger.info("=" * 60)
    logger.info("✓ 知识库索引构建完成！")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="构建知识库索引")

    parser.add_argument("--db", default="data/knowledge/knowledge.db", help="输出数据库路径")
    parser.add_argument("--clinvar", help="ClinVar VCF 文件路径")
    parser.add_argument("--gnomad", help="gnomAD VCF 文件路径")
    parser.add_argument("--gene-info", help="Gene Info 文件路径")
    parser.add_argument("--pharmgkb", help="PharmGKB 基因 ZIP 文件路径")
    parser.add_argument(
        "--chromosomes",
        nargs='+',
        help="仅导入指定染色体 (如: 1 2 22 X Y)"
    )

    args = parser.parse_args()

    # 安装依赖
    try:
        import tqdm
    except ImportError:
        logger.info("安装必要依赖: tqdm")
        os.system("pip install tqdm")

    build_full_index(args)
