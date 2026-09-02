"""
Responsible ONLY for genuine web/social discovery.
"""
import requests
import logging
from typing import List
from dataclasses import dataclass
from utils.config import Config

logger = logging.getLogger(__name__)

@dataclass
class CandidateResult:
    source_url: str
    image_url: str
    metadata: dict

class DiscoveryEngine:
    def __init__(self):
        self.api_key = Config.SERPAPI_API_KEY
        if not self.api_key:
            logger.warning("SERPAPI_API_KEY is not set. Discovery will fail.")

    def search(self, image_bytes: bytes) -> List[CandidateResult]:
        """
        Genuine reverse image search using SerpApi Google Lens.
        """
        if not self.api_key:
            raise ValueError("SERPAPI_API_KEY is missing. Cannot perform genuine discovery.")

        # Step 1: Upload image to SerpApi
        upload_url = "https://serpapi.com/image"
        upload_params = {'api_key': self.api_key}
        # The file tuple must include a filename, otherwise it might be rejected by the endpoint.
        files = {'image': ('image.jpg', image_bytes, 'image/jpeg')}

        try:
            upload_response = requests.post(upload_url, params=upload_params, files=files, timeout=30)
            upload_response.raise_for_status()
            upload_data = upload_response.json()
            image_id = upload_data.get('image_id')
            if not image_id:
                raise ValueError("Failed to retrieve image_id from SerpApi upload response.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Discovery upload failed: {e}")
            raise ConnectionError(f"Failed to upload image to discovery provider: {e}")

        # Step 2: Search using image_id with Google Lens
        search_url = "https://serpapi.com/search"
        search_params = {
            "engine": "google_lens",
            "image_id": image_id,
            "api_key": self.api_key
        }

        try:
            search_response = requests.get(search_url, params=search_params, timeout=30)
            search_response.raise_for_status()
            data = search_response.json()

            candidates = []
            
            # Helper to parse matches
            def parse_matches(matches):
                for match in matches:
                    source_url = match.get('link', '')
                    image_url = match.get('thumbnail', '')
                    
                    if not source_url or not image_url:
                        continue
                        
                    candidates.append(CandidateResult(
                        source_url=source_url,
                        image_url=image_url,
                        metadata={
                            'name': match.get('title', ''),
                            'date': match.get('date', ''),
                            'source': match.get('source', '')
                        }
                    ))

            # Prioritize exact matches, then add visual matches
            parse_matches(data.get('exact_matches', []))
            parse_matches(data.get('visual_matches', []))

            return candidates

        except requests.exceptions.RequestException as e:
            logger.error(f"Discovery search failed: {e}")
            raise ConnectionError(f"Failed to communicate with discovery provider: {e}")


