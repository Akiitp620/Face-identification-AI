import pytest
import json
from core.evidence import Evidence
from core.fingerprint import EvidenceFingerprinter

def test_deterministic_hashing():
    # Same data, dictionaries ordered differently
    evidence1 = Evidence(
        source_url="http://example.com/post/123",
        ipfs_cid="QmHash123",
        relevant_text="Some text",
        metadata={"b": 2, "a": 1, "c": 3}
    )
    
    evidence2 = Evidence(
        source_url="http://example.com/post/123",
        ipfs_cid="QmHash123",
        relevant_text="Some text",
        metadata={"a": 1, "c": 3, "b": 2}
    )
    
    # Assert JSON canonicalization is identical despite dict ordering
    json1 = EvidenceFingerprinter.to_canonical_json(evidence1)
    json2 = EvidenceFingerprinter.to_canonical_json(evidence2)
    assert json1 == json2
    
    # Fingerprints must perfectly match
    fingerprint1 = EvidenceFingerprinter.compute_fingerprint(evidence1)
    fingerprint2 = EvidenceFingerprinter.compute_fingerprint(evidence2)
    assert fingerprint1 == fingerprint2

def test_different_data_yields_different_hash():
    evidence1 = Evidence(
        source_url="http://example.com/post/123",
        ipfs_cid="QmHash123",
        relevant_text="Some text",
        metadata={"a": 1}
    )
    
    evidence2 = Evidence(
        source_url="http://example.com/post/456",  # Different URL
        ipfs_cid="QmHash123",
        relevant_text="Some text",
        metadata={"a": 1}
    )
    
    assert EvidenceFingerprinter.compute_fingerprint(evidence1) != EvidenceFingerprinter.compute_fingerprint(evidence2)
