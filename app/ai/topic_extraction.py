import asyncio
import json
import os
import re
from collections import Counter
from typing import Any, Dict, List

import aiohttp

from app.core.config import settings

HF_API_KEY = settings.HF_API_KEY


GENERIC_TERMS = {
    "good",
    "great",
    "nice",
    "awesome",
    "amazing",
    "cool",
    "wow",
    "best",
    "love",
    "liked",
    "super",
    "beautiful",
    "perfect",
    "thanks",
    "thank",
    "video",
    "content",
    "bro",
    "sir",
    "please",
    "channel",
    "subscribe",
    "subscribed",
    "liked",
    "like",
}

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "were",
    "with",
    "you",
    "your",
    "me",
    "my",
    "we",
    "our",
    "they",
    "their",
}

WEAK_SINGLE_WORD_TOPICS = {
    "have",
    "very",
    "seen",
    "make",
    "made",
    "thing",
    "things",
    "stuff",
    "topic",
    "topics",
    "idea",
    "ideas",
    "more",
    "much",
    "many",
    "some",
    "any",
    "all",
    "none",
    "also",
    "just",
    "really",
    "maybe",
    "please",
    "otters",
}

INTENT_PATTERNS = [
    re.compile(r"(?:make|do|create|upload|cover|explain|discuss|talk\s+about)\s+(?:a\s+)?(?:video\s+)?(?:on|about)?\s*([a-z0-9][a-z0-9\s\-]{2,80})", re.IGNORECASE),
    re.compile(r"(?:video|episode|part)\s+(?:on|about)\s+([a-z0-9][a-z0-9\s\-]{2,80})", re.IGNORECASE),
    re.compile(r"(?:next|another)\s+(?:video|episode|part)\s+(?:on|about)\s+([a-z0-9][a-z0-9\s\-]{2,80})", re.IGNORECASE),
    re.compile(r"(?:please|plz)?\s*(?:make|do)\s+(?:one\s+)?(?:on|about)\s+([a-z0-9][a-z0-9\s\-]{2,80})", re.IGNORECASE),
]


def _clean_text(text: str) -> str:
    text = text or ""
    # Remove HTML tags from YouTube textDisplay content.
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_topic(topic: str) -> str:
    topic = (topic or "").strip().lower()
    topic = re.sub(r"[^a-z0-9\s\-]", "", topic)
    topic = re.sub(r"\s+", " ", topic)
    return topic.strip(" -")


def _is_meaningful_topic(topic: str) -> bool:
    if not topic:
        return False

    tokens = [t for t in topic.split() if t]
    if not tokens:
        return False

    # Reject very short and mostly generic responses.
    if len(tokens) == 1:
        word = tokens[0]
        if len(word) < 4:
            return False
        if word in GENERIC_TERMS or word in STOP_WORDS:
            return False
        if word in WEAK_SINGLE_WORD_TOPICS:
            return False

    non_generic = [t for t in tokens if t not in GENERIC_TERMS and t not in STOP_WORDS]
    if not non_generic:
        return False

    # Reject phrases that start/end with function words, usually artifacts.
    if tokens[0] in STOP_WORDS or tokens[-1] in STOP_WORDS:
        return False

    if tokens[0] in WEAK_SINGLE_WORD_TOPICS or tokens[-1] in WEAK_SINGLE_WORD_TOPICS:
        return False

    # Avoid boilerplate praise patterns with no concrete topic.
    if all(t in GENERIC_TERMS or t in STOP_WORDS for t in tokens):
        return False

    return True


def _is_idea_candidate(topic: str, count: int) -> bool:
    tokens = [t for t in topic.split() if t]
    if len(tokens) >= 2:
        return True

    if len(tokens) == 1 and count >= 3 and tokens[0] not in WEAK_SINGLE_WORD_TOPICS:
        return True

    return False


def _trim_phrase(phrase: str) -> str:
    phrase = re.split(r"[\.,;!\?]|\b(?:because|but|and|so|though)\b", phrase, maxsplit=1)[0]
    return _normalize_topic(phrase)


def _extract_intent_topics(comments: List[str]) -> Counter:
    counter: Counter = Counter()
    for comment in comments:
        text = comment.lower()
        for pattern in INTENT_PATTERNS:
            for match in pattern.findall(text):
                candidate = _trim_phrase(str(match))
                if _is_meaningful_topic(candidate):
                    counter[candidate] += 1
    return counter


def _rank_topics(counter: Counter, top_k: int, total_comments: int) -> List[Dict[str, Any]]:
    min_count = 2 if total_comments >= 10 else 1
    ranked: List[Dict[str, Any]] = []
    for topic, count in counter.most_common(max(1, top_k * 5)):
        if count < min_count:
            continue
        if not _is_meaningful_topic(topic):
            continue

        # Single-word topics need stronger evidence.
        tokens = [t for t in topic.split() if t]
        if len(tokens) == 1 and count < 3:
            continue

        ranked.append({"topic": topic, "count": count})
        if len(ranked) >= max(1, top_k):
            break

    return ranked


def _chunk_comments(comments: List[str], chunk_size: int) -> List[List[str]]:
    return [comments[i : i + chunk_size] for i in range(0, len(comments), chunk_size)]


def _extract_statistical_topics(comments: List[str], top_k: int) -> List[Dict[str, Any]]:
    phrase_counter: Counter = Counter()

    for comment in comments:
        tokens = [
            token
            for token in re.findall(r"[a-zA-Z][a-zA-Z0-9'-]{2,}", comment.lower())
            if token not in STOP_WORDS and token not in GENERIC_TERMS
        ]

        # Count each phrase once per comment to reduce spammy duplication.
        seen_in_comment = set()
        for n in (2, 3):
            for i in range(len(tokens) - n + 1):
                phrase = " ".join(tokens[i : i + n])
                if _is_meaningful_topic(phrase):
                    seen_in_comment.add(phrase)

        for phrase in seen_in_comment:
            phrase_counter[phrase] += 1

    return [
        {"topic": topic, "count": count}
        for topic, count in phrase_counter.most_common(max(1, top_k * 3))
        if count >= 2
    ][: max(1, top_k)]


def _suggest_next_video_ideas(topics: List[Dict[str, Any]], idea_count: int = 4) -> List[str]:
    normalized_topics: List[str] = []
    for item in topics:
        topic = _normalize_topic(str(item.get("topic", "")))
        count = int(item.get("count", 1))
        if topic and _is_idea_candidate(topic, count) and topic not in normalized_topics:
            normalized_topics.append(topic)

    defaults = [
        "Audience request roundup",
        "Subscriber Q&A based on recent comments",
        "Practical walkthrough from top comment themes",
        "Common confusion points explained clearly",
    ]
    merged = normalized_topics + [d for d in defaults if d not in normalized_topics]
    return merged[:idea_count]


def _extract_json_blob(text: str) -> Any:
    text = text.strip()

    # Fast path: raw JSON.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Common path: model returns text around JSON.
    start_obj = text.find("{")
    start_arr = text.find("[")
    start = min([i for i in [start_obj, start_arr] if i != -1], default=-1)
    if start == -1:
        return []

    for end in range(len(text), start, -1):
        candidate = text[start:end].strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    return []


def _parse_topics(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        payload = payload.get("topics", [])

    if not isinstance(payload, list):
        return []

    topics: List[Dict[str, Any]] = []
    for item in payload:
        if isinstance(item, dict):
            topic = _normalize_topic(str(item.get("topic", "")))
            count = item.get("count", 1)
            try:
                count = int(count)
            except (TypeError, ValueError):
                count = 1
        else:
            topic = _normalize_topic(str(item))
            count = 1

        if _is_meaningful_topic(topic):
            topics.append({"topic": topic, "count": max(1, count)})

    return topics


def _build_prompt(comments: List[str], per_chunk_topics: int) -> str:
    numbered_comments = "\n".join(
        f"{idx + 1}. {comment}" for idx, comment in enumerate(comments)
    )

    return (
        "You are extracting meaningful discussion topics from user comments.\n"
        "Focus on concrete requests, subjects, entities, and recurring ideas.\n"
        "Ignore generic praise words like good, nice, awesome, great.\n"
        "Expand short mentions into clearer topic phrases when possible.\n"
        "Return valid JSON only in this format:\n"
        "{\"topics\": [{\"topic\": \"short phrase\", \"count\": 3}]}\n"
        f"Return at most {per_chunk_topics} items.\n"
        "Topic should be 2-10 words and human-readable with context.\n"
        "Count is how many comments in this batch mention that topic.\n"
        "Comments:\n"
        f"{numbered_comments}\n"
    )


def _parse_ideas(payload: Any) -> List[str]:
    if isinstance(payload, dict):
        payload = payload.get("ideas", [])

    if not isinstance(payload, list):
        return []

    ideas: List[str] = []
    for item in payload:
        if not isinstance(item, str):
            continue
        cleaned = re.sub(r"\s+", " ", item).strip()
        if len(cleaned) < 10:
            continue
        if cleaned not in ideas:
            ideas.append(cleaned)
    return ideas


class TopicExtractor:
    def __init__(
        self,
        provider: str = "huggingface",
        model: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        hf_token: str = None,
        ollama_url: str = None,
    ):
        self.provider = (provider or "huggingface").lower()
        self.model = model
        self.hf_token = hf_token or HF_API_KEY
        self.ollama_url = ollama_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    async def _extract_with_hf(self, prompt: str, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        if not self.hf_token:
            raise Exception("HF_API_KEY not provided")

        headers = {"Authorization": f"Bearer {self.hf_token}"}
        urls = [
            f"https://router.huggingface.co/hf-inference/models/{self.model}",
            f"https://api-inference.huggingface.co/models/{self.model}",
        ]

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 320,
                "temperature": 0.1,
                "return_full_text": False,
            },
        }

        last_error = None
        for url in urls:
            try:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=45),
                ) as response:
                    if response.status == 503:
                        data = await response.json()
                        wait_for = int(data.get("estimated_time", 15))
                        await asyncio.sleep(wait_for)
                        continue

                    response.raise_for_status()
                    body = await response.json()
            except Exception as exc:
                last_error = exc
                continue

            generated = ""
            if isinstance(body, list) and body:
                first_item = body[0]
                if isinstance(first_item, dict):
                    generated = first_item.get("generated_text", "")
                else:
                    generated = str(first_item)
            elif isinstance(body, dict):
                generated = str(body.get("generated_text", body))

            return _parse_topics(_extract_json_blob(generated))

        raise Exception(f"HF topic extraction failed: {last_error}")

    async def _extract_with_ollama(self, prompt: str, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
            },
            "format": "json",
        }

        async with session.post(
            f"{self.ollama_url.rstrip('/')}/api/generate",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as response:
            response.raise_for_status()
            body = await response.json()

        generated = body.get("response", "")
        return _parse_topics(_extract_json_blob(generated))

    async def _generate_ideas_with_hf(
        self,
        prompt: str,
        session: aiohttp.ClientSession,
    ) -> List[str]:
        if not self.hf_token:
            raise Exception("HF_API_KEY not provided")

        headers = {"Authorization": f"Bearer {self.hf_token}"}
        urls = [
            f"https://router.huggingface.co/hf-inference/models/{self.model}",
            f"https://api-inference.huggingface.co/models/{self.model}",
        ]

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 420,
                "temperature": 0.7,
                "return_full_text": False,
            },
        }

        last_error = None
        for url in urls:
            try:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    if response.status == 503:
                        data = await response.json()
                        wait_for = int(data.get("estimated_time", 15))
                        await asyncio.sleep(wait_for)
                        continue

                    response.raise_for_status()
                    body = await response.json()
            except Exception as exc:
                last_error = exc
                continue

            generated = ""
            if isinstance(body, list) and body:
                first_item = body[0]
                if isinstance(first_item, dict):
                    generated = first_item.get("generated_text", "")
                else:
                    generated = str(first_item)
            elif isinstance(body, dict):
                generated = str(body.get("generated_text", body))

            return _parse_ideas(_extract_json_blob(generated))

        raise Exception(f"HF idea generation failed: {last_error}")

    async def _generate_ideas_with_ollama(
        self,
        prompt: str,
        session: aiohttp.ClientSession,
    ) -> List[str]:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
            },
            "format": "json",
        }

        async with session.post(
            f"{self.ollama_url.rstrip('/')}/api/generate",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as response:
            response.raise_for_status()
            body = await response.json()

        generated = body.get("response", "")
        return _parse_ideas(_extract_json_blob(generated))

    async def _generate_next_video_ideas(
        self,
        topics: List[Dict[str, Any]],
        session: aiohttp.ClientSession,
        idea_count: int = 4,
    ) -> List[str]:
        topic_lines = "\n".join(
            f"- {item['topic']} (mentions: {item['count']})" for item in topics[:20]
        )

        prompt = (
            "You are a content strategist for a creator channel.\n"
            "Generate original next-video ideas from these audience topics.\n"
            "Do not use templates, avoid repetitive phrasing, and keep each idea specific.\n"
            "Return valid JSON only in this format:\n"
            "{\"ideas\": [\"idea 1\", \"idea 2\", \"idea 3\", \"idea 4\"]}\n"
            f"Return exactly {idea_count} ideas.\n"
            "Topics:\n"
            f"{topic_lines}\n"
        )

        if self.provider == "ollama":
            ideas = await self._generate_ideas_with_ollama(prompt, session)
        else:
            ideas = await self._generate_ideas_with_hf(prompt, session)

        if len(ideas) >= idea_count:
            return ideas[:idea_count]

        # If model output is short or malformed, return raw top topics instead of templates.
        topic_fallback = [item["topic"] for item in topics if item.get("topic")]
        topic_fallback = list(dict.fromkeys(topic_fallback))
        if len(topic_fallback) >= idea_count:
            return topic_fallback[:idea_count]

        defaults = [
            "Audience request roundup",
            "Subscriber Q&A based on recent comments",
            "Practical walkthrough from top comment themes",
            "Common confusion points explained clearly",
        ]
        merged = topic_fallback + [d for d in defaults if d not in topic_fallback]
        return merged[:idea_count]

    async def _extract_chunk_topics(
        self,
        comments_chunk: List[str],
        session: aiohttp.ClientSession,
        per_chunk_topics: int,
    ) -> List[Dict[str, Any]]:
        prompt = _build_prompt(comments_chunk, per_chunk_topics)

        if self.provider == "ollama":
            return await self._extract_with_ollama(prompt, session)

        return await self._extract_with_hf(prompt, session)

    async def extract_topics(
        self,
        comments: List[str],
        top_k: int = 15,
        chunk_size: int = 40,
        per_chunk_topics: int = 12,
        max_parallel_requests: int = 4,
    ) -> Dict[str, Any]:
        cleaned_comments = []
        for raw_comment in comments:
            cleaned = _clean_text(raw_comment)
            if cleaned:
                cleaned_comments.append(cleaned)

        if not cleaned_comments:
            return {
                "provider": self.provider,
                "model": self.model,
                "total_comments": 0,
                "chunks_processed": 0,
                "topics": [],
                "next_video_ideas": _suggest_next_video_ideas([]),
            }

        chunks = _chunk_comments(cleaned_comments, max(1, chunk_size))
        semaphore = asyncio.Semaphore(max(1, max_parallel_requests))

        async with aiohttp.ClientSession() as session:
            async def run_chunk(chunk: List[str]) -> List[Dict[str, Any]]:
                async with semaphore:
                    try:
                        return await self._extract_chunk_topics(chunk, session, per_chunk_topics)
                    except Exception:
                        return []

            chunk_results = await asyncio.gather(*(run_chunk(chunk) for chunk in chunks))

        counter: Counter = Counter()
        for topics in chunk_results:
            for item in topics:
                topic = item["topic"]
                count = int(item.get("count", 1))
                counter[topic] += max(1, count)

        # Boost directly requested/suggested topics from comment intent patterns.
        intent_counter = _extract_intent_topics(cleaned_comments)
        for topic, count in intent_counter.items():
            counter[topic] += count

        ranked = _rank_topics(counter, top_k=top_k, total_comments=len(cleaned_comments))

        if not ranked:
            ranked = _extract_statistical_topics(cleaned_comments, top_k=top_k)

        async with aiohttp.ClientSession() as session:
            try:
                next_video_ideas = await self._generate_next_video_ideas(ranked, session, idea_count=4)
            except Exception:
                next_video_ideas = _suggest_next_video_ideas(ranked, idea_count=4)

        return {
            "provider": self.provider,
            "model": self.model,
            "total_comments": len(cleaned_comments),
            "chunks_processed": len(chunks),
            "topics": ranked,
            "next_video_ideas": next_video_ideas,
        }


async def extract_topics_from_comments(
    comments: List[str],
    provider: str = "huggingface",
    model: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    top_k: int = 30,
    chunk_size: int = 40,
    per_chunk_topics: int = 20,
    max_parallel_requests: int = 4,
) -> Dict[str, Any]:
    extractor = TopicExtractor(provider=provider, model=model)
    return await extractor.extract_topics(
        comments=comments,
        top_k=top_k,
        chunk_size=chunk_size,
        per_chunk_topics=per_chunk_topics,
        max_parallel_requests=max_parallel_requests,
    )
