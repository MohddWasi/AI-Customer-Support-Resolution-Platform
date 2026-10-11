
import { useEffect, useState } from 'react'

type HealthStatus = {
  status: string
  database?: string
  redis?: string
}

function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_BASE_URL}/health/ready`)
      .then((response) => {
        if (!response.ok) throw new Error('Backend is not ready')
        return response.json()
      })
      .then(setHealth)
      .catch((err: Error) => setError(err.message))
  }, [])


  

  return (
    <main className="min-h-screen bg-gray-100 p-8 text-gray-900">
      <h1 className="mb-6 text-3xl font-bold">
        AI Customer Support Resolution Platform
      </h1>

      <section className="rounded-lg bg-white p-6 shadow">
        <h2 className="mb-4 text-xl font-semibold">System Health</h2>

        {error && <p className="text-red-600">Error: {error}</p>}
        {!health && !error && <p>Checking services...</p>}

        {health && (
          <div className="space-y-2">
            <p>Backend: {health.status}</p>
            <p>Database: {health.database ?? 'Unknown'}</p>
            <p>Redis: {health.redis ?? 'Unknown'}</p>
          </div>
        )}
      </section>
    </main>
  )
}

export default App
