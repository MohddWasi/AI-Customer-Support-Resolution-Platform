
import { useParams } from 'react-router-dom'

function TicketDetails() {
  const { ticketId } = useParams()

  return <h1 className="text-2xl font-bold">Ticket: {ticketId}</h1>
}

export default TicketDetails
