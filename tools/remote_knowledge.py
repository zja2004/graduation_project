"""
Remote Knowledge Client
-----------------------
Handles interactions with remote APIs (MyVariant.info) to fetch variant evidence
when local databases are unavailable.
"""

import requests
import logging
import time
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class RemoteKnowledgeClient:
    """Client for fetching variant data from remote public APIs"""
    
    MYVARIANT_URL = "https://myvariant.info/v1/variant"
    
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.session = requests.Session()
        # Add basic retry adapter
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def query_variant(self, chrom: str, pos: int, ref: str, alt: str, assembly: str = "hg38") -> Dict[str, Any]:
        """
        Query MyVariant.info for a specific variant.
        
        Args:
            chrom: Chromosome (e.g., "chr1" or "1")
            pos: Position (1-based)
            ref: Reference allele
            alt: Alternative allele
            assembly: Genome assembly ("hg38" or "hg19")
            
        Returns:
            Dictionary containing unified evidence (ClinVar, gnomAD, etc.)
        """
        # Normalize chromosome
        chrom_clean = str(chrom).replace("chr", "")
        
        # Construct HGVS ID (e.g., chr1:g.123456A>G)
        hgvs_id = f"chr{chrom_clean}:g.{pos}{ref}>{alt}"
        
        params = {
            "assembly": assembly,
            "fields": "clinvar,gnomad_exome,gnomad_genome,dbnsfp,cadd"
        }
        
        try:
            logger.debug(f"Querying MyVariant.info: {hgvs_id}")
            response = self.session.get(
                f"{self.MYVARIANT_URL}/{hgvs_id}",
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 404:
                return {}
                
            response.raise_for_status()
            data = response.json()
            
            return self._parse_response(data)
            
        except Exception as e:
            logger.warning(f"Remote API query failed for {hgvs_id}: {e}")
            return {}

    def _parse_response(self, data: Dict) -> Dict[str, Any]:
        """Parse raw API response into our internal evidence format"""
        evidence = {}
        
        # 1. ClinVar
        if "clinvar" in data:
            cv = data["clinvar"]
            # Handle list vs dict
            if isinstance(cv, list):
                # Rare case where multiple clinvar entries exist at top level?
                cv = cv[0] if cv else {}
                
            if isinstance(cv, dict):
                rcv = cv.get("rcv", [])
                if isinstance(rcv, list) and len(rcv) > 0:
                    entry = rcv[0]
                    
                    # Safe parsing of conditions
                    conditions = entry.get("conditions", {})
                    disease_name = "Unknown"
                    if isinstance(conditions, dict):
                        disease_name = conditions.get("name", "Unknown")
                    elif isinstance(conditions, list):
                        if conditions and isinstance(conditions[0], dict):
                            disease_name = conditions[0].get("name", "Unknown")
                        elif conditions:
                             disease_name = str(conditions[0])
                    elif isinstance(conditions, str):
                        disease_name = conditions
                        
                    evidence["clinvar"] = {
                        "found": True,
                        "clinical_significance": entry.get("clinical_significance", "Unknown"),
                        "disease_name": disease_name,
                        "review_status": entry.get("review_status", "no_assertion_criteria_provided"),
                        "variant_id": cv.get("variant_id")
                    }
                    logger.debug(f"Parsed ClinVar: {evidence['clinvar']}")
        
        # 2. gnomAD (Genome)
        if "gnomad_genome" in data:
            gn = data["gnomad_genome"]
            evidence["gnomad"] = {
                "found": True,
                "allele_frequency": float(gn.get("af", {}).get("af", 0.0)),
                "ac": gn.get("ac", {}).get("ac", 0),
                "an": gn.get("an", {}).get("an", 0)
            }
            
        # 3. DBNSFP (Functional Predictions)
        if "dbnsfp" in data:
            db = data["dbnsfp"]
            evidence["predictions"] = {
                "sift": db.get("sift", {}).get("pred"),
                "polyphen": db.get("polyphen2_hdiv", {}).get("pred"),
                "revel": db.get("revel_score")
            }
            
        return evidence
