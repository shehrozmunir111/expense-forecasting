import apiClient from './client'
import type { AuthUser } from '@/store/auth-store'

interface LoginResponse {
  access_token: string
  token_type: string
  user: AuthUser
}

export const authApi = {
  // OAuth2 password flow: the backend expects form-encoded username/password.
  login: (email: string, password: string) => {
    const body = new URLSearchParams({ username: email, password })
    return apiClient
      .post<LoginResponse>('/auth/login', body, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      .then((r) => r.data)
  },

  register: (data: { email: string; password: string; full_name?: string }) =>
    apiClient.post<AuthUser>('/auth/register', data).then((r) => r.data),

  me: () => apiClient.get<AuthUser>('/auth/me').then((r) => r.data),
}
