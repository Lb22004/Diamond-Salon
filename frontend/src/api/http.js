import axios from 'axios'

// Single HTTP client for every module (owner: P1). Requests go through the
// Vite proxy (/api -> backend), so no CORS issues in development.
const http = axios.create({ baseURL: '/api', timeout: 15000 })

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export default http
