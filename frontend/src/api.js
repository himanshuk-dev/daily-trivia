const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
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
  getUsers: () => request('/users/'),
  createUser: (username) => request('/users/', { method: 'POST', body: JSON.stringify({ username }) }),
  deleteUser: (userId, actingUserId) => request(`/users/${userId}/`, {
    method: 'DELETE',
    body: JSON.stringify({ acting_user_id: actingUserId }),
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
