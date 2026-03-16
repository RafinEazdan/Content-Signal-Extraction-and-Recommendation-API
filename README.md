# Random Thought API - Detailed Project Status

This repository contains a FastAPI backend that currently implements:

- User signup with OTP verification stored in Redis
- JWT-based login and authenticated profile operations
- YouTube channel lookup, persistence, and Redis caching
- Channel video ingestion from YouTube playlist items
- Video metrics ingestion and daily upsert storage
- Video comment ingestion and persistence
- Alembic-driven schema evolution for all major domain tables

The goal of this document is to provide a very detailed description of what has already been built, how each part works, and how components are connected.

## 1. Tech Stack and Runtime

### Application and API
- FastAPI (`fastapi`)
- Uvicorn (`uvicorn`)
- Pydantic v2 (`pydantic`, `pydantic-settings`)

### Persistence and Migrations
- PostgreSQL via psycopg3 (`psycopg`, `psycopg-binary`)
- SQLAlchemy models for metadata and Alembic autogenerate support
- Alembic migrations for schema versioning

### Auth and Security
- JWT creation/verification (`PyJWT` package imported as `jwt`)
- Password hashing with Argon2 via Passlib

### Caching and Ephemeral State
- Redis async client (`redis.asyncio`)
- Redis used for OTP registration staging and channel-level cache

### External APIs
- YouTube Data API v3:
	- `search` endpoint for finding channels by handle/query
	- `channels` endpoint for channel metadata
	- `playlistItems` endpoint for recent videos from upload playlist
	- `videos` endpoint for view/like/comment counts
	- `commentThreads` endpoint for top-level comments

## 2. Repository Structure (Current)

- `app/main.py`: FastAPI app instance and router registration
- `app/api/v1/`: HTTP route modules (auth/users/channel/video/metric/comment)
- `app/services/`: business logic and third-party API orchestration
- `app/models/`: SQLAlchemy ORM table definitions
- `app/schemas/`: Pydantic request/response contracts
- `app/database/`: DB base metadata and connection dependency
- `app/redis/`: Redis client wrapper and dependency provider
- `app/core/`: settings loading and password utilities
- `alembic/`: migration environment and version scripts
- `requirements.txt`: pinned dependencies

## 3. Application Entry and Router Wiring

The app is created in `app/main.py` and includes these routers:

- `users.router`
- `auth.router`
- `channel.router`
- `video.router`
- `metric.router`
- `comment.router`

There is also a root endpoint:

- `GET /` -> returns `{"Hello": "World!"}`

## 4. Environment Variables and Config

The settings class in `app/core/config.py` expects these required values from `.env`:

- `YT_API_KEY`
- `DATABASE_URL`
- `SECRET_KEY`
- `POSTGRES_PASSWORD`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `ALGORITHM`
- `REDIS_URL`

Notes:

- Missing required keys will fail settings initialization.
- JWT expiration is configured by `ACCESS_TOKEN_EXPIRE_MINUTES`.
- YouTube integrations depend entirely on `YT_API_KEY` being valid.

## 5. Database and Redis Connectivity

### PostgreSQL dependency (`app/database/session.py`)

- `get_db()` continuously retries connection in a `while True` loop until success.
- Returns psycopg connection objects with `dict_row` row factory.
- Each request closes the connection in `finally`.

### Redis dependency (`app/redis/redis_client.py`, `app/redis/dependencies.py`)

- A singleton `RedisClient` is created.
- Async helper methods:
	- `get(key)`
	- `set(key, value, expire=None)`
	- `delete(key)`

Current Redis key usage:

- `reg:<email>` for staged signup + OTP payload
- `channel:<channel_handle>` for channel cache (7 days)

## 6. Authentication and Authorization

### Password handling (`app/core/security.py`)

- Hashing: Argon2 via `CryptContext`
- Verification: `verify_pass(given_pass, hashed_pass)`

### JWT flow (`app/services/oauth.py`)

- `create_token(data)`:
	- Copies payload
	- Adds `exp` claim using configured expiry minutes
	- Signs token using `SECRET_KEY` and `ALGORITHM`

- `verify_token(token, credential_exception)`:
	- Decodes token
	- Extracts `id`
	- Raises provided HTTP exception on invalid token or missing id

- `get_current_user(...)` dependency:
	- Reads bearer token via `OAuth2PasswordBearer(tokenUrl="login")`
	- Verifies token
	- Confirms user id exists in `users` table
	- Returns DB user dict with `id`

## 7. Endpoint Reference (All Current Routes)

This section lists all current endpoints with behavior and contracts as implemented.

### 7.1 Auth Endpoints

#### `POST /login`
Tag: `Login`

Purpose:

- Authenticate by email + password and issue JWT token.

Input:

- `OAuth2PasswordRequestForm`
	- `username` field is treated as email
	- `password` is plaintext password

Process:

- Query user by email from `users` table
- Verify password hash
- Build JWT with user id

Response (`Token` schema):

- `token`: JWT string
- `token_type`: `bearer`

Failure cases:

- `403 Invalid Credentials` for unknown email or wrong password

### 7.2 User Endpoints

Base prefix: `/users`
Tag: `Users`

#### `POST /users/signup/send-otp`

Purpose:

- Start registration process and place signup payload + OTP in Redis.

Input (`UserCreate`):

- `username: str`
- `email: EmailStr`
- `password: str`
- `profile_pic: str | None`

Process:

- Ensures email is not already registered in DB
- Hashes password
- Generates 6-digit OTP
- Stores staged payload in Redis key `reg:<email>` with expiry `500` seconds

Response:

- Status `200`
- Message indicating OTP sent

Failure cases:

- `409 Email already registered`
- `500` on DB or internal errors

#### `POST /users/signup/verify-otp`

Purpose:

- Verify OTP and complete user creation in PostgreSQL.

Input (`OTPVerifyRequest`):

- `email: EmailStr`
- `otp: str`

Process:

- Reads Redis `reg:<email>` payload
- Verifies provided OTP
- Inserts user into `users` table
- Deletes staged redis key after successful DB commit

Response (`UserResponse`):

- `username`
- `email`
- `id`
- `created_at`
- `profile_pic`

Failure cases:

- `400` on missing/expired registration or invalid OTP
- `500` on insert/transaction failure

#### `GET /users/profile`

Auth required: yes (`get_current_user`)

Purpose:

- Return current authenticated user profile.

Response (`UserResponse`):

- Full current user row mapped to schema

Failure cases:

- `401` if token missing/invalid
- `403` if user cannot be loaded

#### `DELETE /users/profile/delete`

Auth required: yes (`get_current_user`)

Purpose:

- Delete current authenticated user account.

Process:

- Executes delete by current user id
- Returns `204` no content on success

Failure cases:

- `403` if no row was deleted

### 7.3 Channel Endpoints

Base prefix: `/channels`
Tag: `Channels`

#### `POST /channels/`

Auth required: yes

Purpose:

- Fetch and persist channel metadata from cache/DB/API using channel handle.

Input (`ChannelRequest`):

- `channel_handle: str`

Resolution order in `fetch_create_channel`:

1. Redis cache: `channel:<channel_handle>`
2. PostgreSQL `channels` table
3. YouTube API fetch then DB insert then cache set

Response (`ChannelResponse`):

- `channel_id`
- `channel_title`
- `channel_handle`
- `subscriber_count`
- `upload_playlist`

Implementation details:

- Cache expiry is `604800` seconds (7 days)
- Inserted platform is fixed as `youtube`

### 7.4 Video Endpoints

Base prefix: `/videos`
Tag: `Videos`

#### `POST /videos/store`

Auth required: yes

Purpose:

- Pull latest videos from channel upload playlist and store new rows.

Input (`VideoRequest`):

- `channel_handle: str`

Process summary:

- Finds channel in DB by handle (`id`, `upload_playlist`)
- Calls YouTube `playlistItems` API
- Maps items into internal video objects
- Inserts into `videos` with `ON CONFLICT (video_id) DO NOTHING`

Response (`VideoResponse`):

- `newly_added_video_count: int`

Failure cases:

- `404` if channel does not exist in DB

Important current behavior:

- Current implementation fetches only one page of playlist results (`maxResults=20`).
- Pagination loop is present but not fully enabled for multiple pages.

### 7.5 Metrics Endpoints

Base prefix: `/metrics`
Tag: `metrics`

#### `POST /metrics/`

Auth required: yes

Purpose:

- Fetch per-video statistics for all videos in a channel and upsert daily metrics.

Input (`RequestMetrics`):

- `channel_db_id: int`

Process summary in `video_metrics.get_metrics`:

- Validate channel exists
- Select all videos for that channel
- Batch video ids in chunks of 50
- Call YouTube `videos` API (`part=statistics`)
- Compute engagement rate:

	$$\text{engagement\_rate} = \frac{likes + comments\_count}{views} \times 100$$

- Upsert into `video_metrics` by unique pair `(video_db_id, date)`

Response (`ResponseMetrics`):

- `success: bool`
- `message: str`
- `metrics_count: int`
- `data: List[VideoMetricResponse]`

`VideoMetricResponse` contains:

- `video_id`
- `date`
- `views`
- `likes`
- `comments_count`
- `engagement_rate`

Failure cases:

- `404` if channel id does not exist
- `500` on unexpected errors

### 7.6 Comment Endpoints

No explicit router prefix configured in this module.

#### `POST /fetch_comments`

Auth required: no (current implementation)

Purpose:

- Fetch top-level YouTube comments for a stored video and insert into DB.

Input (`RequestComment`):

- `video_db_id: int`

Process summary in `CommentService`:

- Resolve `video_id` from DB using `video_db_id`
- Iterate through YouTube `commentThreads` pages (`maxResults=100`)
- Build normalized comment objects
- Bulk insert with `executemany`
- `ON CONFLICT (comment_id) DO NOTHING`

Response (`ResponseComment`):

- `success: bool`
- `message: str`
- `comments: list`

Each comment item includes:

- `comment_id`
- `video_db_id`
- `author_name`
- `text`
- `published_at`

Failure cases:

- `404` if video id is not found
- `400` for YouTube API non-200 responses
- `500` for uncaught internal errors

## 8. Service Layer: Detailed Behavior

### `app/services/signup_service.py`

- `check_existing_user(email)`:
	- SQL check for existing user id
	- Raises `409` if found

- `send_otp(email, password, username, profilepic)`:
	- Hashes password
	- Delegates OTP generation/storage to `OTPService`

- `verify_user(email, otp)`:
	- Delegates OTP validation to `OTPService`

- `signup_user(email)`:
	- Loads staged registration JSON from Redis
	- Inserts user row in DB
	- Commits transaction and deletes Redis key
	- Returns profile-like dict

### `app/services/otp_service.py`

- Generates 6-digit OTP with `secrets.randbelow`
- Stores full staged registration payload under `reg:<email>`
- TTL currently set to `500` seconds
- Verifies OTP against stored value

Note:

- OTP is printed in server logs in current implementation (development behavior).

### `app/services/api_get_channel.py`

- Calls YouTube Search API to resolve channel id by query text
- Calls YouTube Channels API for details
- Extracts:
	- `channel_id`
	- `channel_title`
	- `subscriber_count`
	- `upload_playlist`

### `app/services/fetch_create_channel.py`

- Primary channel resolver and persistence entry point:
	- Check Redis cache first
	- Check DB second
	- Fetch from API if not found
- Writes successful channel records into DB and Redis

### `app/services/video_service.py`

- `_get_channel_db_id(channel_handle)`:
	- Loads channel db id + upload playlist by handle

- `get_video_list(channel_handle)`:
	- Fetches playlist items from YouTube
	- Transforms items into internal list shape

- `store_videos(channel_handle)`:
	- Gets mapped video list
	- Inserts into `videos` table with conflict ignore
	- Returns inserted count only

- `get_stored_videos(channel_db_id)`:
	- Utility method for reading persisted videos by channel

### `app/services/metrics_video.py`

- `_channel_exists(channel_db_id)` validation before processing
- `_fetch_youtube_metrics(video_ids)` uses YouTube `videos` statistics
- `_store_metrics(metrics_data, video_db_ids)` does daily upsert
- `_format_metrics_response(metrics_data)` rounds engagement rates

### `app/services/comment_service.py`

- `_get_video_id(video_db_id)` resolves YouTube video id from local DB
- `fetch_and_store_comment(video_db_id)`:
	- Fetches paginated comments
	- Assembles normalized list
	- Delegates DB insert
- `_store_comments(comments)`:
	- Bulk insert with conflict handling

## 9. Data Models (Current Table Definitions)

### `users`
- `id` (PK)
- `email` (unique, required)
- `username` (required)
- `hashed_password` (required)
- `created_at` (default `now()`)
- `profile_pic` (nullable)

### `channels`
- `id` (PK)
- `channel_id` (string identifier from YouTube)
- `platform` (nullable)
- `channel_title` (required)
- `channel_handle` (required)
- `subscriber_count` (nullable)
- `upload_playlist` (nullable)

### `videos`
- `id` (PK)
- `video_id` (unique, required)
- `video_title` (required)
- `video_description` (nullable)
- `published_at` (stored as string)
- `channel_id_url` (required)
- `channel_db_id` (FK -> `channels.id`, cascade delete)

### `video_metrics`
- `id` (PK)
- `video_db_id` (FK -> `videos.id`, cascade delete)
- `date` (required)
- `views` (required)
- `likes` (required)
- `comments_count` (required)
- `engagement_rate` (required)
- Unique constraint: `(video_db_id, date)`

### `comments`
- `id` (PK)
- `comment_id` (unique)
- `video_db_id` (currently stored column type differs between migration and ORM; see notes below)
- `published_at`
- `author_name`
- `like_count`
- `text`

## 10. Pydantic Schemas (API Contracts)

### User schemas (`app/schemas/users.py`)
- `UserCreate`
- `UserResponse`
- `OTPVerifyRequest`
- `Token`
- `TokenData`

### Channel schemas (`app/schemas/channels.py`)
- `ChannelRequest`
- `ChannelResponse`

### Video schemas (`app/schemas/videos.py`)
- `VideoRequest`
- `VideoBase`
- `VideoResponse`

### Metrics schemas (`app/schemas/metrics.py`)
- `RequestMetrics`
- `VideoMetricResponse`
- `ResponseMetrics`

### Comment schemas (`app/schemas/comments.py`)
- `RequestComment`
- `ResponseCommentBase`
- `ResponseComment`

## 11. Alembic Migration History (Detailed)

The migration chain currently progresses as follows:

1. `e2c66c670f65` - initial `users` table
2. `61b3dbb7a103` - create `channels` table with `user_id` FK and integer `channel_id`
3. `8d9869a4e289` - add `total_no_of_videos`, relax nullability on `platform` and `subscriber_count`
4. `be030eeebf1c` - replace `total_no_of_videos` with `upload_playlist`
5. `9e5461a4bb91` - add `channel_handle`
6. `590886e3adf7` - alter `channel_id` from integer to string and add unique constraint
7. `06c35223c7b7` - remove unique constraint on `channels.channel_id`
8. `3f9fba052403` - remove `channels.user_id` and its foreign key
9. `84a9cf7786db` - create `videos` table with FK to `channels`
10. `0028a87bbf03` - add unique constraint on `videos.video_id`
11. `aedf15b9381b` - create `video_metrics` table (initially unique on `video_db_id`)
12. `a99f95b335ce` - replace unique on `video_db_id` with composite unique on `(video_db_id, date)`
13. `6e0fc348cc91` - create `comments` table

Migration infrastructure details:

- `alembic/env.py` imports all model modules for metadata discovery.
- Runtime DB URL is injected from environment into Alembic config.

## 12. Current Functional Flow (End-to-End)

Typical working flow today:

1. Call signup send OTP endpoint.
2. Verify OTP and create user.
3. Login to obtain bearer token.
4. Add/fetch channel by handle (stored and cached).
5. Store videos for that channel.
6. Fetch metrics for that channel's local DB id.
7. Fetch comments for any stored video DB id.

## 13. Setup and Run Instructions

### 13.1 Install dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 13.2 Configure environment

Create `.env` with all required keys listed in section 4.

### 13.3 Run migrations

```bash
alembic upgrade head
```

### 13.4 Start API server

```bash
uvicorn app.main:app --reload
```

### 13.5 Open API docs

- Swagger UI: `http://127.0.0.1:8000/docs`

## 14. Known Gaps and Implementation Notes

These are important, currently visible implementation details that may impact production usage:

- Comment route currently has no auth dependency, unlike other data-fetching routes.
- OTP is currently printed to stdout for development visibility.
- `video_db_id` type in comments migration is `String`, while ORM model uses `Integer`.
- In JWT decode, algorithm argument is passed in a compact form and should be reviewed for strict PyJWT compatibility in all environments.
- Video ingestion currently fetches only first playlist page (up to 20 videos per call).
- Mixed sync/async HTTP usage exists (`requests` in one service, `httpx` elsewhere).

## 15. What Is Completed So Far (Summary)

Completed and working in codebase:

- Core API scaffold and router composition
- Credential login with JWT issuance
- OTP-backed signup flow with Redis staging
- Authenticated profile read/delete
- Channel fetch + persist + cache pipeline
- Video fetch + deduplicated storage pipeline
- Metrics fetch + daily upsert pipeline
- Comment fetch + deduplicated storage pipeline
- Full migration chain from initial users table to comments table

This README now reflects the implementation status currently present in the repository.
