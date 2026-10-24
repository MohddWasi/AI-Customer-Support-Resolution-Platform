import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, Outlet } from 'react-router-dom'

import { useAuth } from '../auth/useAuth'
import { apiRequest } from '../lib/api'
import type { LayoutContext, Organization } from '../lib/useCurrentOrganization'

const ORGANIZATION_KEY = 'acsrp.organizationId'

const ROLE_LABELS: Record<Organization['role'], string> = {
  admin: 'Admin',
  support_agent: 'Support agent',
  customer: 'Customer',
}

function readStoredOrganizationId(): string | null {
  try {
    return localStorage.getItem(ORGANIZATION_KEY)
  } catch {
    return null
  }
}

function AppLayout() {
  const { token, user, logout } = useAuth()
  const [selectedId, setSelectedId] = useState<string | null>(readStoredOrganizationId)

  const { data: organizations = [], isPending } = useQuery({
    queryKey: ['organizations', token],
    queryFn: () => apiRequest<Organization[]>('/organizations', { token }),
  })

  // Fall back to the first organization if the stored one is gone (e.g. membership removed)
  const organization = organizations.find((org) => org.id === selectedId) ?? organizations[0] ?? null

  function selectOrganization(id: string) {
    setSelectedId(id)
    try {
      localStorage.setItem(ORGANIZATION_KEY, id)
    } catch {
      // Storage unavailable: the choice just won't survive a reload
    }
  }

  const context: LayoutContext = { organization }

  return (
    <>
      <header className="flex flex-wrap items-center gap-4 bg-white px-8 py-4 shadow">
        <Link to="/" className="mr-auto text-xl font-bold">AI Customer Support</Link>

        {organizations.length > 0 && organization && (
          <label className="flex items-center gap-2 text-sm">
            <span className="text-gray-600">Organization</span>
            <select value={organization.id} onChange={(e) => selectOrganization(e.target.value)}
              className="rounded border border-gray-300 px-2 py-1">
              {organizations.map((org) => (
                <option key={org.id} value={org.id}>{org.name}</option>
              ))}
            </select>
            <span className="rounded bg-gray-100 px-2 py-1 text-xs">{ROLE_LABELS[organization.role]}</span>
          </label>
        )}

        <span className="text-sm text-gray-700">{user?.full_name}</span>
        <button onClick={logout} className="rounded border border-gray-300 px-3 py-1 text-sm hover:bg-gray-50">
          Log out
        </button>
      </header>

      <main className="p-8">
        {!isPending && organizations.length === 0 ? (
          <p className="rounded-lg bg-white p-6 shadow">
            You're not a member of any organization yet. Ask an organization admin to add you using your email
            {user && <strong> {user.email}</strong>}.
          </p>
        ) : (
          <Outlet context={context} />
        )}
      </main>
    </>
  )
}

export default AppLayout
