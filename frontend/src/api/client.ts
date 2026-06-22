import axios from 'axios'
import toast from 'react-hot-toast'
import { API_BASE_URL } from '@/lib/constants'
import { getToken } from '@/store/auth-store'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 0,
  headers: { 'Content-Type': 'application/json' },
})

// Attach the bearer token (if any) to every request.
apiClient.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

const AUTH_PATHS = ['/login', '/register']

apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
    const status = error.response?.status
    const url: string = error.config?.url || ''
    const onAuthPage = AUTH_PATHS.some((p) => window.location.pathname.startsWith(p))

    // Session expired / not logged in: drop the token and send to login.
    // (Skip when the failing call IS the login/register attempt — that page
    // shows its own error message.)
    if (status === 401 && !url.includes('/auth/login') && !url.includes('/auth/register')) {
      localStorage.removeItem('financeflow_token')
      localStorage.removeItem('financeflow_user')
      if (!onAuthPage) {
        window.location.assign('/login')
        return Promise.reject(error)
      }
    }

    let msg = 'Something went wrong'
    if (error.response?.data?.detail) {
      const detail = error.response.data.detail
      if (typeof detail === 'string') {
        msg = detail
      } else if (Array.isArray(detail)) {
        msg = detail.map((d: any) => d.msg || JSON.stringify(d)).join(', ')
      } else {
        msg = JSON.stringify(detail)
      }
    } else {
      msg = error.message || msg
    }
    if (status !== 404 && status !== 401) {
      toast.error(msg)
    }
    return Promise.reject(error)
  },
)

export default apiClient
