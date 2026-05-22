export function About() {
  return (
    <div className="about-page">

      <div className="about-hero">
        <div className="about-logo">CERA</div>
        <p className="about-tagline">Content Signal Extraction and Recommendation API</p>
      </div>

      <section className="about-section">
        <p className="about-body">
          Most YouTube analytics tools tell you what already happened — views, likes, watch time. CERA
          goes one step further: it reads your comments, figures out what topics your audience keeps
          returning to, and asks an AI to suggest titles you haven't written yet.
        </p>
        <p className="about-body">
          The Reddit side does something different. It watches what's trending in whatever communities
          you care about, ranks posts by engagement, and turns each one into a concrete video idea. You
          tell it which subreddits to watch — or nothing at all and it scans broadly — and it hands you
          ten ranked ideas with a trend score attached to each.
        </p>
        <p className="about-body">
          CERA doesn't manage your channel or post anything on your behalf. It reads, analyzes, and
          recommends. What you do with that is your call.
        </p>
      </section>

      <section className="about-section">
        <h2 className="about-section-title">YouTube — how it works</h2>

        <p className="about-body about-body--lead">
          There are six steps, and they run in order. Each one depends on the previous.
        </p>

        <div className="how-steps">

          <div className="how-step">
            <div className="step-num">1</div>
            <div className="step-body">
              <h3>Fetch the channel</h3>
              <p>
                Enter a channel handle — the <code>@username</code> format YouTube uses — and hit
                Fetch. CERA calls the YouTube API, stores the channel in its database, and returns
                the channel title, subscriber count, and internal channel ID. The first fetch for
                any handle hits the YouTube API directly; repeat fetches within seven days return
                the cached result.
              </p>
            </div>
          </div>

          <div className="how-step">
            <div className="step-num">2</div>
            <div className="step-body">
              <h3>Store videos</h3>
              <p>
                Enter the same channel handle and click Store Videos. CERA pulls the channel's
                upload playlist and stores up to 20 videos — one page of results. Videos already
                in the database are skipped. The response tells you how many were newly added.
              </p>
              <p className="about-caveat">
                The 20-video limit is a known constraint. Only the most recent 20 uploads are
                ingested per call.
              </p>
            </div>
          </div>

          <div className="how-step">
            <div className="step-num">3</div>
            <div className="step-body">
              <h3>Fetch metrics</h3>
              <p>
                This step takes the channel's internal database ID — not the YouTube channel ID.
                After step 1, the channel ID shown in the result card is the YouTube one
                (<code>UCxxxx...</code>). The internal DB ID is the integer assigned when the
                channel was first stored; check your database or API response directly if you need
                it. Enter that integer and CERA fetches current views, likes, comment count, and
                computes an engagement rate — <code>(likes + comments) / views × 100</code> — for
                every stored video, displayed as a table.
              </p>
            </div>
          </div>

          <div className="how-step">
            <div className="step-num">4</div>
            <div className="step-body">
              <h3>Fetch and store comments</h3>
              <p>
                Enter a video's internal DB ID and run this step. CERA pages through the YouTube
                comments API and stores every comment thread it finds, de-duplicating on comment ID
                so re-runs don't create duplicates. The response tells you how many comments were
                retrieved.
              </p>
            </div>
          </div>

          <div className="how-step">
            <div className="step-num">5</div>
            <div className="step-body">
              <h3>Analyze comments</h3>
              <p>
                With comments stored, run analysis on the same video DB ID. CERA sends each comment
                through a sentiment model and a toxicity classifier — both running via the
                Hugging Face Inference API — and falls back to VADER and keyword matching when the
                remote API is unavailable. The result shows sentiment and toxicity scores for each
                comment.
              </p>
            </div>
          </div>

          <div className="how-step">
            <div className="step-num">6</div>
            <div className="step-body">
              <h3>Generate title recommendations</h3>
              <p>
                The last step. CERA extracts recurring topics from the stored comments, then passes
                those topics to the LLM and asks it to generate alternative video titles. The
                titles are cached against the video ID, so re-running this step returns the stored
                results rather than calling the LLM again.
              </p>
              <p className="about-caveat">
                Title quality depends directly on the LLM model configured at deploy time. The
                default is <code>tinyllama</code>, which is small and fast but not especially
                creative. Switching to a larger model will produce noticeably better results.
              </p>
            </div>
          </div>

        </div>
      </section>

      <section className="about-section">
        <h2 className="about-section-title">Reddit — how it works</h2>

        <p className="about-body">
          The Reddit tab has one operation with two modes.
        </p>

        <div className="reddit-modes">
          <div className="reddit-mode">
            <div className="mode-label">General</div>
            <p>
              No input required. CERA fetches trending posts from a broad set of communities, ranks
              them by <code>upvotes + 0.5 × comment count</code>, and returns the top 10. Each post
              comes with its trend score and one AI-generated YouTube video idea.
            </p>
          </div>
          <div className="reddit-mode">
            <div className="mode-label">Specific</div>
            <p>
              Enter between one and three subreddit names. CERA fetches each concurrently, merges
              the results, and applies the same ranking. Use this when you already know which
              communities your audience overlaps with.
            </p>
          </div>
        </div>

        <p className="about-body">
          Results are cached for one hour in Redis. If you run the same query twice within that
          window, the second call returns the cached results without hitting the Reddit API.
          After two hours, the database copy is also considered stale and the next call goes
          back to the source.
        </p>
      </section>

      <section className="about-section">
        <h2 className="about-section-title">A few things to know before you start</h2>

        <ul className="about-caveats-list">
          <li>
            <strong>Sign-up sends an OTP to stdout, not to your email.</strong> When you create an
            account, the six-digit code is printed to the authentication service's terminal output.
            If you're running this locally with Docker, check the container logs for the{' '}
            <code>authentication</code> service.
          </li>
          <li>
            <strong>Internal DB IDs aren't surfaced in the UI yet.</strong> Steps 3 through 6 ask
            for the internal integer ID assigned by the database — not the YouTube-facing ID. For
            now, you'll need to query the database directly or read the API response from{' '}
            <code>/channels/</code> and <code>/videos/store</code> to find those IDs.
          </li>
          <li>
            <strong>Video ingestion is capped at 20 per call.</strong> Only one page of the upload
            playlist is fetched. For channels with large back catalogues, this means only the most
            recent 20 uploads are available for analysis.
          </li>
          <li>
            <strong>Comment analysis calls external APIs.</strong> Sentiment and toxicity scoring
            goes through Hugging Face's Inference API. If that service is unavailable or your API
            key is missing, CERA falls back to VADER — a rule-based sentiment library — and keyword
            matching for toxicity. The fallback results are less accurate but always available.
          </li>
        </ul>
      </section>

      <footer className="about-footer">
        <span>CERA — Content Signal Extraction and Recommendation API</span>
      </footer>

    </div>
  )
}
