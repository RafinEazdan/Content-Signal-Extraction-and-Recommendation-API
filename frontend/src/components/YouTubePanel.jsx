import { useState } from 'react'
import {
  fetchChannel,
  storeVideos,
  fetchMetrics,
  fetchComments,
  analyzeComments,
  getRecommendations,
} from '../api'

function Section({ title, children }) {
  return (
    <div className="yt-section">
      <h3 className="section-title">{title}</h3>
      {children}
    </div>
  )
}

function ResultBox({ data }) {
  if (!data) return null
  return (
    <pre className="result-box">{JSON.stringify(data, null, 2)}</pre>
  )
}

function useStep(token, apiFn) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  async function run(...args) {
    setError('')
    setLoading(true)
    try {
      const data = await apiFn(token, ...args)
      setResult(data)
      return data
    } catch (err) {
      setError(err.message)
      return null
    } finally {
      setLoading(false)
    }
  }

  return { loading, result, error, run }
}

export function YouTubePanel({ token }) {
  const [handle, setHandle] = useState('')
  const [channelDbId, setChannelDbId] = useState('')
  const [videoDbId, setVideoDbId] = useState('')

  const channel = useStep(token, fetchChannel)
  const videos = useStep(token, storeVideos)
  const metrics = useStep(token, fetchMetrics)
  const comments = useStep(token, fetchComments)
  const analysis = useStep(token, analyzeComments)
  const recs = useStep(token, getRecommendations)

  async function handleFetchChannel(e) {
    e.preventDefault()
    await channel.run(handle)
  }

  async function handleStoreVideos(e) {
    e.preventDefault()
    await videos.run(handle)
  }

  async function handleMetrics(e) {
    e.preventDefault()
    await metrics.run(channelDbId)
  }

  async function handleComments(e) {
    e.preventDefault()
    await comments.run(videoDbId)
  }

  async function handleAnalysis(e) {
    e.preventDefault()
    await analysis.run(videoDbId)
  }

  async function handleRecs(e) {
    e.preventDefault()
    await recs.run(videoDbId)
  }

  return (
    <div className="panel">
      {/* Step 1: Channel */}
      <Section title="1 — Fetch Channel">
        <form className="inline-form" onSubmit={handleFetchChannel}>
          <input
            type="text"
            placeholder="@channelHandle"
            value={handle}
            onChange={(e) => setHandle(e.target.value)}
            required
          />
          <button className="btn-primary" type="submit" disabled={channel.loading}>
            {channel.loading ? 'Fetching…' : 'Fetch'}
          </button>
        </form>
        {channel.error && <p className="error-msg">{channel.error}</p>}
        {channel.result && (
          <div className="result-card">
            <p><strong>{channel.result.channel_title}</strong> ({channel.result.channel_handle})</p>
            <p className="muted">Subscribers: {channel.result.subscriber_count?.toLocaleString()}</p>
            <p className="muted">Channel ID: {channel.result.channel_id}</p>
          </div>
        )}
      </Section>

      {/* Step 2: Store Videos */}
      <Section title="2 — Store Videos">
        <form className="inline-form" onSubmit={handleStoreVideos}>
          <input
            type="text"
            placeholder="@channelHandle"
            value={handle}
            onChange={(e) => setHandle(e.target.value)}
            required
          />
          <button className="btn-primary" type="submit" disabled={videos.loading || !handle}>
            {videos.loading ? 'Storing…' : 'Store Videos'}
          </button>
        </form>
        {videos.error && <p className="error-msg">{videos.error}</p>}
        {videos.result && (
          <div className="result-card">
            <p>{videos.result.newly_added_video_count} new video(s) stored.</p>
          </div>
        )}
      </Section>

      {/* Step 3: Metrics */}
      <Section title="3 — Fetch Metrics">
        <p className="muted hint">Requires the internal channel DB id (not the YouTube channel id).</p>
        <form className="inline-form" onSubmit={handleMetrics}>
          <input
            type="number"
            placeholder="channel_db_id"
            value={channelDbId}
            onChange={(e) => setChannelDbId(e.target.value)}
            required
          />
          <button className="btn-primary" type="submit" disabled={metrics.loading}>
            {metrics.loading ? 'Fetching…' : 'Get Metrics'}
          </button>
        </form>
        {metrics.error && <p className="error-msg">{metrics.error}</p>}
        {metrics.result && (
          <div>
            <p className="muted">{metrics.result.message}</p>
            {metrics.result.data?.length > 0 && (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Video ID</th>
                      <th>Date</th>
                      <th>Views</th>
                      <th>Likes</th>
                      <th>Comments</th>
                      <th>Engagement %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metrics.result.data.map((row, i) => (
                      <tr key={i}>
                        <td className="mono">{row.video_id}</td>
                        <td>{row.date}</td>
                        <td>{row.views?.toLocaleString()}</td>
                        <td>{row.likes?.toLocaleString()}</td>
                        <td>{row.comments_count?.toLocaleString()}</td>
                        <td>{row.engagement_rate?.toFixed(2)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </Section>

      {/* Steps 4–6: Per-video */}
      <Section title="4–6 — Per-video Operations">
        <p className="muted hint">Enter the internal video DB id to fetch comments, run sentiment analysis, and generate title recommendations.</p>
        <div className="inline-form" style={{ marginBottom: '1rem' }}>
          <input
            type="number"
            placeholder="video_db_id"
            value={videoDbId}
            onChange={(e) => setVideoDbId(e.target.value)}
          />
        </div>

        <div className="action-group">
          <div className="action-row">
            <span className="action-label">Fetch &amp; Store Comments</span>
            <button
              className="btn-sm"
              onClick={handleComments}
              disabled={comments.loading || !videoDbId}
            >
              {comments.loading ? '…' : 'Run'}
            </button>
          </div>
          {comments.error && <p className="error-msg">{comments.error}</p>}
          {comments.result && (
            <p className="result-inline">
              {comments.result.message} ({comments.result.comments?.length ?? 0} comments)
            </p>
          )}

          <div className="action-row">
            <span className="action-label">Analyze Comments</span>
            <button
              className="btn-sm"
              onClick={handleAnalysis}
              disabled={analysis.loading || !videoDbId}
            >
              {analysis.loading ? '…' : 'Run'}
            </button>
          </div>
          {analysis.error && <p className="error-msg">{analysis.error}</p>}
          {analysis.result && <ResultBox data={analysis.result} />}

          <div className="action-row">
            <span className="action-label">Generate Title Recommendations</span>
            <button
              className="btn-sm"
              onClick={handleRecs}
              disabled={recs.loading || !videoDbId}
            >
              {recs.loading ? '…' : 'Run'}
            </button>
          </div>
          {recs.error && <p className="error-msg">{recs.error}</p>}
          {recs.result?.titles?.length > 0 && (
            <ul className="titles-list">
              {recs.result.titles.map((t, i) => (
                <li key={i}>{t}</li>
              ))}
            </ul>
          )}
        </div>
      </Section>
    </div>
  )
}
