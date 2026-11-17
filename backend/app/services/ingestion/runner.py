
import asyncio

from sqlalchemy import select

from app.db.session import asyncSessionLocal, engine
from app.models.organization import Organization
from app.models.knowledge_source import KnowledgeSource
from app.models.document import (
    DocumentAccessLevel,
    DocumentSourceType,
)

from app.services.ingestion.pipeline import ingest_url


ORGANIZATION_NAME = "Acronis"

SOURCE_NAME = "GitLab Documentation"
SOURCE_URL = "https://docs.gitlab.com"

DOCUMENT_URL = "https://docs.gitlab.com/user/permissions/"


async def main():
    try:
        async with asyncSessionLocal() as session:
            async with session.begin():

                # Find the organization that owns the documents.
                organization = await session.scalar(
                    select(Organization).where(
                        Organization.name == ORGANIZATION_NAME
                    )
                )

                if organization is None:
                    raise ValueError(
                        f"Organization '{ORGANIZATION_NAME}' not found. "
                        "Run the database seed script first."
                    )

                # Find or create the GitLab knowledge source.
                source = await session.scalar(
                    select(KnowledgeSource).where(
                        KnowledgeSource.organization_id == organization.id,
                        KnowledgeSource.name == SOURCE_NAME,
                    )
                )

                if source is None:
                    source = KnowledgeSource(
                        organization_id=organization.id,
                        name=SOURCE_NAME,
                        description="Official public GitLab documentation.",
                        url=SOURCE_URL,
                    )

                    session.add(source)
                    await session.flush()

                # Fetch, clean, chunk, embed and store the document.
                result = await ingest_url(
                    session=session,
                    organization_id=organization.id,
                    knowledge_source_id=source.id,
                    url=DOCUMENT_URL,
                    source_type=DocumentSourceType.PRODUCT_DOCS,
                    access_level=DocumentAccessLevel.PUBLIC,
                    product="GitLab",
                )

                print("Ingestion result:")
                print(result)

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
