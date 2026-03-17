import os
import asyncio
import aiohttp
from typing import List, Dict

from app.core.config import settings

HF_API_KEY = settings.HF_API_KEY

class ToxicityDetector:
    def __init__(self, hf_token: str = None):
        """Initialize with HF token from env or parameter"""
        self.hf_token = hf_token or HF_API_KEY
        self.headers = {"Authorization": f"Bearer {self.hf_token}"} if self.hf_token else {}

        default_models = [
            os.getenv("HF_TOXICITY_MODEL", "martin-ha/toxic-comment-model"),
            "unitary/toxic-bert",
        ]
        self.api_urls = []
        for model_id in default_models:
            self.api_urls.append(f"https://router.huggingface.co/hf-inference/models/{model_id}")
            self.api_urls.append(f"https://api-inference.huggingface.co/models/{model_id}")

        self.toxic_keywords = {
            "hate", "stupid", "idiot", "moron", "trash", "kill", "dumb", "loser", "shut up"
        }
    
    async def _call_api(self, texts: List[str], session: aiohttp.ClientSession) -> List[Dict]:
        """Make async API call"""
        payload = {"inputs": texts}

        if not self.hf_token:
            raise Exception("HF_API_KEY not provided")
        
        max_retries = 3

        last_error = None
        for api_url in self.api_urls:
            for attempt in range(max_retries):
                try:
                    async with session.post(
                        api_url,
                        headers=self.headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 503:
                            # Model is loading
                            data = await response.json()
                            wait_time = data.get("estimated_time", 20)
                            print(f"Toxicity model loading, waiting {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue

                        if response.status == 410:
                            # Endpoint removed. Try next endpoint/model.
                            body = await response.text()
                            last_error = Exception(f"410 Gone from {api_url}: {body}")
                            break

                        response.raise_for_status()
                        results = await response.json()
                        return self._format_results(results)

                except asyncio.TimeoutError:
                    last_error = Exception("Request timed out")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    break

                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    break

        raise Exception(f"API call failed: {str(last_error) if last_error else 'unknown error'}")
    
    def _format_results(self, results: List) -> List[Dict]:
        """Format API response to match expected output"""
        formatted = []
        for result in results:
            # Get top prediction
            top_pred = max(result, key=lambda x: x['score'])
            
            # Normalize label
            label = top_pred['label'].lower()
            if label == 'toxic':
                label = 'toxic'
            else:
                label = 'non-toxic'
            
            formatted.append({
                'label': label,
                'score': top_pred['score']
            })
        return formatted

    def _fallback_results(self, texts: List[str]) -> List[Dict]:
        """Local keyword-based fallback toxicity heuristic."""
        formatted = []
        for text in texts:
            lower_text = (text or "").lower()
            hits = sum(1 for word in self.toxic_keywords if word in lower_text)
            if hits > 0:
                score = min(0.99, 0.55 + 0.1 * hits)
                label = "toxic"
            else:
                score = 0.85
                label = "non-toxic"

            formatted.append({"label": label, "score": score})

        return formatted

# Global instance
_detector = None

def get_detector():
    global _detector
    if _detector is None:
        _detector = ToxicityDetector()
    return _detector

async def detect_toxicity(texts: List[str]) -> List[Dict]:
    """
    Detect toxicity in texts using HF Inference API
    
    Args:
        texts: List of text strings to analyze
        
    Returns:
        List of dicts with 'label' (toxic/non-toxic) and 'score'
    """
    detector = get_detector()

    try:
        async with aiohttp.ClientSession() as session:
            return await detector._call_api(texts, session)
    except Exception as e:
        print(f"Toxicity HF fallback activated: {e}")
        return detector._fallback_results(texts)