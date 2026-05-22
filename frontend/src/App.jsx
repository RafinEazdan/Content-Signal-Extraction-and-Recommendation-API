import { useState } from 'react'
import { Auth } from './components/Auth'
import { YouTubePanel } from './components/YouTubePanel'
import { RedditPanel } from './components/RedditPanel'
import { About } from './components/About'

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem('token') || '')
  const [tab, setTab] = useState('youtube')
  const [showAbout, setShowAbout] = useState(false)

  function handleLogin(t) {
    localStorage.setItem('token', t)
    setToken(t)
    setShowAbout(false)
  }

  function handleLogout() {
    localStorage.removeItem('token')
    setToken('')
  }

  if (showAbout) {
    return (
      <div className="app">
        <header className="topbar">
          <span className="logo">CERA</span>
          <nav className="nav-tabs">
            <button className="nav-tab active">About</button>
            {token && (
              <button className="nav-tab" onClick={() => setShowAbout(false)}>
                Dashboard
              </button>
            )}
            {!token && (
              <button className="nav-tab" onClick={() => setShowAbout(false)}>
                Login
              </button>
            )}
          </nav>
          {token && (
            <button className="btn-ghost logout" onClick={handleLogout}>
              Logout
            </button>
          )}
        </header>
        <main className="main-content about-main">
          <About />
        </main>
      </div>
    )
  }

  if (!token) {
    return <Auth onLogin={handleLogin} onAbout={() => setShowAbout(true)} />
  }

  return (
    <div className="app">
      <header className="topbar">
        <span className="logo">CERA</span>
        <nav className="nav-tabs">
          <button
            className={tab === 'youtube' ? 'nav-tab active' : 'nav-tab'}
            onClick={() => setTab('youtube')}
          >
            YouTube
          </button>
          <button
            className={tab === 'reddit' ? 'nav-tab active' : 'nav-tab'}
            onClick={() => setTab('reddit')}
          >
            Reddit
          </button>
          <button className="nav-tab" onClick={() => setShowAbout(true)}>
            About
          </button>
        </nav>
        <button className="btn-ghost logout" onClick={handleLogout}>
          Logout
        </button>
      </header>

      <main className="main-content">
        {tab === 'youtube' && <YouTubePanel token={token} />}
        {tab === 'reddit' && <RedditPanel />}
      </main>
    </div>
  )
}
