"""
Build Knowledge Base Index
--------------------------
Reads ClinVar VCF and other sources to build a local SQLite knowledge base.
"""

import os
import sqlite3
import gzip
import logging
import argparse
from pathlib import Path
from typing import Dict, Any

# Ensure output directory exists
os.makedirs("data/knowledge", exist_ok=True)

logger = logging.getLogger(__name__)

def setup_db(db_path: str):
    """Create SQLite tables"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # ClinVar table
    c.execute('''
        CREATE TABLE IF NOT EXISTS clinvar (
            chrom TEXT,
            pos INTEGER,
            ref TEXT,
            alt TEXT,
            variant_id TEXT,
            clnsig TEXT,  -- Clinical Significance (e.g. Pathogenic)
            clndn TEXT,   -- Disease Name
            info TEXT,    -- Full INFO string
            PRIMARY KEY (chrom, pos, ref, alt)
        )
    ''')
    
    c.execute('CREATE INDEX IF NOT EXISTS idx_clinvar_pos ON clinvar (chrom, pos)')
    
    conn.commit()
    conn.close()

def parse_clinvar_vcf(vcf_path: str, db_path: str, limit: int = None):
    """Parse ClinVar VCF and insert into DB"""
    if not os.path.exists(vcf_path):
        logger.error(f"ClinVar file not found: {vcf_path}")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    open_func = gzip.open if vcf_path.endswith('.gz') else open
    mode = 'rt' if vcf_path.endswith('.gz') else 'r'
    
    count = 0
    batch = []
    BATCH_SIZE = 1000
    
    print(f"Parsing ClinVar: {vcf_path} ...")
    
    try:
        with open_func(vcf_path, mode, encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.startswith('#'):
                    continue
                
                parts = line.strip().split('\t')
                chrom = parts[0]
                
                # OPTIMIZATION: For this demo, only load chr22 to match our test data
                # Remove this check to load full database
                if '22' not in chrom:
                    continue

                pos = int(parts[1])
                ref = parts[3]
                alt = parts[4]
                info_str = parts[7]
                
                # Parse INFO
                info_dict = {}
                for item in info_str.split(';'):
                    if '=' in item:
                        k, v = item.split('=', 1)
                        info_dict[k] = v
                
                # Extract key fields
                variant_id = parts[2]
                clnsig = info_dict.get('CLNSIG', '')
                clndn = info_dict.get('CLNDN', '').replace('_', ' ')
                
                # Add to batch
                # Normalize chrom (remove 'chr' prefix if present to standardize)
                chrom_norm = chrom.replace('chr', '')
                
                batch.append((chrom_norm, pos, ref, alt, variant_id, clnsig, clndn, info_str))
                count += 1
                
                if len(batch) >= BATCH_SIZE:
                    c.executemany('INSERT OR REPLACE INTO clinvar VALUES (?,?,?,?,?,?,?,?)', batch)
                    batch = []
                    if count % 10000 == 0:
                        print(f"  Processed {count} entries...")
                
                if limit and count >= limit:
                    break
                    
        # Insert remaining
        if batch:
            c.executemany('INSERT OR REPLACE INTO clinvar VALUES (?,?,?,?,?,?,?,?)', batch)
            
        conn.commit()
        print(f"✅ ClinVar import complete: {count} entries.")
        
    except Exception as e:
        logger.error(f"Failed to parse ClinVar: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--clinvar", help="Path to ClinVar VCF", required=True)
    parser.add_argument("--db", default="data/knowledge/knowledge.db", help="Output DB path")
    parser.add_argument("--limit", type=int, help="Limit number of entries (for testing)")
    
    args = parser.parse_args()
    
    setup_db(args.db)
    parse_clinvar_vcf(args.clinvar, args.db, args.limit)
