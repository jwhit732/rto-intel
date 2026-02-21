"""training.gov.au REST API client with rate limiting and error handling."""

import asyncio
import hashlib
import json
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class TGAClient:
    """Async client for training.gov.au REST API."""

    def __init__(
        self,
        base_url: str = "https://training.gov.au/api",
        rate_limit_seconds: float = 1.5,
        max_retries: int = 3,
        timeout: float = 30.0,
    ):
        """Initialize TGA API client.

        Args:
            base_url: Base URL for API
            rate_limit_seconds: Seconds to wait between requests
            max_retries: Max retry attempts for failed requests
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.rate_limit_seconds = rate_limit_seconds
        self.max_retries = max_retries
        self.timeout = timeout
        self._semaphore = asyncio.Semaphore(1)  # One request at a time
        self._last_request_time = 0.0

    async def _throttle(self):
        """Enforce rate limiting between requests."""
        async with self._semaphore:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request_time
            if elapsed < self.rate_limit_seconds:
                await asyncio.sleep(self.rate_limit_seconds - elapsed)
            self._last_request_time = asyncio.get_event_loop().time()

    async def _request(
        self, endpoint: str, rto_code: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Make API request with retry logic.

        Args:
            endpoint: API endpoint path
            rto_code: RTO code for logging context

        Returns:
            JSON response as dict, or None if all retries failed
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        for attempt in range(self.max_retries):
            try:
                await self._throttle()

                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        url, headers={"Accept": "application/json"}
                    )

                    # Success
                    if response.status_code == 200:
                        return response.json()

                    # Not found - permanent error
                    if response.status_code == 404:
                        logger.warning(f"RTO {rto_code}: 404 at {endpoint}")
                        return None

                    # Rate limited or server error - retry
                    if response.status_code in (429, 500, 503):
                        wait_time = 2**attempt  # Exponential backoff
                        logger.warning(
                            f"RTO {rto_code}: HTTP {response.status_code} "
                            f"at {endpoint}, retrying in {wait_time}s "
                            f"(attempt {attempt + 1}/{self.max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    # Other errors - log and skip
                    logger.error(
                        f"RTO {rto_code}: HTTP {response.status_code} "
                        f"at {endpoint}: {response.text[:200]}"
                    )
                    return None

            except httpx.TimeoutException:
                logger.warning(
                    f"RTO {rto_code}: Timeout at {endpoint} "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                return None

            except Exception as e:
                logger.error(f"RTO {rto_code}: Error at {endpoint}: {e}")
                return None

        logger.error(f"RTO {rto_code}: All retries failed for {endpoint}")
        return None

    # Organization endpoints
    async def get_organisation(self, code: str) -> Optional[Dict[str, Any]]:
        """Get organization details."""
        return await self._request(f"organisation/{code}", rto_code=code)

    async def get_scope(self, code: str) -> Optional[Dict[str, Any]]:
        """Get full scope (qualifications and units)."""
        return await self._request(f"organisation/{code}/scope", rto_code=code)

    async def get_scope_summary(self, code: str) -> Optional[Dict[str, Any]]:
        """Get scope summary (lightweight)."""
        return await self._request(f"organisation/{code}/scopesummary", rto_code=code)

    async def get_regulatory_decisions(self, code: str) -> Optional[Dict[str, Any]]:
        """Get regulatory decisions (audit outcomes, compliance)."""
        return await self._request(
            f"organisation/{code}/regulatorydecision", rto_code=code
        )

    async def get_registration(self, code: str) -> Optional[Dict[str, Any]]:
        """Get registration details."""
        return await self._request(f"organisation/{code}/registration", rto_code=code)

    async def get_contacts(self, code: str) -> Optional[Dict[str, Any]]:
        """Get contact information."""
        return await self._request(f"organisation/{code}/contacts", rto_code=code)

    async def get_restrictions(self, code: str) -> Optional[Dict[str, Any]]:
        """Get registration restrictions."""
        return await self._request(f"organisation/{code}/restrictions", rto_code=code)

    # Training component endpoints
    async def get_training_component(self, code: str) -> Optional[Dict[str, Any]]:
        """Get training component details."""
        return await self._request(f"training/{code}", rto_code=code)

    async def get_training_releases(self, code: str) -> Optional[Dict[str, Any]]:
        """Get training component release history."""
        return await self._request(f"training/{code}/releases", rto_code=code)

    # Combined fetch
    async def get_full_rto_data(self, code: str) -> Dict[str, Optional[Dict[str, Any]]]:
        """Fetch all endpoints for an RTO concurrently.

        Args:
            code: RTO code

        Returns:
            Dict with endpoint names as keys and API responses as values
        """
        tasks = {
            "organisation": self.get_organisation(code),
            "scope": self.get_scope(code),
            "regulatory": self.get_regulatory_decisions(code),
            "registration": self.get_registration(code),
            "contacts": self.get_contacts(code),
            "restrictions": self.get_restrictions(code),
        }

        # Run tasks concurrently (rate limiting enforced by _throttle)
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        # Map results back to endpoint names
        data = {}
        for (endpoint, _), result in zip(tasks.items(), results):
            if isinstance(result, Exception):
                logger.error(f"RTO {code}: Exception at {endpoint}: {result}")
                data[endpoint] = None
            else:
                data[endpoint] = result

        return data

    @staticmethod
    def compute_hash(data: Any) -> str:
        """Compute hash of data for change detection.

        Args:
            data: JSON-serializable data

        Returns:
            Hash string
        """
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()
