import { useEffect, useRef } from 'react'
import Message from './Message'

export default function MessageList({ messages, loading }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  if (messages.length === 0) {
    return (
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '0 40px', textAlign: 'center' }}>
        <div style={{ width: 56, height: 56, background: '#eff6ff', borderRadius: 16, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 20 }}>
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
          </svg>
        </div>
        <div style={{ fontSize: 22, fontWeight: 700, color: '#111827', marginBottom: 10 }}>What would you like to know?</div>
        <div style={{ fontSize: 14, color: '#6b7280', maxWidth: 420, lineHeight: 1.7, marginBottom: 32 }}>
          Ask any question about the dataset. I'll write the SQL, run it, and show you the results.
        </div>

      </div>
    )
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '28px 24px', display: 'flex', flexDirection: 'column', gap: 24 }}>
      {messages.map((msg, i) => (
        <Message key={i} message={msg} />
      ))}

      {loading && (
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          <div style={{ width: 32, height: 32, background: '#2563eb', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#9ca3af' }}>AI</div>
            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '4px 16px 16px 16px', padding: '12px 16px', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
              <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                {[0, 150, 300].map((d) => (
                  <span key={d} style={{ width: 7, height: 7, borderRadius: '50%', background: '#d1d5db', display: 'inline-block', animation: `bounce 1.2s ease-in-out ${d}ms infinite` }}/>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
      <style>{`@keyframes bounce { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-5px)} }`}</style>
      <div ref={bottomRef} />
    </div>
  )
}