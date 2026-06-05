import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import ChartDisplay from './ChartDisplay'

export default function Message({ message }) {
  const isUser = message.role === 'user'

  return (
    <div style={{ display: 'flex', gap: 12, justifyContent: isUser ? 'flex-end' : 'flex-start', alignItems: 'flex-start' }}>

      {!isUser && (
        <div style={{ width: 32, height: 32, background: '#2563eb', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 20 }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
          </svg>
        </div>
      )}

      <div style={{ maxWidth: 660, display: 'flex', flexDirection: 'column', gap: 4, alignItems: isUser ? 'flex-end' : 'flex-start' }}>

        <div style={{ fontSize: 11, fontWeight: 600, color: '#9ca3af', paddingLeft: 2 }}>
          {isUser ? 'User' : 'AI'}
        </div>

        {/* message bubble */}
        <div style={{
          padding: '10px 14px',
          borderRadius: isUser ? '16px 4px 16px 16px' : '4px 16px 16px 16px',
          background: isUser ? '#2563eb' : '#fff',
          border: isUser ? 'none' : '1px solid #e5e7eb',
          color: isUser ? '#fff' : '#1f2937',
          fontSize: 14, lineHeight: 1.7,
          boxShadow: isUser ? '0 2px 8px rgba(37,99,235,0.2)' : '0 1px 3px rgba(0,0,0,0.05)'
        }}>
          {isUser ? (
            <p style={{ margin: 0 }}>{message.content}</p>
          ) : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ children }) => <p style={{ margin: '0 0 8px' }}>{children}</p>,
                strong: ({ children }) => <strong style={{ fontWeight: 600 }}>{children}</strong>,
                ul: ({ children }) => <ul style={{ paddingLeft: 18, margin: '0 0 8px' }}>{children}</ul>,
                ol: ({ children }) => <ol style={{ paddingLeft: 18, margin: '0 0 8px' }}>{children}</ol>,
                li: ({ children }) => <li style={{ marginBottom: 4 }}>{children}</li>,
                h3: ({ children }) => <h3 style={{ fontSize: 14, fontWeight: 600, margin: '4px 0' }}>{children}</h3>,
                code: ({ children }) => <code style={{ background: '#f3f4f6', padding: '1px 5px', borderRadius: 4, fontSize: 12, fontFamily: 'monospace' }}>{children}</code>,
                table: ({ children }) => (
                  <div style={{ overflowX: 'auto', margin: '8px 0' }}>
                    <table style={{ fontSize: 12, borderCollapse: 'collapse', width: '100%' }}>{children}</table>
                  </div>
                ),
                thead: ({ children }) => <thead style={{ background: '#f9fafb' }}>{children}</thead>,
                th: ({ children }) => <th style={{ border: '1px solid #e5e7eb', padding: '5px 10px', textAlign: 'left', fontWeight: 600, color: '#374151' }}>{children}</th>,
                td: ({ children }) => <td style={{ border: '1px solid #e5e7eb', padding: '5px 10px', color: '#374151' }}>{children}</td>,
                tr: ({ children }) => <tr>{children}</tr>,
              }}
            >
              {message.content.replace(/!\[.*?\]\(.*?\)/g, '').trim()}
            </ReactMarkdown>
          )}
        </div>

        {/* chart */}
        {message.chartUrl && <ChartDisplay chartUrl={message.chartUrl} />}

        {/* report download button */}
        {message.reportUrl && (
          <a
            href={`http://localhost:8000/download/report/${message.reportUrl.split('/').pop()}`}
            download
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 14px', background: '#fff', border: '1.5px solid #2563eb', borderRadius: 8, fontSize: 13, color: '#2563eb', fontWeight: 500, textDecoration: 'none', transition: 'all 0.15s' }}
            onMouseEnter={e => e.currentTarget.style.background = '#eff6ff'}
            onMouseLeave={e => e.currentTarget.style.background = '#fff'}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            Download report ({message.reportUrl.endsWith('.pdf') ? 'PDF' : 'Word'})
          </a>
        )}

        {/* SQL ReAct trace — collapsible */}
        {message.sqlQueries && message.sqlQueries.length > 0 && (
          <details style={{ width: '100%', maxWidth: 600 }}>
            <summary style={{
              fontSize: 11, color: '#9ca3af', cursor: 'pointer',
              userSelect: 'none', display: 'flex', alignItems: 'center',
              gap: 6, paddingLeft: 2, listStyle: 'none', outline: 'none'
            }}>
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
              </svg>
              View SQL ({message.sqlQueries.length} {message.sqlQueries.length === 1 ? 'query' : 'queries'})
            </summary>
            {message.sqlQueries.map((sql, i) => (
              <pre key={i} style={{
                marginTop: 6, padding: '10px 14px',
                background: '#1e1e2e', color: '#cdd6f4',
                borderRadius: 10, fontSize: 11,
                overflowX: 'auto', lineHeight: 1.7,
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                border: '1px solid #313244'
              }}>
                {sql}
              </pre>
            ))}
          </details>
        )}

        {/* tables used */}
        {message.tablesUsed && message.tablesUsed.length > 0 && (
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', paddingLeft: 2 }}>
            <span style={{ fontSize: 10, color: '#9ca3af', alignSelf: 'center' }}>via</span>
            {message.tablesUsed.map((t) => (
              <span key={t} style={{ fontSize: 10, color: '#6b7280', background: '#f3f4f6', padding: '2px 7px', borderRadius: 20, border: '1px solid #e5e7eb', fontFamily: 'monospace' }}>
                {t}
              </span>
            ))}
          </div>
        )}
      </div>

      {isUser && (
        <div style={{ width: 32, height: 32, background: '#e5e7eb', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 600, color: '#4b5563', flexShrink: 0, marginTop: 20 }}>
          U
        </div>
      )}
    </div>
  )
}