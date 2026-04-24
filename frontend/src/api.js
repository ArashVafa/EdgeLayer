import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: BASE,
  timeout: 30000,
})

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

export default api
