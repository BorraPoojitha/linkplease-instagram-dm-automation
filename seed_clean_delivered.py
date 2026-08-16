import time
import httpx
import json
import hmac
import hashlib
from app.config import settings


def generate_sig(body: bytes, key: str) -> str:
    sig = hmac.new(key.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def seed_clean_delivered(target_url: str = "https://linkplease-ttp8.onrender.com"):
    print(f"Seeding clean delivered jobs to {target_url}...")
    with httpx.Client(timeout=15.0) as client:
        # Create Rule
        client.post(
            f"{target_url}/rules",
            json={"keyword": "DISCOUNT", "dm_message": "Use code SAVE20 for 20% off!"}
        )

        for i in range(3):
            payload = {
                "event_id": f"evt_clean_demo_{i}_{int(time.time())}",
                "event_type": "comment.created",
                "sent_at": "2026-08-16T22:00:00.000Z",
                "data": {
                    "comment_id": f"cmt_clean_{i}_{int(time.time())}",
                    "post_id": "post_demo_1",
                    "text": f"DISCOUNT code please user {i}",
                    "created_at": "2026-08-16T22:00:00.000Z",
                    "from": {
                        "user_id": f"usr_demo_{i}_{int(time.time())}",
                        "username": f"user_demo_{i}"
                    }
                }
            }
            body = json.dumps(payload).encode("utf-8")
            sig = generate_sig(body, settings.PSEUDOGRAM_API_KEY)
            res = client.post(
                f"{target_url}/webhook",
                content=body,
                headers={"X-PseudoGram-Signature": sig, "Content-Type": "application/json"}
            )
            print(f"Clean Event {i} posted:", res.status_code, res.text)
            time.sleep(0.5)

        s_res = client.get(f"{target_url}/stats")
        print("\nUpdated Stats:", s_res.json())


if __name__ == "__main__":
    seed_clean_delivered()
