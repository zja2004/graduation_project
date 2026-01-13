"""
VCF Subset Tool
用于从大型 VCF 文件中提取前 N 行变异，避免 API 消耗过大。
"""

import argparse
from pathlib import Path

import gzip

def subset_vcf(input_file: str, output_file: str, num_variants: int = 20):
    """
    提取 VCF 文件的前 N 个变异 (支持 .vcf 和 .vcf.gz)
    """
    print(f"正在提取 {input_file} 的前 {num_variants} 个变异...")
    
    is_gzip = input_file.endswith('.gz')
    open_func = gzip.open if is_gzip else open
    mode = 'rt' if is_gzip else 'r'
    
    count = 0
    try:
        with open_func(input_file, mode, encoding='utf-8', errors='ignore') as fin, \
             open(output_file, 'w', encoding='utf-8') as fout:
            
            for line in fin:
                if line.startswith("#"):
                    fout.write(line)
                else:
                    if count < num_variants:
                        fout.write(line)
                        count += 1
                    else:
                        break
        print(f"✅ 已生成子集文件: {output_file} ({count} 个变异)")
    except Exception as e:
        print(f"❌ 提取失败: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="提取 VCF 文件子集")
    parser.add_argument("input", help="输入 VCF 文件路径")
    parser.add_argument("-o", "--output", default="examples/subset_test.vcf", help="输出文件路径")
    parser.add_argument("-n", "--num", type=int, default=20, help="提取的变异数量")
    
    args = parser.parse_args()
    subset_vcf(args.input, args.output, args.num)
