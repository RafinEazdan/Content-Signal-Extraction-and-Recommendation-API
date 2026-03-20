# Content Signal Extraction and Recommendation API

Production-style FastAPI backend that transforms raw YouTube channel activity into actionable content signals for recommendation workflows.

## Why This Project

This API was built to solve a practical creator/business problem:

- Collect engagement data from YouTube channels
- Analyze audience sentiment and toxicity at comment level
- Extract high-signal topic requests from comments
- Generate candidate video titles from those signals

In short, it turns audience feedback into structured recommendation inputs.

## Core Features

- Secure user auth with OTP signup (Redis) and JWT login
- Channel ingestion with cache-first fetch (Redis -> DB -> YouTube API)
- Video ingestion and de-duplication for tracked channels
- Daily video metrics snapshots with upsert semantics
- Comment ingestion with conflict-safe persistence
- AI-powered comment analysis:
  - sentiment
  - toxicity
- Topic extraction and LLM-generated title recommendations

## High-Level Architecture

- API Layer: FastAPI routers (`app/api/v1`)
- Service Layer: business logic (`app/services`)
- AI Layer: NLP + title generation pipeline (`app/ai`)
- Data Layer: PostgreSQL + SQLAlchemy models + Alembic migrations
- Cache Layer: Redis for OTP state and channel caching

## Tech Stack

- Python, FastAPI, Uvicorn
- PostgreSQL (psycopg), SQLAlchemy, Alembic
- Redis (`redis.asyncio`)
- JWT + Argon2 (passlib)
- YouTube Data API v3
- Hugging Face Inference API
- Ollama (local model for title generation)

## API Snapshot

Key endpoints currently available:

- `POST /login`
- `POST /users/signup/send-otp`
- `POST /users/signup/verify-otp`
- `GET /users/profile`
- `DELETE /users/profile/delete`
- `POST /channels/`
- `POST /videos/store`
- `POST /metrics/`
- `POST /fetch_comments`
- `POST /comment_analysis`
- `POST /video_recommendation/comments`

Interactive docs:

- `http://127.0.0.1:8000/docs`

## Quick Start

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file with:

- `YT_API_KEY`
- `DATABASE_URL`
- `SECRET_KEY`
- `POSTGRES_PASSWORD`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `ALGORITHM`
- `REDIS_URL`
- `HF_API_KEY`

Run migrations and start the API:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

## Practical Use Cases

- Creator tools that prioritize what audience wants next
- Marketing analytics for trend and sentiment tracking
- Recommendation systems that combine engagement + language signals
- Moderation-aware content pipelines (toxicity-aware signal filtering)

## Current Scope and Notes

- Video ingestion currently pulls first playlist page (`maxResults=20`)
- Recommendation title generation expects local Ollama availability
- Some comment-related endpoints are currently open (no auth)

## Recruiter-Friendly Highlights

- Built a multi-layer backend (API, services, AI, data, cache)
- Integrated multiple external systems (YouTube, Hugging Face, Ollama, Redis, Postgres)
- Implemented production-relevant patterns:
  - idempotent writes (`ON CONFLICT`)
  - caching strategy with TTL
  - migration-driven schema evolution
  - fallback behavior for AI inference failures

---

If you are evaluating this repository, this project demonstrates backend engineering, data pipeline thinking, and applied NLP/LLM integration in one cohesive system.
