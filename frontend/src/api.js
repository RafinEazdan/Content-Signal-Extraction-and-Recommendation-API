const BASE = 'http://localhost:8000'

function authHeaders(token) {
  return { Authorization: `Bearer ${token}` }
}

async function handleRes(res) {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      detail = body.detail || JSON.stringify(body)
    } catch {}
    throw new Error(detail)
  }
  return res.json()
}

// Auth
export async function login(email, password) {
  const body = new URLSearchParams({ username: email, password })
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
  return handleRes(res)
}

export async function sendOtp(email, password, username) {
  const res = await fetch(`${BASE}/auth/users/signup/send-otp`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, username }),
  })
  return handleRes(res)
}

export async function verifyOtp(email, otp) {
  const res = await fetch(`${BASE}/auth/users/signup/verify-otp`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, otp }),
  })
  return handleRes(res)
}

export async function getProfile(token) {
  const res = await fetch(`${BASE}/auth/users/profile`, {
    headers: authHeaders(token),
  })
  return handleRes(res)
}

// YouTube
export async function fetchChannel(token, channelHandle) {
  const res = await fetch(`${BASE}/youtube/channels/`, {
    method: 'POST',
    headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
    body: JSON.stringify({ channel_handle: channelHandle }),
  })
  return handleRes(res)
}

export async function storeVideos(token, channelHandle) {
  const res = await fetch(`${BASE}/youtube/videos/store`, {
    method: 'POST',
    headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
    body: JSON.stringify({ channel_handle: channelHandle }),
  })
  return handleRes(res)
}

export async function fetchMetrics(token, channelDbId) {
  const res = await fetch(`${BASE}/youtube/metrics/`, {
    method: 'POST',
    headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
    body: JSON.stringify({ channel_db_id: Number(channelDbId) }),
  })
  return handleRes(res)
}

export async function fetchComments(token, videoDbId) {
  const res = await fetch(`${BASE}/youtube/fetch-comments`, {
    method: 'POST',
    headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
    body: JSON.stringify({ video_db_id: Number(videoDbId) }),
  })
  return handleRes(res)
}

export async function analyzeComments(token, videoDbId) {
  const res = await fetch(`${BASE}/youtube/comment_analysis`, {
    method: 'POST',
    headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
    body: JSON.stringify({ video_db_id: Number(videoDbId) }),
  })
  return handleRes(res)
}

export async function getRecommendations(token, videoDbId, refresh = false) {
  const res = await fetch(`${BASE}/youtube/video_recommendation/comments`, {
    method: 'POST',
    headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
    body: JSON.stringify({ video_db_id: Number(videoDbId), refresh }),
  })
  return handleRes(res)
}

// Reddit
export async function getRedditIdeas(mode, subreddits) {
  const body = { mode }
  if (mode === 'specific' && subreddits?.length) body.subreddits = subreddits
  const res = await fetch(`${BASE}/reddit/ideas/reddit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return handleRes(res)
}
