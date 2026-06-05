export default function ChartDisplay({ chartUrl }) {
  if (!chartUrl) return null
  const fullUrl = chartUrl.startsWith('http') ? chartUrl : `http://localhost:8000${chartUrl}`
  return (
    <div style={{ borderRadius: 12, overflow: 'hidden', border: '1px solid #e5e7eb', background: '#fff', boxShadow: '0 1px 3px rgba(0,0,0,0.06)', maxWidth: 560 }}>
      <img
        src={fullUrl}
        alt="Chart"
        style={{ width: '100%', objectFit: 'contain', maxHeight: 360, display: 'block' }}
        onError={(e) => { e.target.style.display = 'none' }}
      />
    </div>
  )
}