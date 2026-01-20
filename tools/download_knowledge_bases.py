"""
知识库数据下载脚本
自动下载 ClinVar, gnomAD, COSMIC, PharmGKB 等权威数据库
"""

import os
import sys
import requests
import gzip
import shutil
import logging
from pathlib import Path
try:
    from tqdm import tqdm as tqdm_bar
except ImportError:
    # Fallback if tqdm not available
    def tqdm_bar(iterable=None, total=None, **kwargs):
        return iterable if iterable else range(total)
import hashlib

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 数据下载目录
DATA_DIR = Path("data/knowledge/raw")

def set_download_dir(path: str):
    global DATA_DIR
    DATA_DIR = Path(path)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# 数据源配置
DATA_SOURCES = {
    "clinvar": {
        "name": "ClinVar (GRCh38)",
        "url": "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz",
        "filename": "clinvar.vcf.gz",
        "size_mb": 2048,
        "description": "临床意义已验证的基因变异数据库"
    },
    "clinvar_index": {
        "name": "ClinVar Index",
        "url": "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz.tbi",
        "filename": "clinvar.vcf.gz.tbi",
        "size_mb": 2,
        "description": "ClinVar 索引文件（加速查询）"
    },
    "gnomad_genome": {
        "name": "gnomAD v3.1.2 (Sites Only)",
        "url": "https://gnomad-public-us-east-1.s3.amazonaws.com/release/3.1.2/vcf/genomes/gnomad.genomes.v3.1.2.sites.vcf.bgz",
        "filename": "gnomad.genomes.v3.1.2.sites.vcf.bgz",
        "size_mb": 89000,  # 约 89 GB
        "description": "全基因组等位基因频率数据（超大文件，建议分染色体下载）",
        "optional": True
    },
    "gnomad_chr22": {
        "name": "gnomAD chr22 (测试用)",
        "url": "https://gnomad-public-us-east-1.s3.amazonaws.com/release/3.1.2/vcf/genomes/gnomad.genomes.v3.1.2.sites.chr22.vcf.bgz",
        "filename": "gnomad.chr22.vcf.bgz",
        "size_mb": 1200,
        "description": "22号染色体频率数据（推荐用于测试）"
    },
    "gene_info": {
        "name": "NCBI Gene Info",
        "url": "https://ftp.ncbi.nlm.nih.gov/gene/DATA/GENE_INFO/Mammalia/Homo_sapiens.gene_info.gz",
        "filename": "Homo_sapiens.gene_info.gz",
        "size_mb": 50,
        "description": "人类基因功能注释信息"
    },
    "omim": {
        "name": "OMIM (需要授权)",
        "url": None,
        "filename": "omim.txt",
        "size_mb": 100,
        "description": "人类基因和遗传性疾病知识库（需要到 https://www.omim.org/ 申请下载）",
        "manual": True
    },
    "cosmic": {
        "name": "COSMIC (需要授权)",
        "url": None,
        "filename": "cosmic.vcf.gz",
        "size_mb": 500,
        "description": "癌症体细胞突变数据库（需要到 https://cancer.sanger.ac.uk/cosmic 注册下载）",
        "manual": True
    },
    "pharmgkb_genes": {
        "name": "PharmGKB Genes",
        "url": "https://api.pharmgkb.org/v1/download/file/data/genes.zip",
        "filename": "pharmgkb_genes.zip",
        "size_mb": 10,
        "description": "药物基因组学基因数据"
    },
    "pharmgkb_variants": {
        "name": "PharmGKB Clinical Variants",
        "url": "https://api.pharmgkb.org/v1/download/file/data/clinicalVariants.zip",
        "filename": "pharmgkb_variants.zip",
        "size_mb": 5,
        "description": "药物基因组学临床变异数据"
    }
}


def download_file(url: str, output_path: Path, description: str = "") -> bool:
    """
    下载文件（带进度条）

    Args:
        url: 下载链接
        output_path: 保存路径
        description: 文件描述

    Returns:
        是否下载成功
    """
    try:
        logger.info(f"开始下载: {description}")
        logger.info(f"URL: {url}")

        # 发送 HEAD 请求获取文件大小
        response = requests.head(url, allow_redirects=True, timeout=30)
        total_size = int(response.headers.get('content-length', 0))

        # 检查是否已存在且大小匹配
        if output_path.exists():
            existing_size = output_path.stat().st_size
            if existing_size == total_size:
                logger.info(f"✓ 文件已存在且完整: {output_path.name}")
                return True
            else:
                logger.warning(f"文件已存在但不完整 ({existing_size}/{total_size} bytes)，重新下载")

        # 开始下载
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()

        # 使用进度条
        with open(output_path, 'wb') as f:
            with tqdm_bar(
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                desc=output_path.name
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

        logger.info(f"✓ 下载完成: {output_path}")
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"✗ 下载失败: {e}")
        if output_path.exists():
            output_path.unlink()
        return False
    except Exception as e:
        logger.error(f"✗ 未知错误: {e}")
        return False


def verify_file(file_path: Path, expected_size_mb: int = None) -> bool:
    """验证文件完整性"""
    if not file_path.exists():
        return False

    file_size_mb = file_path.stat().st_size / (1024 * 1024)

    if expected_size_mb:
        # 允许 5% 的大小差异
        if abs(file_size_mb - expected_size_mb) / expected_size_mb > 0.05:
            logger.warning(f"文件大小异常: {file_size_mb:.1f}MB (预期 {expected_size_mb}MB)")
            return False

    logger.info(f"✓ 文件验证通过: {file_path.name} ({file_size_mb:.1f}MB)")
    return True


def download_all(include_large: bool = False, test_mode: bool = True):
    """
    下载所有数据源

    Args:
        include_large: 是否下载大文件（gnomAD 全基因组等）
        test_mode: 测试模式（仅下载小文件和 chr22 数据）
    """
    logger.info("=" * 60)
    logger.info("知识库数据下载工具")
    logger.info("=" * 60)

    downloaded = []
    failed = []
    skipped = []
    manual = []

    for key, config in DATA_SOURCES.items():
        name = config["name"]
        url = config.get("url")
        filename = config["filename"]
        size_mb = config["size_mb"]
        description = config["description"]
        is_optional = config.get("optional", False)
        is_manual = config.get("manual", False)

        output_path = DATA_DIR / filename

        print(f"\n{'='*60}")
        print(f"数据源: {name}")
        print(f"描述: {description}")
        print(f"预计大小: {size_mb} MB")
        print(f"{'='*60}")

        # 需要手动下载的数据源
        if is_manual:
            logger.warning(f"⚠️  {name} 需要手动下载（需要账号授权）")
            logger.info(f"   请访问官网申请下载，然后保存到: {output_path}")
            manual.append(name)
            continue

        # 测试模式下跳过大文件
        if test_mode and size_mb > 2000:
            logger.info(f"⏭️  测试模式，跳过大文件: {name}")
            skipped.append(name)
            continue

        # 跳过可选的超大文件
        if is_optional and not include_large:
            logger.info(f"⏭️  跳过可选的大文件: {name} (使用 --include-large 启用)")
            skipped.append(name)
            continue

        # 下载文件
        if url:
            success = download_file(url, output_path, description)

            if success:
                # 验证文件
                if verify_file(output_path, size_mb):
                    downloaded.append(name)
                else:
                    failed.append(name)
            else:
                failed.append(name)

    # 打印摘要
    print("\n" + "=" * 60)
    print("下载摘要")
    print("=" * 60)

    if downloaded:
        print(f"\n✅ 成功下载 ({len(downloaded)}):")
        for name in downloaded:
            print(f"   - {name}")

    if skipped:
        print(f"\n⏭️  已跳过 ({len(skipped)}):")
        for name in skipped:
            print(f"   - {name}")

    if manual:
        print(f"\n⚠️  需要手动下载 ({len(manual)}):")
        for name in manual:
            print(f"   - {name}")

    if failed:
        print(f"\n❌ 下载失败 ({len(failed)}):")
        for name in failed:
            print(f"   - {name}")

    print("\n" + "=" * 60)
    print("下一步:")
    print("  1. 运行 'python tools/build_knowledge_index.py' 构建索引")
    print("  2. 运行 'python main.py --vcf examples/test_with_genes.vcf' 测试")
    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="下载知识库数据")
    parser.add_argument(
        "--include-large",
        action="store_true",
        help="下载大文件（gnomAD 全基因组等，需要大量磁盘空间）"
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="生产模式（下载所有文件，包括大文件）"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="指定下载目录 (默认: data/knowledge/raw)"
    )

    args = parser.parse_args()
    
    # 设置下载目录
    if args.output_dir:
        set_download_dir(args.output_dir)
    else:
        # Default mkdir behavior if no arg provided
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 安装依赖（已经在虚拟环境中安装）
    try:
        from tqdm import tqdm
    except ImportError:
        logger.warning("tqdm 未安装，将使用基本进度显示")
        pass

    test_mode = not args.production
    download_all(include_large=args.include_large or args.production, test_mode=test_mode)
