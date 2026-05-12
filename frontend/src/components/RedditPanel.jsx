import { useState } from 'react'
import { getRedditIdeas } from '../api'

export function RedditPanel() {
  const [mode, setMode] = useState('general')
  const [subredditInput, setSubredditInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const subreddits =
        mode === 'specific'
          ? subredditInput
              .split(',')
              .map((s) => s.trim())
              .filter(Boolean)
          : undefined
      const data = await getRedditIdeas(mode, subreddits)
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="panel">
      <div className="yt-section">
        <h3 className="section-title">Reddit Trending Ideas</h3>

        <form onSubmit={handleSubmit} className="form-stack" style={{ maxWidth: 480 }}>
          <div className="radio-group">
            <label>
              <input
                type="radio"
                value="general"
                checked={mode === 'general'}
                onChange={() => setMode('general')}
              />
              General
            </label>
            <label>
              <input
                type="radio"
                value="specific"
                checked={mode === 'specific'}
                onChange={() => setMode('specific')}
              />
              Specific subreddits
            </label>
          </div>

          {mode === 'specific' && (
            <input
              type="text"
              placeholder="e.g. programming, webdev, MachineLearning"
              value={subredditInput}
              onChange={(e) => setSubredditInput(e.target.value)}
              required
            />
          )}

          <button className="btn-primary" type="submit" disabled={loading}>
            {loading ? 'Fetching ideas…' : 'Get Ideas'}
          </button>
        </form>

        {error && <p className="error-msg">{error}</p>}

        {result && (
          <div style={{ marginTop: '1.5rem' }}>
            <div className="result-card" style={{ marginBottom: '1.5rem' }}>
              <p>
                <strong>{result.top_posts?.length ?? 0}</strong> trending posts ·{' '}
                <strong>{result.video_ideas?.length ?? 0}</strong> video ideas
                {result.subreddits?.length ? ` · r/${result.subreddits.join(', r/')}` : ''}
              </p>
            </div>

            {result.video_ideas?.length > 0 && (
              <div className="yt-section">
                <h4 className="section-title" style={{ fontSize: '0.8rem' }}>Video Ideas</h4>
                <ul className="titles-list">
                  {result.video_ideas.map((idea, i) => (
                    <li key={i}>{idea}</li>
                  ))}
                </ul>
              </div>
            )}

            {result.top_posts?.length > 0 && (
              <div className="yt-section">
                <h4 className="section-title" style={{ fontSize: '0.8rem' }}>Top Posts</h4>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Title</th>
                        <th>Subreddit</th>
                        <th>Upvotes</th>
                        <th>Comments</th>
                        <th>Trend Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.top_posts.map((post, i) => (
                        <tr key={i}>
                          <td>
                            {post.url ? (
                              <a href={post.url} target="_blank" rel="noreferrer">
                                {post.title}
                              </a>
                            ) : (
                              post.title
                            )}
                          </td>
                          <td className="mono">r/{post.subreddit}</td>
                          <td>{post.upvotes?.toLocaleString()}</td>
                          <td>{post.num_comments?.toLocaleString()}</td>
                          <td>{post.trend_score?.toFixed(1)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
