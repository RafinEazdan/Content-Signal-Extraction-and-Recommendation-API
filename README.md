# Content Signal Extraction and Recommendation API

A FastAPI backend for collecting YouTube channel signals (videos, metrics, comments), analyzing audience sentiment/toxicity, and generating recommendation-ready content title ideas from comments.

## 1. What This Project Currently Does

Implemented end-to-end:

- OTP-based signup flow with Redis staging
- JWT login and authenticated profile endpoints
- Channel discovery by handle with Redis cache and DB persistence
- Video ingestion from channel upload playlist
- Daily metric snapshots with upsert semantics
- Comment ingestion with de-duplication
- AI comment analysis (sentiment + toxicity)
- Topic extraction from comments and LLM-generated suggested titles
- Alembic migration history for schema evolution

## 2. Tech Stack

### API and Runtime

- FastAPI
- Uvicorn
- Pydantic v2 / pydantic-settings

### Database and Migrations

- PostgreSQL via psycopg3
- SQLAlchemy models (metadata/migrations)
- Alembic

### Auth and Security

- JWT via PyJWT
- Password hashing with Argon2 (passlib)

### Caching / Ephemeral Storage

- Redis async client (`redis.asyncio`)

### AI / NLP

- Hugging Face Inference API (sentiment + toxicity)
- VADER fallback for sentiment
- Keyword fallback for toxicity
- Ollama (configurable model via `LLM_MODEL`) for title generation

### External API

- YouTube Data API v3 (`search`, `channels`, `playlistItems`, `videos`, `commentThreads`)

## 3. Project Structure

- `app/main.py`: FastAPI app and router registration
- `app/api/v1/`: API route modules
- `app/services/`: core business logic for auth/signup/channel/video/metrics/comments
- `app/ai/`: AI pipeline and topic/title generation logic
- `app/models/`: SQLAlchemy model definitions
- `app/schemas/`: request/response Pydantic contracts
- `app/database/`: DB base/session dependency
- `app/redis/`: Redis client and dependency wiring
- `app/core/`: settings and security utilities
- `alembic/`: migration environment and revisions
- `requirements.txt`: dependencies

## 4. App Entry and Router Wiring

Current routers included in `app/main.py`:

- `users.router`
- `auth.router`
- `channel.router`
- `video.router`
- `metric.router`
- `comment.router`
- `comment_analysis.router`
- `video_recommendation.router`

Root endpoint:

- `GET /` -> `{ "Hello": "World!" }`

## 5. Environment Variables

Required in `.env`:

- `YT_API_KEY`
- `DATABASE_URL`
- `SECRET_KEY`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `ALGORITHM`
- `REDIS_URL`
- `HF_API_KEY`
- `OLLAMA_BASE_URL`
- `LLM_MODEL`

Optional model overrides:

- `HF_SENTIMENT_MODEL` (default: `distilbert/distilbert-base-uncased-finetuned-sst-2-english`)
- `HF_TOXICITY_MODEL` (default: `martin-ha/toxic-comment-model`)

## 6. Connectivity and State

### PostgreSQL (`app/database/session.py`)

- Uses psycopg with `dict_row` row factory
- Request dependency yields a DB connection and closes it in `finally`
- Connection logic retries forever in a loop with 2-second sleep

### Redis (`app/redis/redis_client.py`)

- Singleton Redis client instance
- Methods: `get`, `set`, `delete`

Current Redis keys:

- `reg:<email>`: staged signup payload + OTP (TTL 500s)
- `channel:<channel_handle>`: cached channel data (TTL 604800s = 7 days)

## 7. Authentication Flow

### Password utilities

- Hash: Argon2 (`app/core/security.py`)
- Verify: passlib verify

### JWT (`app/services/oauth.py`)

- `create_token(data)`: adds expiry and signs token
- `verify_token(token, credential_exception)`: decodes and validates token
- `get_current_user`: resolves bearer token and validates user in DB

## 8. API Endpoints (Current)

### Auth

#### `POST /login`

- Auth: none
- Input: `OAuth2PasswordRequestForm`
  - `username` is treated as email
- Response: `Token`
  - `token`
  - `token_type` (`bearer`)
- Errors: `403` invalid credentials

### Users (`/users`)

#### `POST /users/signup/send-otp`

- Auth: none
- Input: `UserCreate`
- Behavior:
  - checks existing email in DB
  - hashes password
  - generates OTP and stores staged payload in Redis
- Response: message string
- Errors: `409`, `500`

#### `POST /users/signup/verify-otp`

- Auth: none
- Input: `OTPVerifyRequest`
- Behavior:
  - verifies OTP from Redis
  - inserts user into DB
  - removes Redis staged key
- Response: `UserResponse`
- Errors: `400`, `500`

#### `GET /users/profile`

- Auth: required
- Response: `UserResponse`
- Errors: `401`, `403`

#### `DELETE /users/profile/delete`

- Auth: required
- Response: `204 No Content`
- Errors: `403`

### Channels (`/channels`)

#### `POST /channels/`

- Auth: required
- Input: `ChannelRequest`
- Resolution order:
  1. Redis cache
  2. DB lookup
  3. YouTube API fetch + DB insert + Redis set
- Response: `ChannelResponse`

### Videos (`/videos`)

#### `POST /videos/store`

- Auth: required
- Input: `VideoRequest`
- Behavior:
  - finds channel upload playlist
  - fetches playlist items
  - inserts with `ON CONFLICT (video_id) DO NOTHING`
- Response: `VideoResponse`

Important behavior:

- Currently fetches one playlist page (`maxResults=20`); full pagination is not enabled.

### Metrics (`/metrics`)

#### `POST /metrics/`

- Auth: required
- Input: `RequestMetrics` (`channel_db_id`)
- Behavior:
  - validates channel
  - loads stored videos
  - batches YouTube API calls in chunks of 50 IDs
  - computes engagement rate:

$$
\text{engagement\_rate} = \frac{likes + comments\_count}{views} \times 100
$$

  - upserts by `(video_db_id, date)`
- Response: `ResponseMetrics`

### Comments

#### `POST /fetch-comments`

- Auth: required
- Input: `RequestComment` (`video_db_id`)
- Behavior:
  - resolves video ID from DB
  - pages through `commentThreads`
  - inserts with `ON CONFLICT (comment_id) DO NOTHING`
- Response: `ResponseComment`

### Comment Analysis

#### `POST /comment_analysis`

- Auth: required
- Input: `RequestCommentAnalysis` (`video_db_id`)
- Behavior:
  - fetches stored comments from DB
  - runs async sentiment + toxicity pipeline
- Response:
  - list of `{ comment_id, sentiment, sentiment_score, toxicity, toxicity_score }`

### Video Recommendation

#### `POST /video_recommendation/comments`

- Auth: required
- Input: `RequestTopicsFromComments` (`video_db_id`, `refresh`)
- Behavior:
  - if `refresh=false`, returns cached predictions from DB when available
  - else extracts topics from comments and asks Ollama to generate titles
  - stores generated titles in `predicted_titles`
- Response: `ResponseTopicsFromComments` (`titles`)

## 9. Service Layer Notes

### Signup and OTP

- OTP is 6 digits
- OTP staging data stored as JSON in Redis
- OTP is printed to stdout in current implementation (development visibility)

### Channel Fetch (`fetch_create_channel`)

- Caches by `channel:<handle>` for 7 days
- Writes platform as `youtube`

### Video Ingestion (`video_service`)

- Pulls upload playlist items
- Stores only new videos using conflict ignore
- Has `get_stored_videos` helper

### Metrics (`metrics_video`)

- Fetches and stores views/likes/comments_count
- Computes and rounds engagement rates for response

### Comment Service

- Fetch/store comments
- Analyze comments through AI pipeline
- Generate title recommendations from extracted topics

## 10. AI Pipeline Details

### Sentiment (`app/ai/sentiment.py`)

- Uses HF Inference API async calls
- Attempts modern router endpoint then legacy endpoint
- Falls back to VADER if remote call fails

### Toxicity (`app/ai/toxicity.py`)

- Uses HF Inference API async calls
- Multiple endpoint/model fallback strategy
- Falls back to keyword heuristic if remote call fails

### Topic Extraction + Title Generation (`app/ai/comment_topic_extractor.py`)

- Topic candidates from regex intent patterns + n-grams
- Ranking uses frequency, likes, topic length, and intent score
- Title generation via Ollama chat endpoint (`{OLLAMA_BASE_URL}/api/chat`) with model from `LLM_MODEL`

## 11. Data Models (Current)

### `users`

- `id` (PK)
- `email` (unique)
- `username`
- `hashed_password`
- `created_at`
- `profile_pic` (nullable)

### `channels`

- `id` (PK)
- `channel_id` (unique)
- `platform`
- `channel_title`
- `channel_handle` (unique)
- `subscriber_count` (nullable)
- `upload_playlist` (nullable)

### `videos`

- `id` (PK)
- `video_id` (unique)
- `video_title`
- `video_description` (nullable)
- `published_at`
- `channel_id_url`
- `channel_db_id` (FK -> `channels.id`, cascade delete)

### `video_metrics`

- `id` (PK)
- `video_db_id` (FK -> `videos.id`, cascade delete)
- `date`
- `views`
- `likes`
- `comments_count`
- `engagement_rate`
- Unique: `(video_db_id, date)`

### `comments`

- `id` (PK)
- `comment_id` (unique)
- `video_db_id` (FK -> `videos.id`, cascade delete)
- `published_at`
- `author_name`
- `like_count`
- `text`

### `predicted_titles`

- `id` (PK)
- `video_db_id` (FK -> `videos.id`, cascade delete)
- `predicted_title`
- `score`
- `created_at`

## 12. Schemas (Current)

- `app/schemas/users.py`: `UserCreate`, `UserResponse`, `OTPVerifyRequest`, `Token`, `TokenData`
- `app/schemas/channels.py`: `ChannelRequest`, `ChannelResponse`
- `app/schemas/videos.py`: `VideoRequest`, `VideoResponse`
- `app/schemas/comments.py`: `RequestComment`, `ResponseCommentBase`, `ResponseComment`
- `app/schemas/metrics.py`: `RequestMetrics`, `VideoMetricResponse`, `ResponseMetrics`
- `app/schemas/comment_analysis.py`: `RequestCommentAnalysis`
- `app/schemas/video_recommendation.py`: `RequestTopicsFromComments`, `ResponseTopicsFromComments`

## 13. Alembic Migration Chain

Current linear chain by `down_revision`:

1. `e2c66c670f65_initial_schema.py`
2. `61b3dbb7a103_create_channels_table.py`
3. `8d9869a4e289_update_channels_table.py`
4. `be030eeebf1c_changing_a_column_in_channels_table.py`
5. `9e5461a4bb91_adding_channel_handle_in_channels_table.py`
6. `590886e3adf7_changing_the_type_of_channel_id.py`
7. `06c35223c7b7_changing_the_type_of_channel_id.py`
8. `3f9fba052403_removing_user_id_from_channel_table.py`
9. `84a9cf7786db_add_video_table.py`
10. `0028a87bbf03_add_unique_video_ids.py`
11. `aedf15b9381b_adding_video_metrics_table.py`
12. `a99f95b335ce_fix_video_metrics_unique_constraint.py`
13. `6e0fc348cc91_add_comments_table.py`
14. `d0fcf7ec10b5_adding_predicted_titles_table_and_.py`
15. `035c5e921f7f_video_db_id_as_foreign_keys.py`

Note:

- Comments `video_db_id` started as `String` in comments migration and was later cast to `INTEGER` in migration updates.

## 14. Setup and Run

### 1. Install dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

Create `.env` with required keys from section 5.

### 3. Run migrations

```bash
alembic upgrade head
```

### 4. Start server

```bash
uvicorn app.main:app --reload
```

### 5. Open docs

- Swagger UI: `http://127.0.0.1:8000/docs`

## 15. Docker

Prebuilt Docker image is available on Docker Hub:

- `eazdanrafin/content-signal-extraction-and-recommendation-api`

### Pull and run from Docker Hub

```bash
docker pull eazdanrafin/content-signal-extraction-and-recommendation-api:latest
docker run --rm -p 8000:8000 --env-file .env eazdanrafin/content-signal-extraction-and-recommendation-api:latest
```

### Build locally

```bash
docker build -t eazdanrafin/content-signal-extraction-and-recommendation-api:latest .
docker run --rm -p 8000:8000 --env-file .env eazdanrafin/content-signal-extraction-and-recommendation-api:latest
```

### Docker Compose (if using `docker-compose.yml`)

```bash
docker compose up --build
```

## 16. Known Gaps / Current Caveats

- OTP value is printed in logs (development behavior).
- DB connection dependency retries forever if DB is unavailable.
- Video ingestion currently fetches only one playlist page (20 videos).
- Mixed HTTP clients are used across modules (`requests`, `httpx`, `aiohttp`).
- Title generation requires reachable Ollama service at `OLLAMA_BASE_URL`.

## 17. Status Summary

Implemented and working in repository:

- API scaffolding and router composition
- OTP signup + JWT login flows
- Channel fetch/persist/cache pipeline
- Video ingestion pipeline (first page)
- Daily metric ingestion/upsert pipeline
- Comment ingestion/de-duplication pipeline
- AI comment analysis (sentiment + toxicity)
- Topic extraction + generated recommendation titles
- Alembic migration-backed schema history

---

This README was fully refreshed against the current repository implementation and renamed to: **Content Signal Extraction and Recommendation API**.
