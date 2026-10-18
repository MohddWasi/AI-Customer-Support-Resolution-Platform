"""Seed the development database with demo data.

Creates two organizations (so tenant isolation can be demonstrated), users in every role,
tickets with messages and events, and knowledge sources with document metadata.
Safe to run repeatedly: every record is looked up by its natural key before it is created.

Run from backend/:  uv run python -m app.db.seed
"""

import asyncio
import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import asyncSessionLocal, engine
from app.models import (
    Document,
    KnowledgeSource,
    Organization,
    OrganizationMember,
    Ticket,
    TicketEvent,
    TicketMessage,
    User,
)
from app.models.document import DocumentAccessLevel, DocumentSourceType
from app.models.organization_member import OrganizationRole
from app.models.ticket import TicketPriority, TicketStatus
from app.models.ticket_event import EventActorType, TicketEventType
from app.models.ticket_message import MessageSenderType

logger = logging.getLogger(__name__)

# Not a valid password hash: seeded users cannot log in until real auth (Phase 3) sets one
UNUSABLE_PASSWORD_HASH = "!seed-user-no-login"

ORGANIZATIONS = [
    {"name": "Acme Software", "domain": "acme.example"},
    {"name": "Globex Engineering", "domain": "globex.example"},
]

# (key, local part of email, full name, role)
USERS = [
    ("admin", "admin", "Alex Admin", OrganizationRole.ADMIN),
    ("agent", "agent", "Sam Agent", OrganizationRole.SUPPORT_AGENT),
    ("customer1", "chris", "Chris Customer", OrganizationRole.CUSTOMER),
    ("customer2", "dana", "Dana Developer", OrganizationRole.CUSTOMER),
]

TICKETS: list[dict[str, Any]] = [
    {
        "subject": "Cannot push over HTTPS after enabling 2FA",
        "customer": "customer1",
        "assignee": None,
        "status": TicketStatus.IN_PROGRESS,
        "priority": TicketPriority.HIGH,
        "classification": {
            "category": "authentication",
            "intent": "two_factor_git_https",
            "sentiment": "frustrated",
            "product_area": "two_factor_authentication",
        },
        "messages": [
            (MessageSenderType.CUSTOMER, "I enabled two-factor authentication and now git push over HTTPS "
             "rejects my password. How do I push again?"),
            (MessageSenderType.AI, "With 2FA enabled, Git over HTTPS no longer accepts your account password. "
             "Create a personal access token with the write_repository scope and use it as the password."),
        ],
        "events": [
            (TicketEventType.CREATED, EventActorType.CUSTOMER, None),
            (TicketEventType.CLASSIFIED, EventActorType.AI, {"category": "authentication", "priority": "high"}),
            (TicketEventType.STATUS_CHANGED, EventActorType.SYSTEM, {"from": "new", "to": "in_progress"}),
        ],
    },
    {
        "subject": "Developer lost access to private project",
        "customer": "customer2",
        "assignee": "agent",
        "status": TicketStatus.WAITING_FOR_CUSTOMER,
        "priority": TicketPriority.MEDIUM,
        "classification": {
            "category": "permissions",
            "intent": "project_access_lost",
            "sentiment": "neutral",
            "product_area": "project_members",
        },
        "messages": [
            (MessageSenderType.CUSTOMER, "A developer on my team can no longer open our private project. "
             "Nothing changed on our side."),
            (MessageSenderType.SUPPORT_AGENT, "Could you confirm the developer's role in Project information > "
             "Members and whether their membership has an expiration date?"),
        ],
        "events": [
            (TicketEventType.CREATED, EventActorType.CUSTOMER, None),
            (TicketEventType.ASSIGNED, EventActorType.SYSTEM, {"assigned_to": "agent"}),
            (TicketEventType.STATUS_CHANGED, EventActorType.SUPPORT_AGENT,
             {"from": "new", "to": "waiting_for_customer"}),
        ],
    },
    {
        "subject": "CI job stays pending with 'This job is stuck'",
        "customer": "customer1",
        "assignee": None,
        "status": TicketStatus.NEW,
        "priority": TicketPriority.MEDIUM,
        "classification": None,
        "messages": [
            (MessageSenderType.CUSTOMER, "Our pipeline jobs stay pending and show 'This job is stuck because "
             "you don't have any active runners that can run this job'."),
        ],
        "events": [
            (TicketEventType.CREATED, EventActorType.CUSTOMER, None),
        ],
    },
    {
        "subject": "docker login to container registry returns 403",
        "customer": "customer2",
        "assignee": "agent",
        "status": TicketStatus.RESOLVED,
        "priority": TicketPriority.LOW,
        "classification": {
            "category": "container_registry",
            "intent": "registry_authentication_failed",
            "sentiment": "neutral",
            "product_area": "container_registry",
        },
        "messages": [
            (MessageSenderType.CUSTOMER, "docker login to our registry fails with 403 Forbidden."),
            (MessageSenderType.SUPPORT_AGENT, "Use a personal access token with the read_registry and "
             "write_registry scopes as the password. That resolved it for similar cases."),
            (MessageSenderType.CUSTOMER, "That worked, thanks!"),
        ],
        "events": [
            (TicketEventType.CREATED, EventActorType.CUSTOMER, None),
            (TicketEventType.ASSIGNED, EventActorType.SYSTEM, {"assigned_to": "agent"}),
            (TicketEventType.STATUS_CHANGED, EventActorType.SUPPORT_AGENT, {"from": "new", "to": "resolved"}),
        ],
    },
]

# (source name, source url, description, documents: (title, url, source type, access level))
KNOWLEDGE_SOURCES: list[tuple[str, str | None, str, list[tuple[str, str | None, DocumentSourceType, DocumentAccessLevel]]]] = [
    (
        "GitLab Documentation",
        "https://docs.gitlab.com",
        "Official public GitLab documentation (external product knowledge).",
        [
            ("Roles and permissions", "https://docs.gitlab.com/user/permissions/",
             DocumentSourceType.PRODUCT_DOCS, DocumentAccessLevel.PUBLIC),
            ("Members of a project", "https://docs.gitlab.com/user/project/members/",
             DocumentSourceType.PRODUCT_DOCS, DocumentAccessLevel.PUBLIC),
            ("Two-factor authentication", "https://docs.gitlab.com/user/profile/account/two_factor_authentication/",
             DocumentSourceType.PRODUCT_DOCS, DocumentAccessLevel.PUBLIC),
            ("Troubleshooting jobs", "https://docs.gitlab.com/ci/jobs/job_troubleshooting/",
             DocumentSourceType.TROUBLESHOOTING, DocumentAccessLevel.PUBLIC),
            ("Troubleshooting the container registry",
             "https://docs.gitlab.com/user/packages/container_registry/troubleshoot_container_registry/",
             DocumentSourceType.TROUBLESHOOTING, DocumentAccessLevel.PUBLIC),
        ],
    ),
    (
        "Support Policies",
        None,
        "Internal support rules and synthetic support history (generated for the demo).",
        [
            ("Support Escalation Policy", None, DocumentSourceType.INTERNAL_POLICY, DocumentAccessLevel.INTERNAL),
            ("Sensitive Action Policy", None, DocumentSourceType.INTERNAL_POLICY, DocumentAccessLevel.INTERNAL),
            ("Support FAQ", None, DocumentSourceType.FAQ, DocumentAccessLevel.PUBLIC),
            ("Historical Ticket TKT-0001", None, DocumentSourceType.HISTORICAL_TICKET, DocumentAccessLevel.INTERNAL),
        ],
    ),
]


async def get_or_create(session: AsyncSession, model: type, lookup: dict[str, Any], **values: Any) -> tuple[Any, bool]:
    """Return the row matching `lookup`, creating it with `values` if it doesn't exist."""
    row = (await session.execute(select(model).filter_by(**lookup))).scalar_one_or_none()
    if row is not None:
        return row, False
    row = model(**lookup, **values)
    session.add(row)
    await session.flush()
    return row, True


async def seed_organization(session: AsyncSession, name: str, domain: str) -> dict[str, int]:
    created = {"users": 0, "tickets": 0, "documents": 0}

    org, _ = await get_or_create(session, Organization, {"name": name})

    users: dict[str, User] = {}
    for key, local_part, full_name, role in USERS:
        user, is_new = await get_or_create(
            session,
            User,
            {"email": f"{local_part}@{domain}"},
            full_name=full_name,
            hashed_password=UNUSABLE_PASSWORD_HASH,
        )
        created["users"] += is_new
        users[key] = user
        await get_or_create(
            session,
            OrganizationMember,
            {"organization_id": org.id, "user_id": user.id},
            role=role,
        )

    for spec in TICKETS:
        ticket, is_new = await get_or_create(
            session,
            Ticket,
            {"organization_id": org.id, "subject": spec["subject"]},
            customer_id=users[spec["customer"]].id,
            assigned_to_user_id=users[spec["assignee"]].id if spec["assignee"] else None,
            status=spec["status"],
            priority=spec["priority"],
            resolved_at=datetime.now(UTC) if spec["status"] == TicketStatus.RESOLVED else None,
            **(spec["classification"] or {}),
        )
        if not is_new:
            continue  # messages and events were created together with the ticket
        created["tickets"] += 1

        senders = {
            MessageSenderType.CUSTOMER: users[spec["customer"]].id,
            MessageSenderType.SUPPORT_AGENT: users["agent"].id,
            MessageSenderType.AI: None,
        }
        for sender_type, content in spec["messages"]:
            session.add(TicketMessage(
                organization_id=org.id,
                ticket_id=ticket.id,
                sender_type=sender_type,
                sender_user_id=senders[sender_type],
                content=content,
            ))

        actors = {
            EventActorType.CUSTOMER: users[spec["customer"]].id,
            EventActorType.SUPPORT_AGENT: users["agent"].id,
            EventActorType.AI: None,
            EventActorType.SYSTEM: None,
        }
        for event_type, actor_type, details in spec["events"]:
            session.add(TicketEvent(
                organization_id=org.id,
                ticket_id=ticket.id,
                event_type=event_type,
                actor_type=actor_type,
                actor_user_id=actors[actor_type],
                details=details,
            ))

    for source_name, source_url, description, documents in KNOWLEDGE_SOURCES:
        source, _ = await get_or_create(
            session,
            KnowledgeSource,
            {"organization_id": org.id, "name": source_name},
            description=description,
            url=source_url,
        )
        for title, url, source_type, access_level in documents:
            _, is_new = await get_or_create(
                session,
                Document,
                {"knowledge_source_id": source.id, "title": title},
                organization_id=org.id,
                url=url,
                source_type=source_type,
                access_level=access_level,
                product="GitLab",
                # Placeholder until the ingestion pipeline hashes the real content
                content_hash=hashlib.sha256(f"{title}|{url}".encode()).hexdigest(),
            )
            created["documents"] += is_new

    return created


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        async with asyncSessionLocal() as session:
            for org in ORGANIZATIONS:
                created = await seed_organization(session, org["name"], org["domain"])
                logger.info("%s: created %s", org["name"], created)
            await session.commit()
        logger.info("Seed complete.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
