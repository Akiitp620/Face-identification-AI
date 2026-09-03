import pytest
from unittest.mock import patch, MagicMock
from core.discovery import DiscoveryEngine, CandidateResult

@pytest.fixture
def mock_config():
    with patch('core.discovery.Config') as mock:
        mock.SERPAPI_API_KEY = "dummy_key"
        yield mock

def test_discovery_no_key():
    with patch('core.discovery.Config.SERPAPI_API_KEY', None):
        engine = DiscoveryEngine()
        with pytest.raises(ValueError, match="SERPAPI_API_KEY is missing"):
            engine.search(b"dummy_bytes")

def test_discovery_oversized_image(mock_config):
    engine = DiscoveryEngine()
    large_bytes = b"0" * (500 * 1024 + 1)
    with pytest.raises(ValueError, match="Image exceeds the 500 KB web-discovery limit."):
        engine.search(large_bytes)

@patch('core.discovery.requests.get')
@patch('core.discovery.requests.post')
def test_discovery_success(mock_post, mock_get, mock_config):
    # Mock Step 1: Upload Image
    mock_upload_response = MagicMock()
    mock_upload_response.json.return_value = {"image_id": "dummy_image_id"}
    mock_post.return_value = mock_upload_response

    # Mock Step 2: Search Google Lens
    mock_search_response = MagicMock()
    mock_search_response.json.return_value = {
        "exact_matches": [
            {"link": "http://example.com", "thumbnail": "http://img.com/1.jpg", "title": "Match 1", "date": "2023-01-01"}
        ],
        "visual_matches": [
            {"link": "http://example.com/2", "thumbnail": "http://img.com/2.jpg", "title": "Match 2"}
        ]
    }
    mock_get.return_value = mock_search_response
    
    engine = DiscoveryEngine()
    candidates = engine.search(b"dummy_bytes")
    
    assert len(candidates) == 2
    assert candidates[0].source_url == "http://example.com"
    assert candidates[0].image_url == "http://img.com/1.jpg"
    assert candidates[0].metadata['name'] == "Match 1"
    
    assert candidates[1].source_url == "http://example.com/2"
    assert candidates[1].image_url == "http://img.com/2.jpg"
    assert candidates[1].metadata['name'] == "Match 2"

@patch('core.discovery.requests.post')
def test_discovery_api_upload_failure(mock_post, mock_config):
    import requests
    mock_post.side_effect = requests.exceptions.RequestException("Upload Down")
    
    engine = DiscoveryEngine()
    with pytest.raises(ConnectionError, match="Failed to upload image"):
        engine.search(b"dummy_bytes")

@patch('core.discovery.requests.get')
@patch('core.discovery.requests.post')
def test_discovery_api_search_failure(mock_post, mock_get, mock_config):
    import requests
    
    mock_upload_response = MagicMock()
    mock_upload_response.json.return_value = {"image_id": "dummy_image_id"}
    mock_post.return_value = mock_upload_response

    mock_get.side_effect = requests.exceptions.RequestException("Search Down")
    
    engine = DiscoveryEngine()
    with pytest.raises(ConnectionError, match="Failed to communicate"):
        engine.search(b"dummy_bytes")
