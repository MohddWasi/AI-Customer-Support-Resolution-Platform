
import hashlib

import tiktoken
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import (
    Document,
    DocumentAccessLevel,
    DocumentSourceType,
)
from app.models.document_chunk import DocumentChunk

from app.services.ingestion.fetcher import fetch_page
from app.services.ingestion.cleaner import clean_html
from app.services.ingestion.chunker import split_into_chunks
from app.services.ingestion.embedder import generate_embeddings


TOKEN_ENCODING = tiktoken.get_encoding("cl100k_base")
EMBEDDING_BATCH_SIZE = 100


async def ingest_cleaned_document(
    session: AsyncSession,
    organization_id,
    knowledge_source_id,
    title: str,
    content: str,
    source_type: DocumentSourceType,
    access_level: DocumentAccessLevel,
    url: str | None = None,
    product: str | None = None,
    version: str | None = None,
) -> dict:
    """
    Store a document and its embedded chunks.

    Unchanged documents are skipped.
    Changed documents have their old chunks replaced.
    """

    if not content.strip():
        raise ValueError("Document content cannot be empty")

    content_hash = hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()

    # Check whether this document already exists.
    document_query = select(Document).where(
        Document.organization_id == organization_id,
        Document.knowledge_source_id == knowledge_source_id,
    )

    if url is not None:
        document_query = document_query.where(Document.url == url)
    else:
        document_query = document_query.where(Document.title == title)

    document = await session.scalar(document_query)

    # Skip documents whose content hasn't changed.
    if document and document.content_hash == content_hash:
        return {
            "status": "skipped",
            "reason": "Document content has not changed",
            "chunks": 0,
        }

    # Split document content.
    chunks = split_into_chunks(content)

    if not chunks:
        raise ValueError("No chunks were generated")

    # Generate embeddings in batches.
    embeddings = []

    for start in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
        batch = chunks[start:start + EMBEDDING_BATCH_SIZE]

        batch_embeddings = await generate_embeddings(
            [chunk["content"] for chunk in batch]
        )

        embeddings.extend(batch_embeddings)

    if len(embeddings) != len(chunks):
        raise ValueError("Embedding count does not match chunk count")

    # Create or update document metadata.
    if document is None:
        document = Document(
            organization_id=organization_id,
            knowledge_source_id=knowledge_source_id,
            title=title,
            url=url,
            source_type=source_type,
            access_level=access_level,
            product=product,
            version=version,
            content_hash=content_hash,
        )

        session.add(document)
        await session.flush()

    else:
        # Remove old chunks before inserting the updated ones.
        await session.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == document.id
            )
        )

        document.url = url
        document.title = title
        document.source_type = source_type
        document.access_level = access_level
        document.product = product
        document.version = version
        document.content_hash = content_hash

        await session.flush()

    # Prepare chunk records.
    chunk_records = []

    for chunk, embedding in zip(chunks, embeddings, strict=True):
        chunk_records.append(
            DocumentChunk(
                organization_id=organization_id,
                document_id=document.id,
                chunk_index=chunk["chunk_index"],
                content=chunk["content"],
                section=None,
                token_count=len(
                    TOKEN_ENCODING.encode(chunk["content"])
                ),
                embedding=embedding,
                source_type=source_type,
                access_level=access_level,
                product=product,
                version=version,
            )
        )

    session.add_all(chunk_records)

    await session.flush()

    return {
        "status": "ingested",
        "document_id": str(document.id),
        "chunks": len(chunk_records),
    }


async def ingest_url(
    session: AsyncSession,
    organization_id,
    knowledge_source_id,
    url: str,
    source_type: DocumentSourceType,
    access_level: DocumentAccessLevel,
    product: str | None = None,
    version: str | None = None,
) -> dict:
    """
    Fetch, clean and ingest an online document.
    """

    html = await fetch_page(url)

    title, content = clean_html(html)

    if not title:
        title = url

    return await ingest_cleaned_document(
        session=session,
        organization_id=organization_id,
        knowledge_source_id=knowledge_source_id,
        title=title,
        content=content,
        source_type=source_type,
        access_level=access_level,
        url=url,
        product=product,
        version=version,
    )
