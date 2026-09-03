import sys
from unittest.mock import MagicMock, AsyncMock
sys.modules['facenet_pytorch'] = MagicMock()

import pytest
import numpy as np
from unittest.mock import patch
from core.candidate_ranker import CandidateRanker, RankedEvidence
from core.discovery import CandidateResult
from core.face_engine import FaceEngine
import aiohttp

@pytest.fixture
def dummy_face_engine():
    engine = MagicMock(spec=FaceEngine)
    return engine

@pytest.fixture
def dummy_candidates():
    return [
        CandidateResult(source_url="http://a.com", image_url="http://a.com/img.jpg", metadata={}),
        CandidateResult(source_url="http://b.com", image_url="http://b.com/img.jpg", metadata={})
    ]

def test_similarity_calculation(dummy_face_engine):
    ranker = CandidateRanker(dummy_face_engine)
    a = np.array([1, 0, 0])
    b = np.array([1, 0, 0])
    assert ranker._calculate_similarity(a, b) == 1.0
    
    c = np.array([0, 1, 0])
    assert ranker._calculate_similarity(a, c) == 0.0

@patch('core.candidate_ranker.aiohttp.ClientSession.get')
@patch('core.candidate_ranker.Image.open')
def test_rank_candidates(mock_image_open, mock_get, dummy_face_engine, dummy_candidates):
    # Mock network & image
    mock_resp = AsyncMock()
    mock_resp.read.return_value = b"fake_bytes"
    mock_resp.headers = {'Content-Length': '100', 'Content-Type': 'image/jpeg'}
    mock_resp.raise_for_status = MagicMock()
    
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_resp
    mock_get.return_value = mock_ctx
    
    mock_img = MagicMock()
    mock_img.convert.return_value = mock_img
    mock_image_open.return_value = mock_img

    # Return slightly different embeddings to ensure sorting works
    # cand 0 gets [0, 1] (sim 0.0), cand 1 gets [1, 0] (sim 1.0)
    dummy_face_engine.process_face.side_effect = [
        np.array([0, 1]), 
        np.array([1, 0])
    ]
    
    base_embedding = np.array([1, 0])
    ranker = CandidateRanker(dummy_face_engine)
    
    ranked = ranker.rank_candidates(base_embedding, dummy_candidates)
    
    # Assert ranked sorted by similarity descending
    assert len(ranked) == 2
    assert ranked[0].face_similarity == 1.0
    assert ranked[0].evidence_match_score == 100.0
    assert ranked[0].candidate.source_url == "http://b.com"
    
    assert ranked[1].face_similarity == 0.0
    assert ranked[1].evidence_match_score == 0.0
    assert ranked[1].candidate.source_url == "http://a.com"

@patch('core.candidate_ranker.aiohttp.ClientSession.get')
def test_rank_candidates_skips_errors(mock_get, dummy_face_engine, dummy_candidates):
    # cand 0 network fails, cand 1 succeeds
    def mock_get_side_effect(url, **kwargs):
        if url == "http://a.com/img.jpg":
            raise aiohttp.ClientError("Network error")
        mock_resp = AsyncMock()
        mock_resp.read.return_value = b"fake_bytes"
        mock_resp.headers = {'Content-Length': '100', 'Content-Type': 'image/jpeg'}
        mock_resp.raise_for_status = MagicMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_resp
        return mock_ctx
        
    mock_get.side_effect = mock_get_side_effect
    
    base_embedding = np.array([1, 0])
    with patch('core.candidate_ranker.Image.open') as mock_image_open:
        mock_img = MagicMock()
        mock_img.convert.return_value = mock_img
        mock_image_open.return_value = mock_img
        dummy_face_engine.process_face.return_value = np.array([1, 0])
        
        ranker = CandidateRanker(dummy_face_engine)
        ranked = ranker.rank_candidates(base_embedding, dummy_candidates)
        
        # Only cand 1 survived
        assert len(ranked) == 1
        assert ranked[0].candidate.source_url == "http://b.com"

def test_select_best_evidence(dummy_face_engine):
    ranker = CandidateRanker(dummy_face_engine)
    c1 = RankedEvidence(candidate=None, face_similarity=0.8, evidence_match_score=80.0)
    c2 = RankedEvidence(candidate=None, face_similarity=0.4, evidence_match_score=40.0)
    
    best = ranker.select_best_evidence([c1, c2], threshold=0.5)
    assert best == c1
    
    best_low = ranker.select_best_evidence([c2], threshold=0.5)
    assert best_low is None
