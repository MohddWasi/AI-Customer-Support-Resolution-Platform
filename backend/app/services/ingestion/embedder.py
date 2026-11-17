from urllib import response

from openai import AsyncOpenAI, api_key
from app.core.config import settings
from app.models.document_chunk import EMBEDDING_DIMENSIONS
MODEL_NAME = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536

client = AsyncOpenAI(
    api_key = settings.OPENAI_API_KEY
)

async def generate_embeddings(
        text : list[str]
) -> list[list[float]]:
     """
    Generate embeddings for a list of text chunks.
    """
     
     if not text:
          return []

     response = await client.embeddings.create(
          model=MODEL_NAME,
          dimensions=EMBEDDING_DIMENSIONS,
          input=text
     )

     return [
          item.embedding
          for item in response.data
     ]



     
