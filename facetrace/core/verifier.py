import logging
from dataclasses import dataclass
from core.evidence import Evidence
from core.fingerprint import EvidenceFingerprinter
from core.blockchain import BlockchainRegistry

logger = logging.getLogger(__name__)

@dataclass
class VerificationResult:
    is_verified: bool
    computed_fingerprint: str
    blockchain_timestamp: int
    blockchain_registrar: str
    message: str

class EvidenceVerifier:
    def __init__(self, registry: BlockchainRegistry):
        self.registry = registry

    def verify(self, evidence: Evidence) -> VerificationResult:
        computed_fingerprint = EvidenceFingerprinter.compute_fingerprint(evidence)
        
        try:
            record = self.registry.verify_evidence(computed_fingerprint)
        except Exception as e:
            logger.error(f"Blockchain lookup failed: {e}")
            return VerificationResult(False, computed_fingerprint, 0, "", f"Blockchain lookup error: {e}")
            
        if record.get("exists"):
            return VerificationResult(
                is_verified=True,
                computed_fingerprint=computed_fingerprint,
                blockchain_timestamp=record.get("timestamp"),
                blockchain_registrar=record.get("registrar"),
                message="VERIFIED: Evidence is authentic and untampered."
            )
        else:
            return VerificationResult(
                is_verified=False,
                computed_fingerprint=computed_fingerprint,
                blockchain_timestamp=0,
                blockchain_registrar="",
                message="MISMATCH: Evidence fingerprint not found on blockchain. Possible tampering detected."
            )
