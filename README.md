# CERA: Content Signal Extraction and Recommendation API

CERA turns YouTube comments and trending Reddit posts into ranked video title recommendations. The system is split into five FastAPI services that run as independent processes, share a single Postgres database and Redis instance, and route through one gateway. A React frontend sits on top.

The interesting part is not the routing. It's the scoring. Two recommendation pipelines run inside the system, one for each data source, and both end in a Gemini call that converts ranked signal into copy a creator can actually use. The full formulas are documented later in this file.

## Quick Start

The fastest path is Docker. From the repo root:

```bash
docker compose up --build
```

That command brings up everything: the frontend on port 3000, the gateway on 8000, the four backend services on 8001-8004, Postgres 15 on 5433, Redis 7-alpine on 6379, and Ollama on 11434 (kept for local fallback use, see the LLM section).

Before the first run, copy each service's `.env.example` to `.env` and fill in five keys.

| Variable | File | What it's for |
|---|---|---|
| `YT_API_KEY` | `youtube/.env` | YouTube Data API v3 |
| `HF_API_KEY` | `youtube/.env` | Hugging Face Inference (sentiment, toxicity) |
| `GEMINI_API_KEY` | `llm/.env` | Google Gemini for title generation |
| `RAPIDAPI_KEY` | `reddit/.env` | `reddit34.p.rapidapi.com` |
| `SECRET_KEY` | `authentication/.env`, `youtube/.env` | JWT signing |

Postgres and Redis credentials, JWT expiration, and the Gemini model name are also read from these files. Defaults that work for local development are already in the `.env.example` files.

Once the containers are healthy, open `http://localhost:3000`. Sign up, copy the OTP printed in the auth service logs (it's also returned in the API response in dev mode), verify, log in, then paste a YouTube channel handle to start ingestion. Or hit the Reddit tab and pull trending ideas without authentication.

If you'd rather skip Docker, every service has its own `requirements.txt`. Standard pattern in each directory:

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head      # only for youtube/ and reddit/
uvicorn app.main:app --port <port> --reload
```

Postgres, Redis, and the LLM service still need to be running. Start the gateway last so its upstream resolution finds the others.

## Service Map

```
Client (http://localhost:3000)
   │
   ▼
api-gateway       :8000     path-prefix routing
   ├── /auth       →  authentication  :8001
   ├── /youtube    →  youtube         :8003
   ├── /reddit     →  reddit          :8002
   └── /llm        →  llm             :8004
                                       │
                                       ▼
                              Google Gemini API
```

All four backend services connect to the same Postgres 15 and Redis 7. The gateway holds no state. It's a single `httpx.AsyncClient` that strips hop-by-hop headers, forwards the body unchanged, and streams the upstream response back.

| Service | Port | Stack | Owns |
|---|---|---|---|
| Frontend | 3000 | React 18, Vite, Nginx | UI, auth flow, dashboard |
| API Gateway | 8000 | FastAPI, httpx | Routing, CORS, header hygiene |
| Authentication | 8001 | FastAPI, SQLAlchemy, psycopg | Users, OTP, JWT |
| Reddit | 8002 | FastAPI, SQLAlchemy, httpx | Trending posts, idea generation |
| YouTube | 8003 | FastAPI, psycopg, Alembic | Channels, videos, metrics, comments, AI analysis, title recommendations |
| LLM | 8004 | FastAPI, google-genai | Gemini wrapper |

## The Recommendation Formulas

This is the core of the project. Two pipelines, two scoring formulas, one shared generative step at the end.

### YouTube: Comment-Driven Title Recommendations

The YouTube recommender does not guess what a creator should make next from view counts. It reads the comments and finds out what the audience is asking for. The pipeline lives in [comment_topic_extractor.py](youtube/app/ai/comment_topic_extractor.py) and runs in five passes.

**Pass one: intent extraction by regex.** Three patterns look for comments that explicitly ask for content. The patterns target verbs like `make`, `create`, `upload`, `explain`, `cover`, `discuss`, the polite forms (`can you`, `could you`, `would you`), and tutorial requests (`how to`, `how do I`, `tutorial on`). Each pattern uses `finditer` rather than a single match, so a comment like "make a video on X and also cover Y" yields both X and Y. Topics shorter than three characters get dropped. Conjunctions and punctuation are trimmed before the topic is normalised. Intent matches count as the highest-quality signal and earn an `intent_bonus` later.

**Pass two: n-gram extraction.** Every comment also produces bigrams and trigrams, with stopwords (`the`, `a`, `an`, `is`, `it`, `to`, `of`, `in`, `on`, `for`, `i`, `you`, `me`) and tokens shorter than three characters removed. A small blocklist of generic phrases (`this video`, `this channel`, `great video`, `love this`, `good job`, `thank you`, `keep up`) drops the kind of n-grams that show up on every video and tell you nothing.

**Pass three: topic merging by substring containment.** Once topics are collected across all comments, the merger sorts them longest-first and walks the list looking for shorter topics that appear as substrings of longer ones. When it finds one, it folds the shorter topic's count, total likes, and intent count into the longer one. The longer topic is treated as canonical because it's more specific. "Python testing" survives and absorbs "python", not the other way round.

**Pass four: the score.** Every surviving topic gets a single floating-point score from this formula:

```
score = (count * 0.5)
      + (log(total_likes + 1) * 0.2)
      + (length_bonus       * 0.1)
      + (intent_bonus       * 0.2)
```

Each term is doing specific work.

The `count` term carries half the weight on purpose. The number of distinct comments that mentioned a topic is the strongest signal of audience interest, and nothing should outweigh it without good reason.

The `log(total_likes + 1)` term rewards topics raised in comments the audience itself upvoted. The logarithm matters. A comment with 500 likes is louder than a comment with 5, but it shouldn't be a hundred times louder. Log compression keeps a single viral comment from drowning out the steady volume of organic agreement underneath it. The `+1` keeps the math defined for topics with zero likes.

The `length_bonus` is `min(words / 3, 1.0)`. A three-word topic gets the full bonus. A one-word topic gets a third of it. The idea is that longer phrases tend to be more specific, and specificity is what makes a title differentiated. The cap at 1.0 prevents the bonus from running away when someone writes a paragraph.

The `intent_bonus` is `min(intent_count, 1.0)`, capped at one. Either the topic was raised by someone explicitly asking for content, or it wasn't. The bonus exists, but it doesn't get to compound. One explicit request and one implicit n-gram match should be ranked above two implicit n-gram matches, but ten explicit requests shouldn't trample everything else: the count term is already counting them.

**Pass five: rank and truncate.** Sort by score, take the top ten, hand the list to the LLM.

The LLM call goes through the gateway-style internal service at `llm:8004` and uses Gemini under the hood. The prompt asks for one click-worthy title per topic, under 70 characters, SEO-friendly, returned as a numbered list. The titles are parsed, persisted in `predicted_titles` against `video_db_id` with a `score` column that records rank position, and returned to the caller. A `refresh=false` flag on the endpoint short-circuits to the cached results in `predicted_titles`; `refresh=true` re-runs the whole pipeline.

### Reddit: Trend-Driven Video Ideas

The Reddit recommender is simpler by design. Reddit already does the heavy lifting on which posts the audience cares about. The job is to rank what's already there and convert it into a video pitch.

The trend score is one line, found in [reddit_service.py](reddit/app/services/reddit_service.py):

```
trend_score = upvotes + 0.5 * num_comments
```

Upvotes are the primary signal of community endorsement. Comments are the secondary signal of community engagement. A post that's been debated heavily is interesting even if its upvote count is moderate, but the debate shouldn't be valued at parity with the endorsement. The 0.5 multiplier is the trade. Half a vote of credit per comment.

After scoring, the service sorts descending, slices to the top ten, and sends those posts to the LLM with a prompt that asks for one YouTube idea per post, under 100 characters, educational or entertaining, matching the post order. The response is parsed and returned alongside the top posts.

### Three-Tier Caching Behind the Reddit Pipeline

The Reddit data pipeline runs through three tiers before it ever hits RapidAPI.

Tier one is Redis with a one-hour TTL, keyed by mode and (for specific mode) the sorted lowercased subreddit list. A cache hit returns immediately.

Tier two is Postgres with a two-hour freshness window. If Redis misses but the database has rows for this cache key fetched in the last two hours, the service rehydrates Redis from the database and returns. The two-hour window is longer than the Redis TTL by design: it gives the database a chance to absorb the next Redis miss after Redis expires, instead of forcing every Redis miss into an external API call.

Tier three is RapidAPI's `reddit34.p.rapidapi.com`. Only requests that miss both Redis and the freshness window reach the external API. Specific mode (with one to three subreddits) fans out concurrently with `asyncio.gather` and merges the results before ranking.

## Service Details

### Authentication (port 8001)

Owns the `users` table. Three flows: signup with OTP verification, login, and profile management.

Signup is two endpoints. `POST /users/signup/send-otp` hashes the password with bcrypt, generates a six-digit OTP with `secrets.randbelow(1000000)`, stages the registration payload in Redis under `reg:<email>` with a 500-second TTL, and returns. The OTP is printed to stdout and returned in the response body under `dev_otp`. This is **development mode behaviour**: the OTP is currently exposed to the frontend and printed to logs because email delivery isn't wired up yet. Treat it as a known-dev affordance and don't ship it as is.

`POST /users/signup/verify-otp` checks the OTP against the Redis entry, inserts the user row, and clears the Redis key.

The login endpoint is standard FastAPI: `POST /login` takes an `OAuth2PasswordRequestForm` and returns `{ token, token_type }`. Profile endpoints `GET /users/profile` and `DELETE /users/profile/delete` are JWT-gated.

### YouTube (port 8003)

The largest service by surface area. Migrations run automatically on container start: `alembic upgrade head` then `uvicorn`.

Endpoints:

- `POST /channels/` looks up a YouTube channel by handle through a three-tier cache: Redis (7-day TTL), then Postgres, then the YouTube Data API. Resolved channels are persisted with their `upload_playlist` ID, which is what the video ingester needs.
- `POST /videos/store` pulls the first page of the channel's upload playlist (20 videos), bulk-inserts with `ON CONFLICT (video_id) DO NOTHING`, and returns the new-row count.
- `POST /metrics/` fetches statistics for every stored video on a channel. The YouTube API allows 50 IDs per request, so the service batches in chunks of 50, then upserts each row by `(video_db_id, date)`. Engagement rate is computed as `(likes + comments) / views * 100`, rounded to two decimal places.
- `POST /fetch-comments` walks the `commentThreads` endpoint with pagination, deduplicates on `comment_id`, and stores the result.
- `POST /comment_analysis` runs sentiment and toxicity analysis concurrently with `asyncio.gather`. Sentiment uses Hugging Face's inference API against `distilbert/distilbert-base-uncased-finetuned-sst-2-english` by default, with VADER as a local fallback when the API is unreachable. Toxicity uses `martin-ha/toxic-comment-model` with `unitary/toxic-bert` as a fallback model and a keyword list as the final safety net. Both models can be overridden through `HF_SENTIMENT_MODEL` and `HF_TOXICITY_MODEL` environment variables.
- `POST /video_recommendation/comments` runs the comment-driven title pipeline described above.

Every endpoint except the root is JWT-gated via `get_current_user`.

### Reddit (port 8002)

One endpoint, but it does a lot. `POST /ideas/reddit` accepts a body of `{ mode, subreddits? }`. Mode `general` pulls Reddit's top popular posts for the week. Mode `specific` requires one to three subreddits and fetches each concurrently.

Either way, the service runs the trend score, picks the top ten, calls the LLM service for one video idea per post, and returns the posts and ideas together. Migrations run on container start. Reddit tracks its Alembic history in a separate `alembic_version_reddit` table so it never collides with YouTube's.

### LLM (port 8004)

The service is small on purpose. It exists so that the YouTube and Reddit services don't both have to know how to talk to Gemini.

`POST /generate` accepts `{ prompt: string, system?: string }` and returns `{ text: string }`. The default implementation calls Google Gemini through the `google-genai` SDK. An Ollama-backed implementation is also present in the codebase ([ollama_service.py](llm/app/services/ollama_service.py)) and can be swapped in by changing the import in [generate.py](llm/app/api/v1/generate.py). The Ollama path expects `OLLAMA_BASE_URL` and `LLM_MODEL` in the env; the docker-compose Ollama service ships with `tinyllama` available.

`GET /health` is a liveness probe.

### API Gateway (port 8000)

Path-prefix routing with longer prefixes evaluated first, so `/youtube` matches before `/yt` would. The mapping lives in `ROUTE_MAP` in [config.py](api-gateway/app/core/config.py). The gateway strips a fixed list of hop-by-hop headers (`connection`, `keep-alive`, `proxy-authenticate`, `proxy-authorization`, `te`, `trailers`, `transfer-encoding`, `upgrade`, `host`) and forwards everything else. JWT verification happens inside the upstream services, not at the gateway.

CORS is open to `http://localhost:3000` for development.

### Frontend (port 3000)

React 18 with Vite, served by Nginx in the production container. The component tree is small: an auth screen, a YouTube dashboard panel, a Reddit ideas panel, and an About page. All API calls go through a single `api.js` module that points at `http://localhost:8000` and attaches the JWT to authenticated requests.

The Reddit panel does not require authentication. Anyone hitting the frontend can pull trending ideas. The YouTube panel walks the user through the full pipeline: paste a channel handle, fetch the channel, store videos, fetch metrics, pull comments, analyse them, and request title recommendations.

## Data Models

**Authentication**

| Table | Columns |
|---|---|
| `users` | `id`, `email` (unique), `username`, `hashed_password`, `created_at`, `profile_pic` |

**YouTube**

| Table | Columns |
|---|---|
| `channels` | `id`, `channel_id` (unique), `platform`, `channel_title`, `channel_handle` (unique), `subscriber_count`, `upload_playlist` |
| `videos` | `id`, `video_id` (unique), `video_title`, `video_description`, `published_at`, `channel_id_url`, `channel_db_id` (FK, cascade) |
| `video_metrics` | `id`, `video_db_id` (FK, cascade), `date`, `views`, `likes`, `comments_count`, `engagement_rate`; unique on `(video_db_id, date)` |
| `comments` | `id`, `comment_id` (unique), `video_db_id` (FK, cascade), `published_at`, `author_name`, `like_count`, `text` |
| `predicted_titles` | `id`, `video_db_id` (FK, cascade), `predicted_title`, `score`, `created_at` |

**Reddit**

| Table | Columns |
|---|---|
| `reddit_trending_posts` | `id`, `post_id`, `title`, `subreddit`, `upvotes`, `num_comments`, `trend_score`, `url`, `cache_key`, `mode`, `fetched_at`; indexed on `cache_key`, `fetched_at` |

## Environment Variables

Every service reads its own `.env`. There is no shared file.

`authentication/.env`

```
DATABASE_URL
SECRET_KEY
ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES
REDIS_URL
POSTGRES_PASSWORD
POSTGRES_DB
```

`youtube/.env` (also read by the `postgres` container in compose)

```
DATABASE_URL
SECRET_KEY
ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES
REDIS_URL
YT_API_KEY
HF_API_KEY
LLM_SERVICE_URL
POSTGRES_PASSWORD
POSTGRES_DB
HF_SENTIMENT_MODEL  (optional; default distilbert/distilbert-base-uncased-finetuned-sst-2-english)
HF_TOXICITY_MODEL   (optional; default martin-ha/toxic-comment-model)
```

`reddit/.env`

```
DATABASE_URL
REDIS_URL
RAPIDAPI_KEY
LLM_SERVICE_URL
POSTGRES_PASSWORD
POSTGRES_DB
```

`llm/.env`

```
OLLAMA_BASE_URL
LLM_MODEL
GEMINI_API_KEY
GEMINI_MODEL
```

`api-gateway/.env`

```
AUTH_SERVICE_URL
YOUTUBE_SERVICE_URL
REDDIT_SERVICE_URL
LLM_SERVICE_URL
```

## Service URLs

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API Gateway | http://localhost:8000 |
| Authentication | http://localhost:8001 |
| Reddit | http://localhost:8002 |
| YouTube | http://localhost:8003 |
| LLM | http://localhost:8004 |
| Ollama (local) | http://localhost:11434 |

Swagger UI is at `/docs` on each backend service. The gateway proxies these too, so you can reach them through `http://localhost:8000/<prefix>/docs`.

## Migrating From an Older Schema

If the database previously ran an earlier consolidated version of the schema, the `alembic_version` table will hold a revision the current YouTube migrations don't recognise. Stamp it with the current head before upgrading:

```bash
cd youtube
python -c "
from dotenv import load_dotenv; import os, psycopg; load_dotenv()
conn = psycopg.connect(os.getenv('DATABASE_URL'))
conn.cursor().execute(\"UPDATE alembic_version SET version_num = '035c5e921f7f'\")
conn.commit(); conn.close()
"
alembic upgrade head
```

Reddit's migrations live in `alembic_version_reddit`, so they upgrade independently and never collide with YouTube's history.

## Notes

The OTP flow is currently in development mode: the six-digit code is printed to stdout and returned in the signup response under `dev_otp`, so it's reachable from the frontend without an email provider. Wiring up real email delivery is a single replacement of the OTP service's print statement and the response shape.
