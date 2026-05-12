import os
from typing import List, Dict
import asyncio
import aiohttp
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.core.config import settings

HF_API_KEY = settings.HF_API_KEY

class SentimentAnalyzer:
    def __init__(self, hf_token: str = None):
        """Initialize with HF token from env or parameter"""
        self.hf_token = hf_token or HF_API_KEY
        self.headers = {"Authorization": f"Bearer {self.hf_token}"} if self.hf_token else {}

        default_model = "distilbert/distilbert-base-uncased-finetuned-sst-2-english"
        model_id = os.getenv("HF_SENTIMENT_MODEL", default_model)

        # Try modern HF router endpoint first, then legacy endpoint.
        self.api_urls = [
            f"https://router.huggingface.co/hf-inference/models/{model_id}",
            f"https://api-inference.huggingface.co/models/{model_id}",
        ]

        self.vader = SentimentIntensityAnalyzer()
        
        # Label mapping for twitter-roberta-base-sentiment
        self.label_map = {
            'LABEL_0': 'negative',
            'LABEL_1': 'neutral', 
            'LABEL_2': 'positive'
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
                            print(f"Model loading, waiting {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue

                        if response.status == 410:
                            # Model endpoint removed; try the next endpoint/model.
                            body = await response.text()
                            last_error = Exception(f"410 Gone from {api_url}: {body}")
                            break

                        response.raise_for_status()
                        results = await response.json()
                        return self._format_results(results)

                except asyncio.TimeoutError:
                    last_error = Exception("Request timed out")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    break

                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    break

        raise Exception(f"API call failed: {str(last_error) if last_error else 'unknown error'}")
        
    def _fallback_results(self, texts: List[str]) -> List[Dict]:
        """Local fallback sentiment using VADER so API outages do not break analysis."""
        formatted = []
        for text in texts:
            compound = self.vader.polarity_scores(text or "")["compound"]
            if compound >= 0.05:
                label = "positive"
            elif compound <= -0.05:
                label = "negative"
            else:
                label = "neutral"

            formatted.append({
                "label": label,
                "score": abs(compound)
            })
        return formatted
    
    def _format_results(self, results: List) -> List[Dict]:
        """Format API response to match expected output"""
        formatted = []
        for result in results:
            # Get top prediction
            top_pred = max(result, key=lambda x: x['score'])
            formatted.append({
                'label': self.label_map.get(top_pred['label'], top_pred['label']),
                'score': top_pred['score']
            })
        return formatted

# Global instance
_analyzer = None

def get_analyzer():
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentAnalyzer()
    return _analyzer

async def analyze_sentiment(texts: List[str]) -> List[Dict]:
    """
    Analyze sentiment of texts using HF Inference API
    
    Args:
        texts: List of text strings to analyze
        
    Returns:
        List of dicts with 'label' (negative/neutral/positive) and 'score'
    """
    analyzer = get_analyzer()

    try:
        async with aiohttp.ClientSession() as session:
            return await analyzer._call_api(texts, session)
    except Exception as e:
        print(f"Sentiment HF fallback activated: {e}")
        return analyzer._fallback_results(texts)