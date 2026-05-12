import { useState } from 'react'
import { Auth } from './components/Auth'
import { YouTubePanel } from './components/YouTubePanel'
import { RedditPanel } from './components/RedditPanel'

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem('token') || '')
  const [tab, setTab] = useState('youtube')

  function handleLogin(t) {
    localStorage.setItem('token', t)
    setToken(t)
  }

  function handleLogout() {
    localStorage.removeItem('token')
    setToken('')
  }

  if (!token) {
    return <Auth onLogin={handleLogin} />
  }

  return (
    <div className="app">
      <header className="topbar">
        <span className="logo">Random Thoughts</span>
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
