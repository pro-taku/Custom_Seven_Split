from typing import Any

import httpx
from fastapi.logger import logger


BASE_HAEDER = {
    "Content-Type": "application/json",
    "Accept": "text/plain",
    "charset": "UTF-8",
}


async def _request(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    **kwargs,  # data or params
) -> dict[str, Any]:
    """Helper method for making HTTP requests."""
    if headers is None:
        headers = BASE_HAEDER

    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
            logger.debug(f"Request to {url} successful.")
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
            f" Response body: {e.response.text}",
        )
        raise
    except httpx.RequestError as e:
        logger.error(f"An error occurred while requesting {e.request.url!r}: {e}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise


async def get(
    url: str,
    headers: dict[str, str] | None = None,
    **kwargs,
) -> dict[str, Any]:
    return await _request("GET", url, headers, **kwargs)


async def post(
    url: str,
    headers: dict[str, str] | None = None,
    **kwargs,
) -> dict[str, Any]:
    return await _request("POST", url, headers, **kwargs)


async def put(
    url: str,
    headers: dict[str, str] | None = None,
    **kwargs,
) -> dict[str, Any]:
    return await _request("PUT", url, headers, **kwargs)


async def delete(
    url: str,
    headers: dict[str, str] | None = None,
    **kwargs,
) -> dict[str, Any]:
    return await _request("DELETE", url, headers, **kwargs)
