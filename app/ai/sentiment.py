# from transformers import pipeline

# sentiment_model = pipeline(
#     "sentiment-analysis",
#     model="cardiffnlp/twitter-roberta-base-sentiment"
# )

# def analyze_sentiment(texts):
#     return sentiment_model(texts)

# ==================================
# Cheap Alternative for Sentiment Analysis (since the above model is too slow to run on CPU)
#=================================
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()


async def analyze_sentiment(texts):

    results = []

    for text in texts:
        score = analyzer.polarity_scores(text)["compound"]

        if score >= 0.05:
            label = "positive"
        elif score <= -0.05:
            label = "negative"
        else:
            label = "neutral"

        results.append({
            "label": label,
            "score": score
        })

    return results
