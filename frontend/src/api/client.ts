import axios from 'axios'
import toast from 'react-hot-toast'
import { API_BASE_URL } from '@/lib/constants'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 0,
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
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
    if (error.response?.status !== 404) {
      toast.error(msg)
    }
    return Promise.reject(error)
  },
)

export default apiClient
