import { useState } from 'react'

const SUGGESTIONS = [
  'How many unique customers are in the database?',
  'What is the average review score?',
  'Which product category has the most orders?',
  'Show me top 5 sellers by total revenue as a bar chart',
  'What is the total revenue converted to USD?',
  'Convert total 2017 revenue to EUR"',
  'Show me top 5 categories by revenue',
  'Now show that as a pie chart',
]

export default function ChatInput({ onSend, loading }) {
  const [value, setValue] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    if (!value.trim() || loading) return
    onSend(value.trim())
    setValue('')
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div style={{ background: '#fff', borderTop: '1px solid #e5e7eb', padding: '10px 20px 16px', flexShrink: 0 }}>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onSend(s)}
            disabled={loading}
            style={{
              fontSize: 11, padding: '4px 10px', borderRadius: 20,
              border: '1px solid #e5e7eb', background: '#f9fafb',
              color: '#6b7280', cursor: 'pointer', transition: 'all 0.15s',
              opacity: loading ? 0.4 : 1, whiteSpace: 'nowrap'
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = '#2563eb'; e.currentTarget.style.color = '#2563eb'; e.currentTarget.style.background = '#eff6ff' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = '#e5e7eb'; e.currentTarget.style.color = '#6b7280'; e.currentTarget.style.background = '#f9fafb' }}
          >
            {s}
          </button>
        ))}
      </div>
      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything…"
          rows={1}
          disabled={loading}
          style={{
            flex: 1, resize: 'none', border: '1.5px solid #e5e7eb',
            borderRadius: 12, padding: '11px 14px', fontSize: 14,
            fontFamily: 'inherit', outline: 'none', background: '#f9fafb',
            color: '#111827', transition: 'border-color 0.15s',
            opacity: loading ? 0.6 : 1, boxSizing: 'border-box', lineHeight: 1.5
          }}
          onFocus={e => e.target.style.borderColor = '#2563eb'}
          onBlur={e => e.target.style.borderColor = '#e5e7eb'}
        />
        <button
          type="submit"
          disabled={loading || !value.trim()}
          style={{
            width: 44, height: 44, flexShrink: 0,
            background: loading || !value.trim() ? '#e5e7eb' : '#2563eb',
            color: loading || !value.trim() ? '#9ca3af' : '#fff',
            border: 'none', borderRadius: 12,
            cursor: loading || !value.trim() ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'all 0.15s'
          }}
        >
          {loading ? (
            <svg style={{ animation: 'spin 1s linear infinite', width: 16, height: 16 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" strokeLinecap="round"/>
            </svg>
          ) : (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          )}
        </button>
      </form>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}