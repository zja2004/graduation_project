"""
精简版知识库下载
仅下载必需的核心数据（ClinVar + Gene Info + PharmGKB）
跳过超大文件 gnomAD
"""

import os
import requests
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = Path("data/knowledge/raw")
DATA_DIR.mkdir(parents=True, exist_ok=True)

def download_file(url, output_path, description=""):
    """下载文件"""
    try:
        logger.info(f"下载: {description}")
        logger.info(f"URL: {url}")

        # 检查文件是否已存在
        if output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            logger.info(f"✓ 文件已存在: {output_path.name} ({size_mb:.1f} MB)")
            return True

        response = requests.head(url, allow_redirects=True, timeout=30)
        total_size = int(response.headers.get('content-length', 0))
        total_mb = total_size / (1024 * 1024)

        logger.info(f"文件大小: {total_mb:.1f} MB")

        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()

        downloaded = 0
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024*1024):  # 1MB chunks
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if downloaded % (10 * 1024 * 1024) == 0:  # 每 10MB 显示进度
                        progress = (downloaded / total_size * 100) if total_size else 0
                        logger.info(f"  进度: {progress:.1f}% ({downloaded/(1024*1024):.1f}/{total_mb:.1f} MB)")

        logger.info(f"✓ 下载完成: {output_path.name}")
        return True

    except Exception as e:
        logger.error(f"✗ 下载失败: {e}")
        if output_path.exists():
            output_path.unlink()
        return False


def main():
    logger.info("="*60)
    logger.info("下载必需知识库数据")
    logger.info("="*60)

    tasks = [
        {
            "url": "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz",
            "filename": "clinvar.vcf.gz",
            "description": "ClinVar 临床变异数据库 (~2 GB)"
        },
        {
            "url": "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz.tbi",
            "filename": "clinvar.vcf.gz.tbi",
            "description": "ClinVar 索引文件"
        },
        {
            "url": "https://ftp.ncbi.nlm.nih.gov/gene/DATA/GENE_INFO/Mammalia/Homo_sapiens.gene_info.gz",
            "filename": "Homo_sapiens.gene_info.gz",
            "description": "基因功能注释 (~50 MB)"
        },
        {
            "url": "https://api.pharmgkb.org/v1/download/file/data/genes.zip",
            "filename": "pharmgkb_genes.zip",
            "description": "PharmGKB 药物基因数据 (~10 MB)"
        },
        {
            "url": "https://api.pharmgkb.org/v1/download/file/data/clinicalVariants.zip",
            "filename": "pharmgkb_variants.zip",
            "description": "PharmGKB 临床变异 (~5 MB)"
        }
    ]

    success_count = 0
    for task in tasks:
        print("\n" + "="*60)
        output_path = DATA_DIR / task["filename"]
        if download_file(task["url"], output_path, task["description"]):
            success_count += 1

    print("\n" + "="*60)
    print(f"下载完成: {success_count}/{len(tasks)} 个文件")
    print("="*60)
    print(f"\n数据保存位置: {DATA_DIR.absolute()}")
    print("\n下一步: 运行 'python tools/build_knowledge_index_enhanced.py' 构建索引")

if __name__ == "__main__":
    main()
