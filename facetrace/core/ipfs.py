import requests
import logging
from utils.config import Config

logger = logging.getLogger(__name__)

class IPFSClient:
    def __init__(self):
        self.api_key = Config.PINATA_API_KEY
        self.secret_api_key = Config.PINATA_SECRET_API_KEY

    def pin_image(self, image_bytes: bytes, filename: str = "evidence.jpg") -> str:
        """
        Uploads image bytes to IPFS via Pinata.
        Returns the IPFS CID (Content Identifier).
        """
        if not self.api_key or not self.secret_api_key:
            raise ValueError("Pinata API keys are missing. Cannot pin to IPFS.")

        url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
        headers = {
            "pinata_api_key": self.api_key,
            "pinata_secret_api_key": self.secret_api_key
        }
        
        # requests expects (filename, file_object, content_type)
        files = {
            "file": (filename, image_bytes, "image/jpeg")
        }

        try:
            response = requests.post(url, headers=headers, files=files, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("IpfsHash", "")
        except Exception as e:
            logger.error(f"Failed to pin image to IPFS: {e}")
            raise Exception(f"IPFS Pinning failed: {e}")
