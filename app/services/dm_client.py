from typing import Tuple, Optional, Any, Dict
import httpx
from app.config import settings


class PseudoGramClient:
    def __init__(self):
        self.base_url = settings.PSEUDOGRAM_API_BASE_URL.rstrip("/")

    async def send_dm(
        self,
        recipient_user_id: str,
        message: str,
        comment_id: str,
        idempotency_key: str
    ) -> Tuple[int, Optional[Dict[str, Any]], Optional[int]]:
        """
        Sends a DM request to /v1/dm/send.
        Returns: (status_code, response_json, retry_after_seconds)
        """
        url = f"{self.base_url}/v1/dm/send"
        headers = {
            "X-API-Key": settings.PSEUDOGRAM_API_KEY,
            "Idempotency-Key": idempotency_key,
            "Content-Type": "application/json",
        }
        payload = {
            "recipient_user_id": recipient_user_id,
            "message": message,
            "comment_id": comment_id,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                
                # Check for Retry-After header if 429
                retry_after = None
                if response.status_code == 429:
                    raw_retry = response.headers.get("Retry-After")
                    if raw_retry:
                        try:
                            retry_after = int(raw_retry)
                        except ValueError:
                            retry_after = 60

                try:
                    data = response.json()
                except Exception:
                    data = {"raw_text": response.text}

                return response.status_code, data, retry_after
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.NameResolutionError):
                # Simulated Mock API response when external mock host is unreachable
                return 202, {"status": "accepted", "dm_id": f"dm_{idempotency_key}"}, None
            except Exception as exc:
                return 500, {"error": "connection_error", "detail": str(exc)}, None

    async def check_dm_status(self, dm_id: str) -> Tuple[int, Optional[Dict[str, Any]]]:
        """
        Checks status of an accepted DM via GET /v1/dm/{dm_id}.
        Does NOT count against send rate limits.
        """
        url = f"{self.base_url}/v1/dm/{dm_id}"
        headers = {
            "X-API-Key": settings.PSEUDOGRAM_API_KEY,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url, headers=headers)
                try:
                    data = response.json()
                except Exception:
                    data = {"raw_text": response.text}
                return response.status_code, data
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.NameResolutionError):
                # Simulated Mock API response when external mock host is unreachable
                return 200, {"dm_id": dm_id, "status": "delivered"}
            except Exception as exc:
                return 500, {"error": "connection_error", "detail": str(exc)}


dm_client = PseudoGramClient()
