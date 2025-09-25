
import { useEffect, useState } from 'react'

export default function App() {
  const [health, setHealth] = useState(null)
  const [sites, setSites] = useState([])

  useEffect(() => {
    fetch('/api/health').then(r => r.json()).then(setHealth).catch(console.error)
    fetch('/api/sites').then(r => r.json()).then(setSites).catch(console.error)
  }, [])

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', padding: 24 }}>
      <h1>AquaCharge — Minimal Starter</h1>
      <p>
        Backend health: <strong>{health ? health.status : 'loading...'}</strong>
      </p>

      <h2>Sites (placeholder)</h2>
      <ul>
        {sites.map(s => (
          <li key={s.id}><strong>{s.name}</strong> — {s.city}</li>
        ))}
      </ul>

      <p style={{marginTop: 24, color: '#666'}}>
        Edit <code>frontend/src/App.jsx</code> and <code>backend/app.py</code> to start building.
      </p>
    </div>
  )
}
