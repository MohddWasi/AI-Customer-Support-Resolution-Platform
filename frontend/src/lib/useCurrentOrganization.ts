import { useOutletContext } from 'react-router-dom'

export type Organization = {
  id: string
  name: string
  role: 'customer' | 'support_agent' | 'admin'
}

export type LayoutContext = {
  organization: Organization | null
}

// The organization selected in the header, for pages rendered inside AppLayout
export function useCurrentOrganization(): Organization | null {
  return useOutletContext<LayoutContext>().organization
}
