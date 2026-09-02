import pytest
import copy
from unittest.mock import MagicMock
from core.evidence import Evidence
from core.verifier import EvidenceVerifier

@pytest.fixture
def dummy_evidence():
    return Evidence(
        source_url="http://x.com",
        ipfs_cid="QmHash123",
        relevant_text="Some text",
        metadata={"author": "Alice"}
    )

@pytest.fixture
def mock_registry():
    registry = MagicMock()
    return registry

def test_verify_success(dummy_evidence, mock_registry):
    # Mock registry returns success
    mock_registry.verify_evidence.return_value = {
        "exists": True,
        "timestamp": 1234567890,
        "registrar": "0x123"
    }
    
    verifier = EvidenceVerifier(mock_registry)
    result = verifier.verify(dummy_evidence)
    
    assert result.is_verified is True
    assert result.blockchain_timestamp == 1234567890
    assert "VERIFIED" in result.message

def test_verify_tampered_fails(dummy_evidence, mock_registry):
    # If fingerprint is not found, registry returns exists=False
    mock_registry.verify_evidence.return_value = {
        "exists": False,
        "timestamp": 0,
        "registrar": "0x0"
    }
    
    verifier = EvidenceVerifier(mock_registry)
    
    # Tamper the evidence
    tampered_evidence = copy.deepcopy(dummy_evidence)
    tampered_evidence.relevant_text = "Manipulated text"
    
    result = verifier.verify(tampered_evidence)
    
    assert result.is_verified is False
    assert "MISMATCH" in result.message
