import asyncio
import logging

from backend.app.core.config import settings
from backend.app.core.redis import redis_client


logging.basicConfig(
    level=settings.LOG_LEVEL,
)

logger = logging.getLogger(__name__)


async def main():
    await redis_client.ping()

    logger.info("Worker started")

    while True:
        await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())