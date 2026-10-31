from sqlalchemy import Select, or_, select

from app.models.organization_member import OrganizationMember, OrganizationRole
from app.models.ticket import Ticket


def visible_tickets(membership: OrganizationMember) -> Select[tuple[Ticket]]:
    """Tickets the member may see, always limited to their organization.

    Customers see their own tickets; support agents see tickets assigned to them
    and the unassigned queue; admins see every ticket in the organization.
    """
    query = select(Ticket).where(Ticket.organization_id == membership.organization_id)

    if membership.role == OrganizationRole.CUSTOMER:
        return query.where(Ticket.customer_id == membership.user_id)
    if membership.role == OrganizationRole.SUPPORT_AGENT:
        return query.where(
            or_(Ticket.assigned_to_user_id == membership.user_id, Ticket.assigned_to_user_id.is_(None))
        )
    return query
