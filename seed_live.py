import json
import time
import httpx
import hmac
import hashlib
from app.config import settings


def generate_sig(body: bytes, key: str) -> str:
    sig = hmac.new(key.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def seed_live_data(target_url: str = "https://linkplease-ttp8.onrender.com"):
    print(f"Seeding live data to {target_url}...")
    with httpx.Client(timeout=15.0) as client:
        # 1. Create Rule
        print("Creating Rule: PRICE...")
        r_res = client.post(
            f"{target_url}/rules",
            json={"keyword": "PRICE", "dm_message": "Here's the price list: https://example.com/pricing"}
        )
        print("Rule result:", r_res.status_code, r_res.text)

        # 2. Send 5 Comment Created events
        for i in range(5):
            payload = {
                "event_id": f"evt_live_seed_{i}",
                "event_type": "comment.created",
                "sent_at": "2026-08-10T09:14:22.481Z",
                "data": {
                    "comment_id": f"cmt_live_{i}",
                    "post_id": "post_live_1",
                    "text": "PRICE please 🙏" if i % 2 == 0 else "Can I get the price list?",
                    "created_at": "2026-08-10T09:14:21.900Z",
                    "from": {
                        "user_id": f"usr_seed_{i}",
                        "username": f"user_{i}"
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
            print(f"Event {i} result:", res.status_code, res.text)
            time.sleep(0.5)

        # 3. Check stats
        s_res = client.get(f"{target_url}/stats")
        print("\nLive Stats:", s_res.json())


if __name__ == "__main__":
    seed_live_data()
