import requests
import logging
from typing import List
from dataclasses import dataclass
from utils.config import Config

logger = logging.getLogger(__name__)

MAX_IMAGE_SIZE_BYTES = 500 * 1024


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
        """Genuine reverse image search using SerpApi Google Lens."""

        if not self.api_key:
            raise ValueError(
                "SERPAPI_API_KEY is missing. Cannot perform genuine discovery."
            )

        if not image_bytes:
            raise ValueError("Image is empty. Please provide a valid image.")

        if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
            raise ValueError(
                f"Image exceeds the 500 KB web-discovery limit. "
                f"Selected image: {len(image_bytes) / 1024:.1f} KB."
            )

        # Step 1: Upload image to SerpApi
        try:
            response = requests.post(
                "https://serpapi.com/image",
                params={"api_key": self.api_key},
                files={"image": ("image.jpg", image_bytes, "image/jpeg")},
                timeout=30,
            )
            response.raise_for_status()
            image_id = response.json().get("image_id")

            if not image_id:
                raise ValueError("SerpApi did not return an image_id.")

        except requests.exceptions.RequestException as e:
            logger.error("Discovery upload failed: %s", e)
            raise ConnectionError(f"Failed to upload image: {e}") from e

        # Step 2: Search using Google Lens
        try:
            response = requests.get(
                "https://serpapi.com/search",
                params={
                    "engine": "google_lens",
                    "image_id": image_id,
                    "api_key": self.api_key,
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

        except requests.exceptions.RequestException as e:
            logger.error("Discovery search failed: %s", e)
            raise ConnectionError(
                f"Failed to communicate with discovery provider: {e}"
            ) from e

        candidates = []

        for match in data.get("exact_matches", []) + data.get("visual_matches", []):
            source_url = match.get("link", "")
            image_url = match.get("thumbnail", "")

            if not source_url or not image_url:
                continue

            candidates.append(
                CandidateResult(
                    source_url=source_url,
                    image_url=image_url,
                    metadata={
                        "name": match.get("title", ""),
                        "date": match.get("date", ""),
                        "source": match.get("source", ""),
                    },
                )
            )

        return candidates