import { createContext } from 'react'

export type User = {
  id: string
  email: string
  full_name: string
}

export type RegisterData = {
  email: string
  full_name: string
  password: string
  organization_name?: string
}

export type AuthContextValue = {
  token: string | null
  user: User | null
  isLoadingUser: boolean
  login: (email: string, password: string) => Promise<void>
  register: (data: RegisterData) => Promise<void>
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)
