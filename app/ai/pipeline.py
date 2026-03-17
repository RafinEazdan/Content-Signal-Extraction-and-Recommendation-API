from .sentiment import analyze_sentiment
from .toxicity import detect_toxicity

async def analyze_comments(comments):
    texts = [c["text"] for c in comments]
    
    # Run both analyses concurrently for better performance
    import asyncio
    sentiments, toxicity = await asyncio.gather(
        analyze_sentiment(texts),
        detect_toxicity(texts)
    )
    
    results = []
    for i, c in enumerate(comments):
        results.append({
            "comment_id": c["comment_id"],
            "sentiment": sentiments[i]["label"],
            "sentiment_score": sentiments[i]["score"],
            "toxicity": toxicity[i]["label"],
            "toxicity_score": toxicity[i]["score"]
        })
    
    return results