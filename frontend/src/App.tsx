
import {useQuery} from '@tanstack/react-query'
import { Route, Routes } from 'react-router-dom'
import Tickets from './pages/Tickets'
import Dashboard from './pages/Dashboard'
import TicketDetails from './pages/TicketDetails'

type HealthStatus = {
  status: string
  database?: string
  redis?: string
}

async function fetchHealth() : Promise<HealthStatus> {
  const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/health/ready`);

  if(!response.ok) {
    throw new Error('Backend is not ready');
  }

  return response.json();
}
function App() {
  const {data:health, isPending, error} = useQuery({
    queryKey: ['system-health'],
    queryFn: fetchHealth,
    retry: 1,
    refetchInterval: 30_000,
  })

  return (
    <main className="min-h-screen bg-gray-100 p-8 text-gray-900">
      <h1 className="mb-6 text-3xl font-bold">
        AI Customer Support Resolution Platform
      </h1>
      
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/tickets" element={<Tickets />} />
        <Route path="/tickets/:ticketId" element={<TicketDetails />} />
      </Routes>

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
    </main>
  )
}

export default App
