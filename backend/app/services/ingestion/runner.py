import asyncio
import re
from pathlib import Path

from sqlalchemy import select

from app.db.session import asyncSessionLocal, engine
from app.models.document import (
    DocumentAccessLevel,
    DocumentSourceType,
)
from app.models.knowledge_source import KnowledgeSource
from app.models.organization import Organization
from app.services.ingestion.pipeline import ingest_cleaned_document, ingest_url

ORGANIZATION_NAME = "Acme Software"

GITLAB_SOURCE_NAME = "GitLab Documentation"
POLICY_SOURCE_NAME = "Support Policies"

GITLAB_SOURCE_URL = "https://docs.gitlab.com"

# runner.py -> ingestion -> services -> app -> backend -> repository root
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
SUPPORT_DOCS_DIR = REPOSITORY_ROOT / "data" / "support_docs"


GITLAB_DOCUMENTS = [
    {
        "url": "https://docs.gitlab.com/user/permissions/",
        "source_type": DocumentSourceType.PRODUCT_DOCS,
    },
    {
        "url": "https://docs.gitlab.com/user/project/members/",
        "source_type": DocumentSourceType.PRODUCT_DOCS,
    },
    {
        "url": "https://docs.gitlab.com/user/profile/account/two_factor_authentication/",
        "source_type": DocumentSourceType.PRODUCT_DOCS,
    },
    {
        "url": "https://docs.gitlab.com/ci/jobs/job_troubleshooting/",
        "source_type": DocumentSourceType.TROUBLESHOOTING,
    },
    {
        "url": "https://docs.gitlab.com/user/packages/container_registry/troubleshoot_container_registry/",
        "source_type": DocumentSourceType.TROUBLESHOOTING,
    },
    {
        "url": "https://docs.gitlab.com/user/project/settings/",
        "source_type": DocumentSourceType.PRODUCT_DOCS,
    },
]


GENERATED_DOCUMENTS = {
    "01_support_escalation_policy.md": (
        DocumentSourceType.INTERNAL_POLICY,
        DocumentAccessLevel.INTERNAL,
    ),
    "02_response_quality_policy.md": (
        DocumentSourceType.INTERNAL_POLICY,
        DocumentAccessLevel.INTERNAL,
    ),
    "03_sensitive_actions_policy.md": (
        DocumentSourceType.INTERNAL_POLICY,
        DocumentAccessLevel.INTERNAL,
    ),
    "04_customer_communication_guidelines.md": (
        DocumentSourceType.INTERNAL_POLICY,
        DocumentAccessLevel.INTERNAL,
    ),
    "05_ticket_handling_workflow.md": (
        DocumentSourceType.INTERNAL_POLICY,
        DocumentAccessLevel.INTERNAL,
    ),
    "06_known_issues.md": (
        DocumentSourceType.TROUBLESHOOTING,
        DocumentAccessLevel.INTERNAL,
    ),
    "07_faq.md": (
        DocumentSourceType.FAQ,
        DocumentAccessLevel.PUBLIC,
    ),
    "08_historical_ticket_TKT-0001.md": (
        DocumentSourceType.HISTORICAL_TICKET,
        DocumentAccessLevel.INTERNAL,
    ),
    "09_historical_ticket_TKT-0002.md": (
        DocumentSourceType.HISTORICAL_TICKET,
        DocumentAccessLevel.INTERNAL,
    ),
    "10_historical_ticket_TKT-0003.md": (
        DocumentSourceType.HISTORICAL_TICKET,
        DocumentAccessLevel.INTERNAL,
    ),
    "11_historical_ticket_TKT-0004.md": (
        DocumentSourceType.HISTORICAL_TICKET,
        DocumentAccessLevel.INTERNAL,
    ),
    "12_historical_ticket_TKT-0005.md": (
        DocumentSourceType.HISTORICAL_TICKET,
        DocumentAccessLevel.INTERNAL,
    ),
    "13_historical_ticket_TKT-0006.md": (
        DocumentSourceType.HISTORICAL_TICKET,
        DocumentAccessLevel.INTERNAL,
    ),
}


def extract_markdown_title(content: str, filename: str) -> str:
    """Extract the first H1 heading, falling back to the filename."""

    for line in content.splitlines():
        match = re.match(r"^#\s+(.+)$", line.strip())

        if match:
            return match.group(1).strip()

    return Path(filename).stem.replace("_", " ").title()


async def get_or_create_source(
    session,
    organization_id,
    name: str,
    description: str,
    url: str | None,
):
    source = await session.scalar(
        select(KnowledgeSource).where(
            KnowledgeSource.organization_id == organization_id,
            KnowledgeSource.name == name,
        )
    )

    if source is None:
        source = KnowledgeSource(
            organization_id=organization_id,
            name=name,
            description=description,
            url=url,
        )
        session.add(source)
        await session.flush()

    return source


async def main():
    failures = []

    try:
        async with asyncSessionLocal() as session:
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

            gitlab_source = await get_or_create_source(
                session,
                organization.id,
                GITLAB_SOURCE_NAME,
                "Official public GitLab documentation.",
                GITLAB_SOURCE_URL,
            )

            policy_source = await get_or_create_source(
                session,
                organization.id,
                POLICY_SOURCE_NAME,
                "Internal support policies and generated support knowledge.",
                None,
            )

            await session.commit()

            # Each document is committed on its own, so one failure doesn't stop the run.
            for spec in GITLAB_DOCUMENTS:
                try:
                    async with session.begin():
                        result = await ingest_url(
                            session=session,
                            organization_id=organization.id,
                            knowledge_source_id=gitlab_source.id,
                            url=spec["url"],
                            source_type=spec["source_type"],
                            access_level=DocumentAccessLevel.PUBLIC,
                            product="GitLab",
                        )
                except Exception as error:
                    failures.append(spec["url"])
                    print(f"FAILED GitLab: {spec['url']}: {error!r}")
                    continue

                print(f"GitLab: {spec['url']}")
                print(result)

            for filename, (source_type, access_level) in GENERATED_DOCUMENTS.items():
                file_path = SUPPORT_DOCS_DIR / filename

                if not file_path.is_file():
                    failures.append(filename)
                    print(f"SKIPPED: File not found: {file_path}")
                    continue

                content = file_path.read_text(encoding="utf-8")
                title = extract_markdown_title(content, filename)

                try:
                    async with session.begin():
                        result = await ingest_cleaned_document(
                            session=session,
                            organization_id=organization.id,
                            knowledge_source_id=policy_source.id,
                            title=title,
                            content=content,
                            source_type=source_type,
                            access_level=access_level,
                            product="GitLab",
                        )
                except Exception as error:
                    failures.append(filename)
                    print(f"FAILED Markdown: {filename}: {error!r}")
                    continue

                print(f"Markdown: {filename}")
                print(result)

    finally:
        await engine.dispose()

    if failures:
        print(f"{len(failures)} document(s) not ingested: {failures}")


if __name__ == "__main__":
    asyncio.run(main())
