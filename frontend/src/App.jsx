import { useState, useCallback, useEffect, useRef } from 'react'
import MessageList from './components/MessageList'
import ChatInput from './components/ChatInput'
import { sendMessage } from './api'

export default function App() {
  const [messages, setMessages] = useState([])
  const [sessionId, setSessionId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef(null)

  useEffect(() => { fetchSessions() }, [])

  async function fetchSessions() {
    try {
      const res = await fetch('/sessions')
      const data = await res.json()
      setSessions(data.sessions || [])
    } catch {}
  }

  async function loadSessionMessages(sid) {
    try {
      const res = await fetch(`/session/${sid}/messages`)
      const data = await res.json()
      const msgs = (data.messages || []).map(m => ({
        role: m.role,
        content: m.content,
        chartUrl: m.chart_url || null,
        reportUrl: m.report_url || null,
        sqlQueries: m.sql_queries || [],
        tablesUsed: m.tables_used || []
      }))
      setMessages(msgs)
    } catch {}
  }

  async function handleUpload(e) {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await fetch('/upload/csv', { method: 'POST', body: formData })
      const data = await res.json()
      if (data.success) {
        setError(null)
        handleSend(`I just uploaded a dataset called "${data.table_name}" with ${data.rows.toLocaleString()} rows and columns: ${data.columns.join(', ')}. Give me a quick summary of what questions I can ask about this data.`)
      } else {
        setError(data.detail || 'Upload failed')
      }
    } catch {
      setError('Upload failed. Is the backend running?')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleSend = useCallback(async (text) => {
    if (loading) return
    setError(null)
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setLoading(true)
    try {
      const data = await sendMessage(text, sessionId)
      if (!sessionId) {
        setSessionId(data.session_id)
        setActiveSessionId(data.session_id)
      }
      // refresh sessions after every message
      fetchSessions()
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: data.answer,
        chartUrl: data.chart_url,
        reportUrl: data.report_url,
        tablesUsed: data.tables_used,
        sqlQueries: data.sql_queries || []
      }])
    } catch {
      setError('Something went wrong. Is the backend running?')
      setMessages((prev) => prev.slice(0, -1))
    } finally {
      setLoading(false)
    }
  }, [loading, sessionId])

  function handleNewChat() {
    setMessages([])
    setSessionId(null)
    setActiveSessionId(null)
    setError(null)
    fetchSessions()
  }

  async function handleDeleteSession(sid, e) {
    e.stopPropagation()
    try {
      await fetch(`/session/${sid}`, { method: 'DELETE' })
      if (activeSessionId === sid) handleNewChat()
      fetchSessions()
    } catch {}
  }

  return (
    <div style={{ height: '100vh', display: 'flex', background: '#f0f2f5', fontFamily: "'Inter', system-ui, sans-serif", overflow: 'hidden' }}>

      {sidebarOpen && (
        <aside style={{ width: 260, background: '#fff', borderRight: '1px solid #e8eaed', display: 'flex', flexDirection: 'column', flexShrink: 0, overflow: 'hidden' }}>

          <div style={{ padding: '20px 16px 16px', borderBottom: '1px solid #f1f3f4' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
              <div style={{ width: 32, height: 32, background: '#2563eb', borderRadius: 9, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
                </svg>
              </div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: '#111827' }}>Data Analyst</div>
                <div style={{ fontSize: 11, color: '#9ca3af' }}>AI-powered insights</div>
              </div>
            </div>

            <button onClick={handleNewChat}
              style={{ width: '100%', padding: '9px 14px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 9, fontSize: 13, fontWeight: 500, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
              onMouseEnter={e => e.currentTarget.style.background = '#1d4ed8'}
              onMouseLeave={e => e.currentTarget.style.background = '#2563eb'}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
              </svg>
              New chat
            </button>

            <button onClick={() => fileInputRef.current?.click()} disabled={uploading}
              style={{ width: '100%', marginTop: 8, padding: '8px 14px', background: 'none', color: '#6b7280', border: '1px solid #e5e7eb', borderRadius: 9, fontSize: 13, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = '#2563eb'; e.currentTarget.style.color = '#2563eb' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = '#e5e7eb'; e.currentTarget.style.color = '#6b7280' }}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              {uploading ? 'Uploading…' : 'Upload CSV'}
            </button>
            <input ref={fileInputRef} type="file" accept=".csv" onChange={handleUpload} style={{ display: 'none' }}/>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: '12px 8px' }}>
            {sessions.length > 0 ? (
              <>
                <div style={{ fontSize: 10, color: '#9ca3af', marginBottom: 6, padding: '0 8px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Recent chats</div>
                {sessions.slice(0, 20).map((sid, i) => (
                  <div key={sid}
                    onClick={() => { setSessionId(sid); setActiveSessionId(sid); loadSessionMessages(sid) }}
                    style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 10px', borderRadius: 8, cursor: 'pointer', marginBottom: 2, background: activeSessionId === sid ? '#eff6ff' : 'transparent', transition: 'background 0.1s', gap: 8 }}
                    onMouseEnter={e => { if (activeSessionId !== sid) e.currentTarget.style.background = '#f9fafb' }}
                    onMouseLeave={e => { if (activeSessionId !== sid) e.currentTarget.style.background = 'transparent' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke={activeSessionId === sid ? '#2563eb' : '#9ca3af'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                      </svg>
                      <span style={{ fontSize: 12, color: activeSessionId === sid ? '#2563eb' : '#374151', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: activeSessionId === sid ? 500 : 400 }}>
                        Chat {sessions.length - i}
                      </span>
                    </div>
                    <button onClick={(e) => handleDeleteSession(sid, e)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#d1d5db', padding: 2, borderRadius: 4, display: 'flex', flexShrink: 0 }}
                      onMouseEnter={e => e.currentTarget.style.color = '#ef4444'}
                      onMouseLeave={e => e.currentTarget.style.color = '#d1d5db'}>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                        <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                      </svg>
                    </button>
                  </div>
                ))}
              </>
            ) : (
              <div style={{ padding: '20px 10px', textAlign: 'center', color: '#9ca3af', fontSize: 12 }}>No chat history yet</div>
            )}
          </div>
        </aside>
      )}

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <header style={{ background: '#fff', borderBottom: '1px solid #e5e7eb', padding: '0 20px', height: 54, display: 'flex', alignItems: 'center', gap: 14, flexShrink: 0, boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
          <button onClick={() => setSidebarOpen(v => !v)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 6, borderRadius: 6, color: '#6b7280', display: 'flex' }}
            onMouseEnter={e => e.currentTarget.style.background = '#f3f4f6'}
            onMouseLeave={e => e.currentTarget.style.background = 'none'}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 28, height: 28, background: '#2563eb', borderRadius: 7, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
              </svg>
            </div>
            <span style={{ fontSize: 15, fontWeight: 600, color: '#111827' }}>Data Analyst Agent</span>
          </div>
          <div style={{ height: 16, width: 1, background: '#e5e7eb' }}/>
          <span style={{ fontSize: 12, color: '#9ca3af' }}>Olist e-commerce · 8 tables · RAG · MCP</span>
          {loading && (
            <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#2563eb', background: '#eff6ff', padding: '4px 10px', borderRadius: 20 }}>
              <svg style={{ animation: 'spin 1s linear infinite', width: 12, height: 12 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" strokeLinecap="round"/>
              </svg>
              Analyzing…
            </div>
          )}
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </header>

        {error && (
          <div style={{ background: '#fef2f2', borderBottom: '1px solid #fecaca', padding: '8px 20px', fontSize: 12, color: '#dc2626', display: 'flex', justifyContent: 'space-between' }}>
            {error}
            <button onClick={() => setError(null)} style={{ background: 'none', border: 'none', color: '#dc2626', cursor: 'pointer' }}>✕</button>
          </div>
        )}

        <MessageList messages={messages} loading={loading} />
        <ChatInput onSend={handleSend} loading={loading} />
      </div>
    </div>
  )
}