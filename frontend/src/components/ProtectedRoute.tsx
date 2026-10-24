import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuth } from '../auth/useAuth'

function ProtectedRoute() {
  const { token, isLoadingUser } = useAuth()
  const location = useLocation()

  if (!token) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (isLoadingUser) return <p className="p-8 text-gray-600">Loading…</p>
  return <Outlet />
}

export default ProtectedRoute
