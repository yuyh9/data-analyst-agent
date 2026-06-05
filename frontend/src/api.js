import axios from 'axios'

const api = axios.create({
  baseURL: '',
  headers: { 'Content-Type': 'application/json' }
})

export async function sendMessage(message, sessionId) {
  const res = await api.post('/chat', {
    message,
    session_id: sessionId || undefined
  })
  return res.data
}

export async function getSession(sessionId) {
  const res = await api.get(`/session/${sessionId}`)
  return res.data
}

export async function clearSession(sessionId) {
  const res = await api.delete(`/session/${sessionId}`)
  return res.data
}

export async function getTables() {
  const res = await api.get('/tables')
  return res.data
}

export async function healthCheck() {
  const res = await api.get('/health')
  return res.data
}