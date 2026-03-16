# from transformers import pipeline

# toxicity_model = pipeline(
#     "text-classification",
#     model="unitary/toxic-bert"
# )

# def detect_toxicity(texts):
#     return toxicity_model(texts)


# ================================
# Cheap Alternative for Toxicity Detection (since the above model is too slow to run on CPU) = using ollama
#===================================

from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="tinyllama",
    temperature=0
)


async def detect_toxicity(texts):

    results = []

    for text in texts:

        prompt = f"""
        Determine if this YouTube comment is toxic.

        Respond with ONLY one word:
        toxic or non-toxic.

        Comment: {text}
        """

        response = await llm.ainvoke(prompt)

        output = response.content.lower().strip()

        if output.startswith("toxic"):
            label = "toxic"
        else:
            label = "non-toxic"

        results.append({
            "label": label,
            "score": None
        })

    return results