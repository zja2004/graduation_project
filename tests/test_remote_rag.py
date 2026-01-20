
import sys
import os
import logging
import pandas as pd
from pathlib import Path

# Setup path
sys.path.append(os.getcwd())

from agents.executor.evidence_rag import EvidenceRAGAgent

# Config for test (Hybrid mode)
config = {
    "knowledge": {
        "mode": "hybrid",
        "remote_timeout": 10
    },
    "evidence_rag": {
        "top_k": 5,
        "source_weights": {"clinvar": 1.0}
    }
}

def test_remote_rag():
    print("Testing Remote RAG Capability...")
    
    agent = EvidenceRAGAgent(config)
    
    # Force local DB to be None to simulate missing DB
    agent.db_conn = None 
    agent.gnomad_db = None
    
    # Test Variant: BRAF V600E (chr7:140753336 A>T in hg38)
    # Note: MyVariant.info might use 1-based coordinates
    variant = pd.Series({
        "variant_id": "test_var",
        "chrom": "chr7",
        "pos": 140753336,
        "ref": "A",
        "alt": "T",
        "final_score": 0.9,
        "impact_level": "HIGH",
        "gene": "BRAF" # For DeepSeek if enabled
    })
    
    print(f"Querying variant: {variant['chrom']}:{variant['pos']} {variant['ref']}>{variant['alt']}")
    
    evidence = agent._retrieve_evidence(variant)
    
    # Check ClinVar
    clinvar_found = False
    for source in evidence["sources"]:
        if source["source"] == "ClinVar":
            data = source["data"]
            if data.get("found"):
                print("[SUCCESS] ClinVar evidence found via Remote API!")
                print(f"  - Significance: {data.get('clinical_significance')}")
                print(f"  - Disease: {data.get('disease_name')}")
                clinvar_found = True
                
        if source["source"] == "gnomAD":
            data = source["data"]
            if data.get("found"):
                print("[SUCCESS] gnomAD frequency found via Remote API!")
                print(f"  - AF: {data.get('allele_frequency')}")

    if not clinvar_found:
        print("[FAILURE] ClinVar evidence NOT found.")
        exit(1)
        
    print("\nTest Passed!")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    test_remote_rag()
