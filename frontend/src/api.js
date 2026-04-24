import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: BASE,
  timeout: 30000,
})

// Attach JWT to every request
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Player APIs ───────────────────────────────────────────────────────────────

export const searchPlayers = (q) =>
  api.get('/api/search', { params: { q } }).then(r => r.data)

export const getPlayer = (id) =>
  api.get(`/api/player/${id}`).then(r => r.data)

export const getReport = (id, refresh = false) =>
  api.get(`/api/report/${id}`, { params: refresh ? { refresh: true } : {} }).then(r => r.data)

export const refreshReport = (id) =>
  api.post(`/api/report/${id}/refresh`).then(r => r.data)

export const getFixtures = (team, limit = 20) =>
  api.get('/api/fixtures', { params: { team, limit } }).then(r => r.data)

export const getHealth = () =>
  api.get('/api/health').then(r => r.data)

export const triggerScrape = (source) =>
  api.post(`/api/admin/scrape/${source}`).then(r => r.data)

// ── Auth APIs ─────────────────────────────────────────────────────────────────

export const authApi = {
  register: (email, password) =>
    api.post('/auth/register', { email, password }).then(r => r.data),

  login: (email, password) =>
    api.post('/auth/login', { email, password }).then(r => r.data),

  refresh: (token) =>
    api.post('/auth/refresh', { token }).then(r => r.data),

  forgotPassword: (email) =>
    api.post('/auth/forgot-password', { email }).then(r => r.data),

  resetPassword: (token, password) =>
    api.post('/auth/reset-password', { token, password }).then(r => r.data),

  me: () =>
    api.get('/auth/me').then(r => r.data),
}

export default api
