import hmac
import hashlib
from fastapi import Request, HTTPException, status
from app.config import settings


def verify_hmac_signature(raw_body: bytes, signature_header: str, secret_key: str) -> bool:
    if not signature_header:
        return False
    
    # Handle optional "sha256=" prefix if present
    expected_sig = signature_header.strip()
    if expected_sig.startswith("sha256="):
        expected_sig = expected_sig[7:]

    computed_sig = hmac.new(
        secret_key.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed_sig, expected_sig)


async def verify_webhook_signature(request: Request) -> bytes:
    signature_header = request.headers.get("X-PseudoGram-Signature")
    if not signature_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-PseudoGram-Signature header"
        )
    
    body = await request.body()
    if not verify_hmac_signature(body, signature_header, settings.PSEUDOGRAM_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HMAC signature"
        )
    
    return body
