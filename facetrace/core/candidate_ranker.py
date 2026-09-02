"""
Responsible for candidate evaluation.
"""

import numpy as np
import logging
import asyncio
import aiohttp
from PIL import Image, UnidentifiedImageError
from io import BytesIO
from typing import List, Optional
from dataclasses import dataclass
from core.face_engine import FaceEngine
from core.discovery import CandidateResult

logger = logging.getLogger(__name__)

@dataclass
class RankedEvidence:
    candidate: CandidateResult
    face_similarity: float
    evidence_match_score: float

class CandidateRanker:
    def __init__(self, face_engine: FaceEngine):
        self.face_engine = face_engine

    async def _fetch_image_safe(self, session: aiohttp.ClientSession, cand: CandidateResult) -> Optional[Image.Image]:
        """
        Safely fetches an image asynchronously.
        Enforces a 5-second timeout, checks Content-Length (<5MB), and validates Content-Type.
        """
        try:
            # 5-second timeout to prevent stalling
            timeout = aiohttp.ClientTimeout(total=5.0)
            async with session.get(cand.image_url, timeout=timeout) as resp:
                resp.raise_for_status()
                
                # Prevent Image Bombing / SSRF DoS
                content_length = resp.headers.get('Content-Length')
                if content_length and int(content_length) > 5 * 1024 * 1024:
                    logger.warning(f"Skipping {cand.image_url}: File too large ({content_length} bytes)")
                    return None
                    
                content_type = resp.headers.get('Content-Type', '')
                if not content_type.startswith('image/'):
                    logger.warning(f"Skipping {cand.image_url}: Not an image ({content_type})")
                    return None

                data = await resp.read()
                image = Image.open(BytesIO(data)).convert('RGB')
                return image
        except asyncio.TimeoutError:
            logger.debug(f"Timeout fetching {cand.image_url}")
        except aiohttp.ClientError as e:
            logger.debug(f"ClientError fetching {cand.image_url}: {e}")
        except UnidentifiedImageError:
            logger.debug(f"Invalid image format at {cand.image_url}")
        except Exception as e:
            logger.debug(f"Skipping candidate {cand.source_url} due to error: {e}")
            
        return None

    async def _process_candidate_async(self, session: aiohttp.ClientSession, base_embedding: np.ndarray, cand: CandidateResult) -> Optional[RankedEvidence]:
        image = await self._fetch_image_safe(session, cand)
        if not image:
            return None
            
        try:
            # Note: This is blocking CPU work, but for a hackathon we'll run it in the loop
            # Ideally this would be offloaded to an executor or batched.
            embedding = self.face_engine.process_face(image)
            sim = self._calculate_similarity(base_embedding, embedding)
            
            return RankedEvidence(
                candidate=cand,
                face_similarity=sim,
                evidence_match_score=max(0.0, sim * 100)
            )
        except Exception as e:
            # FaceEngine raises ValueError if no face or multiple faces found
            logger.debug(f"Face processing failed for {cand.source_url}: {e}")
            return None

    def rank_candidates(self, base_embedding: np.ndarray, candidates: List[CandidateResult]) -> List[RankedEvidence]:
        """
        Synchronous entrypoint that runs the async gathering.
        Limits to the first 10 candidates to prevent UI freezing.
        """
        # Limit to 10 to avoid stalling the demo
        candidates = candidates[:10]
        
        async def _run_all():
            async with aiohttp.ClientSession() as session:
                tasks = [self._process_candidate_async(session, base_embedding, cand) for cand in candidates]
                return await asyncio.gather(*tasks)

        # Use asyncio.run to execute the coroutines
        results = asyncio.run(_run_all())
        
        # Filter out None results and sort
        ranked = [r for r in results if r is not None]
        ranked.sort(key=lambda x: x.face_similarity, reverse=True)
        return ranked
        
    def select_best_evidence(self, ranked_candidates: List[RankedEvidence], threshold: float = 0.6) -> RankedEvidence:
        if not ranked_candidates:
            return None
        best = ranked_candidates[0]
        return best if best.face_similarity >= threshold else None

    def _calculate_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
