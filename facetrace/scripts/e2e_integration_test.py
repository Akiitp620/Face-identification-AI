import os
import json
import copy
import sys
from PIL import Image
from dotenv import load_dotenv

os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

# 0. Set sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# 1. Load env
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)

# 2. Load deployed contract address if not in env
if not os.getenv("CONTRACT_ADDRESS"):
    dep_path = os.path.join(os.path.dirname(__file__), "..", "blockchain", "deployment.json")
    if os.path.exists(dep_path):
        with open(dep_path, "r") as f:
            data = json.load(f)
            if "address" in data:
                os.environ["CONTRACT_ADDRESS"] = data["address"]

# Force reloading of config variables if needed, or simply patch Config
import utils.config
if not utils.config.Config.CONTRACT_ADDRESS:
    utils.config.Config.CONTRACT_ADDRESS = os.environ.get("CONTRACT_ADDRESS")

import torch
torch.backends.mps.is_available = lambda: False

# Now import the core modules
from core.face_engine import FaceEngine
from core.discovery import DiscoveryEngine
from core.candidate_ranker import CandidateRanker
from core.evidence import Evidence
from core.fingerprint import EvidenceFingerprinter
from core.blockchain import BlockchainRegistry
from core.verifier import EvidenceVerifier

def run_e2e():
    print("\n========================================")
    print(" FACE TRACE E2E INTEGRATION TEST")
    print("========================================\n")
    
    # FACE ENGINE
    print("[FACE ENGINE] Initializing and processing image...")
    engine = FaceEngine()
    test_image_path = os.path.join(os.path.dirname(__file__), "..", "test_face.jpg")
    image = Image.open(test_image_path)
    embedding = engine.process_face(image)
    print("STATUS: PASS\n")
    
    # DISCOVERY
    print("[DISCOVERY] Running SerpApi Google Lens discovery...")
    discovery = DiscoveryEngine()
    with open(test_image_path, "rb") as f:
        image_bytes = f.read()
    candidates = discovery.search(image_bytes)
    print(f"Found {len(candidates)} candidates.")
    print("STATUS: PASS\n")
    
    # CANDIDATE RANKING
    print("[CANDIDATE RANKING] Ranking candidates...")
    ranker = CandidateRanker(engine)
    ranked = ranker.rank_candidates(embedding, candidates)
    best_evidence = ranker.select_best_evidence(ranked)
    print(f"Best match score: {best_evidence.evidence_match_score:.1f}%")
    print(f"Source URL: {best_evidence.candidate.source_url}")
    print("STATUS: PASS\n")
    
    # EVIDENCE
    print("[EVIDENCE] Creating Canonical Evidence...")
    canonical_evidence = Evidence(
        source_url=best_evidence.candidate.source_url,
        ipfs_cid="QmTestCID1234567890abcdef", # Dummy IPFS CID for test since we aren't testing Pinata
        relevant_text=best_evidence.candidate.metadata.get('name', 'Unknown context'),
        metadata=best_evidence.candidate.metadata
    )
    print("STATUS: PASS\n")
    
    # SHA-256
    print("[SHA-256] Generating Fingerprint...")
    fingerprint = EvidenceFingerprinter.compute_fingerprint(canonical_evidence)
    print(f"Calculated Fingerprint: {fingerprint}")
    print("STATUS: PASS\n")
    
    # BLOCKCHAIN WRITE
    print(f"[BLOCKCHAIN WRITE] Registering to Sepolia (Contract: {utils.config.Config.CONTRACT_ADDRESS})...")
    registry = BlockchainRegistry()
    try:
        tx_hash = registry.register_evidence(fingerprint)
        print("STATUS: PASS")
        
        # BLOCKCHAIN TX HASH
        print(f"\n[BLOCKCHAIN TX HASH]")
        print(f"Hash: {tx_hash}\n")
    except Exception as e:
        print(f"Error during registration: {e}")
        print("STATUS: FAIL\n")
        return
        
    # ON-CHAIN READ & VERIFICATION
    print("[ON-CHAIN READ & VERIFICATION] Reading fingerprint from blockchain...")
    verifier = EvidenceVerifier(registry)
    result_orig = verifier.verify(canonical_evidence)
    
    if result_orig.is_verified:
        print("Verification Output:", result_orig.message)
        print("STATUS: PASS\n")
    else:
        print("Verification Output:", result_orig.message)
        print("STATUS: FAIL\n")
        
    # TAMPER DETECTION
    print("[TAMPER DETECTION] Tampering with evidence CID and verifying...")
    tampered = copy.deepcopy(canonical_evidence)
    tampered.ipfs_cid = "QmTamperedCID999999"
    result_tampered = verifier.verify(tampered)
    
    if not result_tampered.is_verified:
        print("Tamper correctly detected. Verification rejected.")
        print("STATUS: PASS\n")
    else:
        print("Tamper NOT detected.")
        print("STATUS: FAIL\n")

    # FINAL E2E STATUS
    print("========================================")
    print("[FINAL E2E STATUS] ", end="")
    if result_orig.is_verified and not result_tampered.is_verified:
        print("PASS")
    else:
        print("FAIL")
    print("========================================\n")

if __name__ == "__main__":
    run_e2e()
