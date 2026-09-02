"""
Responsible for representing discovered evidence.
"""
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class Evidence:
    source_url: str
    ipfs_cid: str
    relevant_text: str
    metadata: Dict[str, Any]
