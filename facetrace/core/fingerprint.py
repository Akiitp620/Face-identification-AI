"""
Responsible ONLY for cryptographic fingerprinting.
"""

import hashlib
import json
from dataclasses import asdict
from core.evidence import Evidence

class EvidenceFingerprinter:
    @staticmethod
    def to_canonical_json(evidence: Evidence) -> str:
        """
        Returns a deterministic JSON representation of the evidence.
        Sorts keys to ensure the same object always produces the same string.
        """
        data = asdict(evidence)
        return json.dumps(data, sort_keys=True, separators=(',', ':'))

    @staticmethod
    def compute_fingerprint(evidence: Evidence) -> str:
        """
        Generates a SHA-256 fingerprint from the canonical JSON.
        """
        canonical_str = EvidenceFingerprinter.to_canonical_json(evidence)
        return hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()
