from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_into_chunks(
        content : str,
        chunk_size : int = 500,
        chunk_overlap :int = 50
) -> list[dict]:
    """
    Split document content into overlapping, token-aware chunks.
    """

    if not content.split():
        return []

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")
     
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base",
        chunk_size = chunk_size,
        chunk_overlap = chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    text_chunks = splitter.split_text(content)

    return [
        {
            "chunk_index" : index,
            "content" : chunk
        }
        for index, chunk in enumerate(text_chunks)
    ]
