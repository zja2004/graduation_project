"""
Generate Synthetic VCF Data for Testing
生成用于测试的合成 VCF 数据
"""

import random
import argparse
from pathlib import Path
from datetime import datetime

def generate_vcf(output_file: str, num_variants: int = 10):
    """
    生成包含随机变异的 VCF 文件
    """
    import random
    
    CHROMOSOMES = [f"chr{i}" for i in range(1, 23)] + ["chrX", "chrY"]
    BASES = ['A', 'T', 'C', 'G']
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Header
        f.write("##fileformat=VCFv4.2\n")
        f.write(f"##fileDate={datetime.now().strftime('%Y%m%d')}\n")
        f.write("##source=GenosSyntheticGenerator\n")
        f.write("##reference=hg38\n")
        f.write("##INFO=<ID=DP,Number=1,Type=Integer,Description=\"Total Depth\">\n")
        f.write("##INFO=<ID=AF,Number=A,Type=Float,Description=\"Allele Frequency\">\n")
        f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
        
        for i in range(num_variants):
            chrom = random.choice(CHROMOSOMES)
            pos = random.randint(10000, 10000000)
            rs_id = f"rs{random.randint(100000, 999999)}"
            
            ref = random.choice(BASES)
            alt = random.choice([b for b in BASES if b != ref])
            
            qual = random.randint(30, 99)
            dp = random.randint(10, 100)
            af = round(random.random() * 0.05, 4) # Low frequency mostly
            
            # 10% chance of being "ClinVar pathogenic" simulation (high QUAL, specific info)
            if random.random() < 0.1:
                af = 0.0001
                qual = 99
            
            line = f"{chrom}\t{pos}\t{rs_id}\t{ref}\t{alt}\t{qual}\tPASS\tDP={dp};AF={af}\n"
            f.write(line)
            
    print(f"✅ 已生成测试文件: {output_file} ({num_variants} 个变异)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成合成 VCF 测试数据")
    parser.add_argument("-o", "--output", default="examples/synthetic_test.vcf", help="输出文件路径")
    parser.add_argument("-n", "--num", type=int, default=20, help="生成的变异数量")
    
    args = parser.parse_args()
    generate_vcf(args.output, args.num)
    print("使用方法: python tools/generate_test_vcf.py -o examples/my_test.vcf -n 50")
