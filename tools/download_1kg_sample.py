"""
1000 Genomes Data Sampler
Stream and sample VCF data from 1000 Genomes FTP without full download.
支持 HTTP/FTP 流式下载
"""

import sys
import gzip
import argparse
from pathlib import Path
from urllib.request import urlopen

# Default URL for Chromosome 22
DEFAULT_URL = "http://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz"

def download_sample(url: str, output_file: str, num_variants: int = 100):
    print(f"Connecting to: {url}")
    print(f"Goal: Extract {num_variants} variants to {output_file}...")
    
    try:
        # urlopen handle both http and ftp
        with urlopen(url) as response:
            with gzip.open(response, 'rt', encoding='utf-8') as gz_file:
                with open(output_file, 'w', encoding='utf-8') as out_file:
                    count = 0
                    
                    for line in gz_file:
                        if line.startswith('#'):
                            out_file.write(line)
                            continue
                        
                        if count < num_variants:
                            out_file.write(line)
                            count += 1
                            if count % 10 == 0:
                                print(f"Extracted {count}/{num_variants} variants...", end='\r')
                        else:
                            break
                            
        print(f"\n✅ Successfully extracted {count} variants to {output_file}")
        
    except Exception as e:
        print(f"\n❌ Download failed: {e}")
        if Path(output_file).exists():
            Path(output_file).unlink()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download 1000 Genomes Sample")
    parser.add_argument("-u", "--url", default=DEFAULT_URL, help="URL to VCF.gz file")
    parser.add_argument("-o", "--output", default="data/1000_genomes/chr22_sample.vcf", help="Output file path")
    parser.add_argument("-n", "--num", type=int, default=50, help="Number of variants to extract")
    
    args = parser.parse_args()
    
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    download_sample(args.url, args.output, args.num)
