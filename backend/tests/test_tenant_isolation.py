"""Tenant isolation: data of one organization must never be visible to another.

DB tests run inside a rolled-back transaction (see conftest.db_session).
"""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401 - registers all models on Base.metadata
from app.db.base import Base
from app.models import AuditLog, DocumentChunk, Organization
from app.models.document import DocumentAccessLevel
from tests.conftest import make_tenant, unit_vector

# Tables that are not owned by a single organization
GLOBAL_TABLES = {"organizations", "users"}
# Audit history must outlive the organization, so its tenant id is nullable (SET NULL)
NULLABLE_TENANT_TABLES = {"audit_logs"}
TENANT_TABLES = sorted(set(Base.metadata.tables) - GLOBAL_TABLES)


@pytest.mark.parametrize("table_name", TENANT_TABLES)
def test_tenant_table_has_organization_id(table_name: str) -> None:
    table = Base.metadata.tables[table_name]

    assert "organization_id" in table.columns, f"{table_name} has no organization_id"
    column = table.columns["organization_id"]
    assert {fk.target_fullname for fk in column.foreign_keys} == {"organizations.id"}
    assert column.nullable == (table_name in NULLABLE_TENANT_TABLES)


@pytest.mark.anyio
async def test_scoped_queries_never_return_other_tenant_rows(db_session: AsyncSession) -> None:
    tenant_a = await make_tenant(db_session, "Alpha", unit_vector(0))
    tenant_b = await make_tenant(db_session, "Beta", unit_vector(1))

    # Every tenant table is covered by the fixture
    assert set(tenant_a.ids) == set(TENANT_TABLES)

    for table_name in TENANT_TABLES:
        table = Base.metadata.tables[table_name]
        scoped_ids = set(
            (await db_session.execute(
                select(table.c.id).where(table.c.organization_id == tenant_a.organization.id)
            )).scalars()
        )
        assert tenant_a.ids[table_name] in scoped_ids, table_name
        assert tenant_b.ids[table_name] not in scoped_ids, f"{table_name} leaked another tenant's row"


@pytest.mark.anyio
async def test_vector_search_never_returns_other_tenant_chunks(db_session: AsyncSession) -> None:
    query = unit_vector(1)
    tenant_a = await make_tenant(db_session, "Alpha", unit_vector(0))
    # Beta's chunk is an exact match for the query, so it would rank first without the tenant filter
    tenant_b = await make_tenant(db_session, "Beta", query)

    distance = DocumentChunk.embedding.cosine_distance(query)
    scoped = (await db_session.execute(
        select(DocumentChunk.id)
        .where(DocumentChunk.organization_id == tenant_a.organization.id)
        .order_by(distance)
        .limit(5)
    )).scalars().all()
    unscoped_top = (await db_session.execute(
        select(DocumentChunk.id)
        .where(DocumentChunk.organization_id.in_([tenant_a.organization.id, tenant_b.organization.id]))
        .order_by(distance)
        .limit(1)
    )).scalar_one()

    assert unscoped_top == tenant_b.ids["document_chunks"]  # the filter is what prevents the leak
    assert scoped == [tenant_a.ids["document_chunks"]]


@pytest.mark.anyio
async def test_customer_search_excludes_internal_chunks(db_session: AsyncSession) -> None:
    tenant = await make_tenant(db_session, "Alpha", unit_vector(0))
    public_chunk = await db_session.get(DocumentChunk, tenant.ids["document_chunks"])
    internal_chunk = DocumentChunk(
        organization_id=tenant.organization.id,
        document_id=public_chunk.document_id,
        chunk_index=1,
        content="internal escalation rule",
        embedding=unit_vector(0),
        source_type=public_chunk.source_type,
        access_level=DocumentAccessLevel.INTERNAL,
    )
    db_session.add(internal_chunk)
    await db_session.flush()

    customer_visible = (await db_session.execute(
        select(DocumentChunk.id).where(
            DocumentChunk.organization_id == tenant.organization.id,
            DocumentChunk.access_level == DocumentAccessLevel.PUBLIC,
        )
    )).scalars().all()

    assert customer_visible == [public_chunk.id]


@pytest.mark.anyio
async def test_deleting_an_organization_leaves_other_tenants_intact(db_session: AsyncSession) -> None:
    tenant_a = await make_tenant(db_session, "Alpha", unit_vector(0))
    tenant_b = await make_tenant(db_session, "Beta", unit_vector(1))

    await db_session.delete(await db_session.get(Organization, tenant_b.organization.id))
    await db_session.flush()
    db_session.expunge_all()

    for table_name in TENANT_TABLES:
        table = Base.metadata.tables[table_name]
        remaining = (await db_session.execute(
            select(func.count()).select_from(table).where(table.c.id.in_([tenant_a.ids[table_name], tenant_b.ids[table_name]]))
        )).scalar_one()
        # Alpha's row stays; Beta's row is deleted, except the audit log, which is kept
        expected = 2 if table_name in NULLABLE_TENANT_TABLES else 1
        assert remaining == expected, table_name

    beta_audit = await db_session.get(AuditLog, tenant_b.ids["audit_logs"])
    assert beta_audit.organization_id is None
