"""HTTP SERVICE
Perform HTTP requests with logging, error handling & retries support
"""

# # Native # #
import time
from typing import Optional

# # Installed # #
import httpx
from httpx import AsyncResponse

# # Project # #
from vigobusbot.logger import logger

__all__ = ("http_request", "Methods", "AsyncResponse")

DEFAULT_HEADERS = {"Accept-Charset": "UTF-8"}


class Methods:
    GET = "GET"
    POST = "POST"
    DELETE = "DELETE"


async def http_request(
        method: str,
        url: str,
        timeout: float,
        retries: int,
        query_params: Optional[dict] = None,
        body: Optional[dict] = None,
        headers: Optional[dict] = None
) -> httpx.AsyncResponse:
    last_error = None
    headers = {**headers, **DEFAULT_HEADERS} if headers else DEFAULT_HEADERS

    for retry_count in range(retries):
        with logger.contextualize(
            request_method=method,
            request_url=url,
            request_timeout=timeout,
            request_attempt=retry_count+1,
            request_max_attempts=retries,
            request_params=query_params,
            request_body=body,
            request_headers=headers
        ):
            logger.debug("Requesting URL")

            try:
                start_time = time.time()
                async with httpx.AsyncClient(timeout=timeout) as client:
                    if method == Methods.GET:
                        result = await client.get(url=url, params=query_params, headers=headers)
                    elif method == Methods.POST:
                        result = await client.post(url=url, params=query_params, json=body, headers=headers)
                    elif method == Methods.DELETE:
                        result = await client.delete(url=url, params=query_params, headers=headers)

                response_time = round(time.time() - start_time, 4)
                logger.bind(
                    response_elapsed_time=response_time,
                    response_status_code=result.status_code,
                    response_body=result.text
                ).debug("Response received")

                result.raise_for_status()
                result.encoding = "utf-8"
                return result

            except httpx.Timeout as error:
                logger.warning("Request timed out")
                last_error = error

            except httpx.HTTPError as error:
                logger.bind(
                    response_status_code=error.response.status_code,
                    response_body=result.text
                ).warning("Request failed by HTTP Error")
                raise error

            except Exception as error:
                logger.opt(exception=True).warning("Request failed by other error")
                raise error

    raise last_error
