import httpx

async def fetch_page(url: str) -> str:
    """
    Fetch a web page and return its HTML content.
    """

    headers = {
        "User-Agent" : "ACSRP-Documentation-Ingestion/1.0"
    }

    timeout = httpx.Timeout(30)

    async with httpx.AsyncClient(
        headers= headers,
        timeout= timeout,
        follow_redirects= True
    ) as client :
        response = await client.get(url)
        response.raise_for_status()

        return response.text