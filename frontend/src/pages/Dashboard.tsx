import { useQuery } from '@tanstack/react-query'

import { useCurrentOrganization } from '../lib/useCurrentOrganization'

type HealthStatus = {
  status: string
  database?: string
  redis?: string
}

async function fetchHealth(): Promise<HealthStatus> {
  const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/health/ready`)

  if (!response.ok) {
    throw new Error('Backend is not ready')
  }

  return response.json()
}

function Dashboard() {
  const organization = useCurrentOrganization()
  const { data: health, isPending, error } = useQuery({
    queryKey: ['system-health'],
    queryFn: fetchHealth,
    retry: 1,
    refetchInterval: 30_000,
  })

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard{organization && ` · ${organization.name}`}</h1>

      <section className="rounded-lg bg-white p-6 shadow">
        <h2 className="mb-4 text-xl font-semibold">System Health</h2>

        {isPending && <p>Checking services...</p>}
        {error && <p className="text-red-600">Error: {error.message}</p>}

        {health && (
          <div className="space-y-2">
            <p>Backend: {health.status}</p>
            <p>Database: {health.database ?? 'Unknown'}</p>
            <p>Redis: {health.redis ?? 'Unknown'}</p>
          </div>
        )}
      </section>
    </div>
  )
}

export default Dashboard
