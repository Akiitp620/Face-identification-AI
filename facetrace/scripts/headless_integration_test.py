import sys
import os
import copy
from PIL import Image
import requests
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.face_engine import FaceEngine
from core.discovery import DiscoveryEngine
from core.candidate_ranker import CandidateRanker
from core.evidence import Evidence
from core.fingerprint import EvidenceFingerprinter
from core.blockchain import BlockchainRegistry
from core.verifier import EvidenceVerifier
from core.ipfs import IPFSClient
from utils.config import Config

def run_test():
    report = {
        "FACE ENGINE": "FAIL",
        "SERPAPI GOOGLE LENS": "FAIL",
        "CANDIDATE RANKING": "FAIL",
        "EVIDENCE": "FAIL",
        "SHA-256": "FAIL",
        "IPFS": "BLOCKED",
        "BLOCKCHAIN": "BLOCKED",
        "ON-CHAIN RE-VERIFICATION": "BLOCKED",
        "TAMPER DETECTION": "BLOCKED"
    }

    start_time = time.time()
    
    top_candidate_url = None
    similarity_score = None
    fingerprint = None
    ipfs_cid = None
    tx_hash = None

    try:
        # 1. Image loading
        image_path = os.path.join(os.path.dirname(__file__), '..', 'test_face.jpg')
        if not os.path.exists(image_path):
            print("Test image not found.")
            return report, 0, top_candidate_url, similarity_score, fingerprint, ipfs_cid, tx_hash
        
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        # 2. Face Engine
        print("--- FACE ENGINE ---")
        try:
            import torch
            # Temporary patch to force CPU and avoid PyTorch MPS Adaptive pool bug on Apple Silicon
            original_mps_check = torch.backends.mps.is_available
            torch.backends.mps.is_available = lambda: False
            engine = FaceEngine()
            torch.backends.mps.is_available = original_mps_check
            
            image = Image.open(image_path)
            embedding = engine.process_face(image)
            report["FACE ENGINE"] = "PASS"
            print("Face embedding successfully generated.")
        except Exception as e:
            print(f"Failed to generate face embedding: {e}")
            return report, time.time() - start_time, top_candidate_url, similarity_score, fingerprint, ipfs_cid, tx_hash

        # 3. SerpApi Google Lens
        print("--- SERPAPI GOOGLE LENS ---")
        if not Config.SERPAPI_API_KEY:
            report["SERPAPI GOOGLE LENS"] = "BLOCKED"
            print("SERPAPI_API_KEY not configured.")
            return report, time.time() - start_time, top_candidate_url, similarity_score, fingerprint, ipfs_cid, tx_hash
            
        discovery = DiscoveryEngine()
        try:
            candidates = discovery.search(image_bytes)
            if candidates:
                report["SERPAPI GOOGLE LENS"] = "PASS"
                print(f"Found {len(candidates)} candidates.")
            else:
                print("No candidates returned from SerpApi.")
                return report, time.time() - start_time, top_candidate_url, similarity_score, fingerprint, ipfs_cid, tx_hash
        except Exception as e:
            print(f"SerpApi Error: {e}")
            return report, time.time() - start_time, top_candidate_url, similarity_score, fingerprint, ipfs_cid, tx_hash

        # 4. Candidate Ranking
        print("--- CANDIDATE RANKING ---")
        try:
            ranker = CandidateRanker(engine)
            ranked = ranker.rank_candidates(embedding, candidates)
            best_evidence = ranker.select_best_evidence(ranked)
            if best_evidence:
                report["CANDIDATE RANKING"] = "PASS"
                top_candidate_url = best_evidence.candidate.source_url
                similarity_score = best_evidence.evidence_match_score
                print(f"Top Candidate URL: {top_candidate_url}")
                print(f"Similarity Score: {similarity_score}")
            else:
                print("Candidate ranking failed to select best evidence.")
                return report, time.time() - start_time, top_candidate_url, similarity_score, fingerprint, ipfs_cid, tx_hash
        except Exception as e:
            print(f"Candidate Ranking Error: {e}")
            return report, time.time() - start_time, top_candidate_url, similarity_score, fingerprint, ipfs_cid, tx_hash

        # 5. IPFS
        print("--- IPFS ---")
        try:
            if not Config.PINATA_API_KEY or not Config.PINATA_SECRET_API_KEY:
                report["IPFS"] = "BLOCKED"
                print("IPFS credentials not configured.")
                ipfs_cid = "unavailable"
            else:
                resp = requests.get(best_evidence.candidate.image_url, timeout=10, stream=True)
                resp.raise_for_status()
                ipfs_client = IPFSClient()
                ipfs_cid = ipfs_client.pin_image(resp.content)
                if ipfs_cid:
                    report["IPFS"] = "PASS"
                    print(f"IPFS CID: {ipfs_cid}")
                else:
                    report["IPFS"] = "FAIL"
                    print("IPFS pinning returned empty CID.")
        except Exception as e:
            print(f"IPFS Error: {e}")
            report["IPFS"] = "FAIL"
            ipfs_cid = "unavailable"

        # 6. Evidence & SHA-256
        print("--- EVIDENCE & SHA-256 ---")
        try:
            canonical_evidence = Evidence(
                source_url=best_evidence.candidate.source_url,
                ipfs_cid=ipfs_cid,
                relevant_text=best_evidence.candidate.metadata.get('name', 'Unknown context'),
                metadata=best_evidence.candidate.metadata
            )
            report["EVIDENCE"] = "PASS"
            
            fingerprint = EvidenceFingerprinter.compute_fingerprint(canonical_evidence)
            if fingerprint:
                report["SHA-256"] = "PASS"
                print(f"SHA-256 Fingerprint: {fingerprint}")
            else:
                print("Failed to compute SHA-256 fingerprint.")
                return report, time.time() - start_time, top_candidate_url, similarity_score, fingerprint, ipfs_cid, tx_hash
        except Exception as e:
            print(f"Evidence/SHA-256 Error: {e}")
            return report, time.time() - start_time, top_candidate_url, similarity_score, fingerprint, ipfs_cid, tx_hash

        # 7. Blockchain & On-chain Re-verification
        print("--- BLOCKCHAIN ---")
        try:
            if not Config.RPC_URL or not Config.BLOCKCHAIN_PRIVATE_KEY:
                report["BLOCKCHAIN"] = "BLOCKED"
                print("Blockchain credentials not configured.")
            else:
                registry = BlockchainRegistry()
                tx_hash = registry.register_evidence(fingerprint)
                if tx_hash:
                    report["BLOCKCHAIN"] = "PASS"
                    print(f"Blockchain TX Hash: {tx_hash}")
                    
                    # On-chain re-verification
                    print("--- ON-CHAIN RE-VERIFICATION ---")
                    verifier = EvidenceVerifier(registry)
                    result_orig = verifier.verify(canonical_evidence)
                    if result_orig.is_verified:
                        report["ON-CHAIN RE-VERIFICATION"] = "PASS"
                        print("On-chain re-verification passed.")
                    else:
                        report["ON-CHAIN RE-VERIFICATION"] = "FAIL"
                        print("On-chain re-verification failed.")
                else:
                    report["BLOCKCHAIN"] = "FAIL"
                    print("Blockchain registration returned empty TX hash.")
        except Exception as e:
            print(f"Blockchain Error: {e}")
            report["BLOCKCHAIN"] = "FAIL"

        # 8. Tamper Detection
        print("--- TAMPER DETECTION ---")
        try:
            if report["BLOCKCHAIN"] == "PASS" and report["ON-CHAIN RE-VERIFICATION"] == "PASS":
                tampered = copy.deepcopy(canonical_evidence)
                tampered.ipfs_cid = "QmDeepfakeHash1234567890abcdef1234567890abcdef"
                result_tampered = verifier.verify(tampered)
                if not result_tampered.is_verified:
                    report["TAMPER DETECTION"] = "PASS"
                    print("Tamper detection successfully prevented verification of altered image binary.")
                else:
                    report["TAMPER DETECTION"] = "FAIL"
                    print("Tamper detection failed to detect altered binary.")
            else:
                report["TAMPER DETECTION"] = "BLOCKED"
                print("Tamper detection blocked due to blockchain failure/unavailability.")
        except Exception as e:
            print(f"Tamper Detection Error: {e}")
            report["TAMPER DETECTION"] = "FAIL"

    finally:
        total_runtime = time.time() - start_time
        return report, total_runtime, top_candidate_url, similarity_score, fingerprint, ipfs_cid, tx_hash

if __name__ == "__main__":
    report, total_runtime, top_candidate_url, similarity_score, fingerprint, ipfs_cid, tx_hash = run_test()
    
    print("\n\n==== END TO END REPORT ====")
    overall_status = "PASS"
    for k, v in report.items():
        print(f"{k}: {v}")
        if v == "FAIL":
            overall_status = "FAIL"
            
    print(f"\nTotal Runtime: {total_runtime:.2f} seconds")
    print(f"Top Candidate URL: {top_candidate_url}")
    print(f"Similarity Score: {similarity_score}")
    print(f"Fingerprint: {fingerprint}")
    print(f"IPFS CID: {ipfs_cid if ipfs_cid != 'unavailable' else 'Not Uploaded'}")
    print(f"Blockchain TX Hash: {tx_hash}")
    print(f"FINAL OVERALL STATUS: {overall_status}")
