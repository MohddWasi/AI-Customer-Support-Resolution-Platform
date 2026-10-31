import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'

import { ApiError, apiRequest } from '../lib/api'
import { AuthContext, type RegisterData, type User } from './AuthContext'

const TOKEN_KEY = 'acsrp.accessToken'

function readStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

function storeToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    // Storage unavailable (e.g. private mode): the session just won't survive a reload
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [token, setToken] = useState<string | null>(readStoredToken)

  const endSession = useCallback(() => {
    storeToken(null)
    setToken(null)
  }, [])

  const logout = useCallback(() => {
    endSession()
    queryClient.clear()
  }, [endSession, queryClient])

  const meQuery = useQuery({
    queryKey: ['auth', 'me', token],
    queryFn: async () => {
      try {
        return await apiRequest<User>('/auth/me', { token })
      } catch (error) {
        // An expired or revoked token ends the session
        if (error instanceof ApiError && error.status === 401) endSession()
        throw error
      }
    },
    enabled: token !== null,
    retry: false,
  })

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await apiRequest<{ access_token: string }>('/auth/login', {
      method: 'POST',
      body: { email, password },
    })
    storeToken(access_token)
    setToken(access_token)
  }, [])

  const register = useCallback(async (data: RegisterData) => {
    await apiRequest<User>('/auth/register', { method: 'POST', body: data })
    await login(data.email, data.password)
  }, [login])

  const value = useMemo(() => ({
    token,
    user: meQuery.data ?? null,
    isLoadingUser: token !== null && meQuery.isPending,
    login,
    register,
    logout,
  }), [token, meQuery.data, meQuery.isPending, login, register, logout])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
