"""
Genos Benchmark Tool
--------------------
Automates the comparison of Genos Pipeline performance against ClinVar data.
Generates an ROC curve and accuracy metrics.
"""

import sys
import os
import sqlite3
import random
import subprocess
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import roc_curve, auc, accuracy_score, precision_score, recall_score
from pathlib import Path

# Setup logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    db_path = "data/knowledge/knowledge.db"
    if not os.path.exists(db_path):
        logger.error(f"Database not found: {db_path}")
        sys.exit(1)
    return sqlite3.connect(db_path)

def generate_benchmark_vcf(output_vcf, limit_per_class=50):
    """Generate a VCF file with balanced Pathogenic and Benign variants from DB"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get Pathogenic
    logger.info("Sampling Pathogenic variants...")
    c.execute("SELECT chrom, pos, ref, alt, variant_id FROM clinvar WHERE clnsig LIKE '%Pathogenic%' AND clnsig NOT LIKE '%Conflict%' ORDER BY RANDOM() LIMIT ?", (limit_per_class,))
    pathogenic = c.fetchall()
    
    # Get Benign
    logger.info("Sampling Benign variants...")
    c.execute("SELECT chrom, pos, ref, alt, variant_id FROM clinvar WHERE clnsig LIKE '%Benign%' AND clnsig NOT LIKE '%Conflict%' ORDER BY RANDOM() LIMIT ?", (limit_per_class,))
    benign = c.fetchall()
    
    conn.close()
    
    logger.info(f"Found {len(pathogenic)} Pathogenic and {len(benign)} Benign variants.")
    
    if len(pathogenic) == 0 and len(benign) == 0:
        logger.error("No variants found in database! Please check knowledge.db population.")
        return None

    # Create VCF
    with open(output_vcf, 'w') as f:
        f.write("##fileformat=VCFv4.2\n")
        f.write("##source=GenosBenchmark\n")
        f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
        
        # Ground truth dictionary to return
        ground_truth = {}
        
        for p in pathogenic:
            chrom, pos, ref, alt, vid = p
            f.write(f"{chrom}\t{pos}\t{vid}\t{ref}\t{alt}\t100\tPASS\tBENCHMARK_STATUS=Pathogenic\n")
            ground_truth[vid] = 1 # Positive class
            
        for b in benign:
            chrom, pos, ref, alt, vid = b
            f.write(f"{chrom}\t{pos}\t{vid}\t{ref}\t{alt}\t100\tPASS\tBENCHMARK_STATUS=Benign\n")
            ground_truth[vid] = 0 # Negative class
            
    return ground_truth

def run_pipeline(vcf_path, output_dir):
    """Run the main genos pipeline"""
    logger.info(f"Running Genos Pipeline on {vcf_path}...")
    
    if os.path.exists(output_dir):
        import shutil
        shutil.rmtree(output_dir, ignore_errors=True)
        
    cmd = [
        sys.executable, "main.py",
        "--vcf", vcf_path,
        "--output", output_dir,
        "--config", "configs/run.yaml" # Ensure we use the config
    ]
    
    # Determine platform shell
    use_shell = True if os.name == 'nt' else False
    
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=use_shell)
    
    if process.returncode != 0:
        logger.error("Pipeline failed!")
        logger.error(process.stderr)
        return False
    
    logger.info("Pipeline completed successfully.")
    return True

def analyze_results(scores_path, ground_truth, output_dir):
    """Compare scores with ground truth"""
    if not os.path.exists(scores_path):
        logger.error(f"Scores file not found: {scores_path}")
        return
        
    df = pd.read_csv(scores_path, sep='\t')
    
    # Match predictions to truth
    y_true = []
    y_scores = []
    
    for _, row in df.iterrows():
        vid = str(row['variant_id'])
        if vid in ground_truth:
            y_true.append(ground_truth[vid])
            y_scores.append(row['final_score'])
            
    if not y_true:
        logger.error("No matching variants found between Output and Ground Truth.")
        return

    # Metrics
    y_true = np.array(y_true)
    y_scores = np.array(y_scores)
    prediction_binary = (y_scores > 0.5).astype(int)
    
    acc = accuracy_score(y_true, prediction_binary)
    prec = precision_score(y_true, prediction_binary, zero_division=0)
    rec = recall_score(y_true, prediction_binary, zero_division=0)
    
    try:
        fpr, tpr, _ = roc_curve(y_true, y_scores)
        roc_auc = auc(fpr, tpr)
    except:
        roc_auc = 0.5 # Fail safe for single class
        
    logger.info("=" * 40)
    logger.info("BENCHMARK RESULTS")
    logger.info("=" * 40)
    logger.info(f"Total Samples: {len(y_true)}")
    logger.info(f"Accuracy:      {acc:.4f}")
    logger.info(f"Precision:     {prec:.4f}")
    logger.info(f"Recall:        {rec:.4f}")
    logger.info(f"AUC-ROC:       {roc_auc:.4f}")
    logger.info("=" * 40)
    
    # Plotting
    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'Genos (AUC = {roc_auc:.2f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Receiver Operating Characteristic (ROC)')
    plt.legend(loc="lower right")
    plt.grid(True, alpha=0.3)
    
    plot_path = os.path.join(output_dir, "benchmark_roc.png")
    plt.savefig(plot_path)
    logger.info(f"ROC Plot saved to: {plot_path}")
    
    # Save Report
    with open(os.path.join(output_dir, "benchmark_summary.txt"), "w") as f:
        f.write(f"Genos Benchmark Report\n")
        f.write(f"======================\n")
        f.write(f"Accuracy: {acc:.4f}\n")
        f.write(f"AUC:      {roc_auc:.4f}\n")
        
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=20, help="Number of samples per class")
    parser.add_argument("--dir", type=str, default="runs/benchmark", help="Output directory")
    args = parser.parse_args()
    
    # 0. Output Setup
    benchmark_vcf = "examples/benchmark_set.vcf"
    
    # 1. Generate Data
    ground_truth = generate_benchmark_vcf(benchmark_vcf, args.samples)
    
    if ground_truth:
        # 2. Run Pipeline
        if run_pipeline(benchmark_vcf, args.dir):
            # 3. Analyze
            analyze_results(os.path.join(args.dir, "scores.tsv"), ground_truth, args.dir)
