const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api'
const TOKEN_KEY = 'daily-trivia-auth-token'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(localStorage.getItem(TOKEN_KEY) ? { Authorization: `Token ${localStorage.getItem(TOKEN_KEY)}` } : {}),
      ...(options.headers ?? {}),
    },
    ...options,
  })

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    const message = data?.detail
      ?? Object.values(data ?? {}).flat().join(' ')
      ?? `Request failed: ${response.status}`
    throw new Error(message || `Request failed: ${response.status}`)
  }

  return data
}
export const api = {
  setToken: (token) => localStorage.setItem(TOKEN_KEY, token),
  clearToken: () => localStorage.removeItem(TOKEN_KEY),
  hasToken: () => Boolean(localStorage.getItem(TOKEN_KEY)),
  requestCode: (payload) => request('/auth/request-code/', { method: 'POST', body: JSON.stringify(payload) }),
  verifyCode: (payload) => request('/auth/verify-code/', { method: 'POST', body: JSON.stringify(payload) }),
  getMe: () => request('/auth/me/'),
  logout: () => request('/auth/logout/', { method: 'POST' }),
  getUsers: () => request('/users/'),
  deleteUser: (userId) => request(`/users/${userId}/`, {
    method: 'DELETE',
  }),
  getLeaderboard: () => request('/leaderboard/'),
  getMasterCycles: () => request('/master-cycles/'),
  createMasterCycle: (payload) => request('/master-cycles/', { method: 'POST', body: JSON.stringify(payload) }),
  generateTrivia: (cycleId, payload) => request(`/master-cycles/${cycleId}/generate-trivia/`, { method: 'POST', body: JSON.stringify(payload) }),
  getTriviaSession: (sessionId) => request(`/trivia-sessions/${sessionId}/`),
  publishTriviaSession: (sessionId) => request(`/trivia-sessions/${sessionId}/publish/`, { method: 'POST' }),
  evaluateTriviaSession: (sessionId) => request(`/trivia-sessions/${sessionId}/evaluate/`, { method: 'POST' }),
  submitAnswer: (sessionId, payload) => request(`/trivia-sessions/${sessionId}/answers/`, { method: 'POST', body: JSON.stringify(payload) }),
}
