import json
import time
import httpx
import hmac
import hashlib
from app.config import settings


def generate_sig(body: bytes, key: str) -> str:
    sig = hmac.new(key.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def seed_multiple_rules(target_url: str = "https://linkplease-ttp8.onrender.com"):
    print(f"Seeding multiple rules and events to {target_url}...")
    
    rules = [
        {"keyword": "PRICE", "dm_message": "Here is our full pricing catalog: https://example.com/pricing. Use code WELCOME10 for 10% off!"},
        {"keyword": "LINK", "dm_message": "Access the link to our latest course here: https://example.com/course"},
        {"keyword": "DISCOUNT", "dm_message": "Exclusive 25% discount code: SAVE25. Valid for the next 24 hours!"},
        {"keyword": "DEMO", "dm_message": "Book your live 1-on-1 demo call here: https://example.com/demo"},
        {"keyword": "INFO", "dm_message": "Here are all product specifications and brochure: https://example.com/info"},
    ]

    events_data = [
        {"user_id": "usr_alice_1", "username": "alice_tech", "text": "Can you send me the PRICE list please?"},
        {"user_id": "usr_bob_2", "username": "bob_builder", "text": "I need the LINK to join the webinar!"},
        {"user_id": "usr_charlie_3", "username": "charlie_dev", "text": "Any DISCOUNT code available today?"},
        {"user_id": "usr_david_4", "username": "david_fitness", "text": "Would love to see a DEMO of this tool!"},
        {"user_id": "usr_emma_5", "username": "emma_design", "text": "Please DM me more INFO about this product!"},
        {"user_id": "usr_frank_6", "username": "frank_creator", "text": "What is the PRICE?"},
        {"user_id": "usr_grace_7", "username": "grace_art", "text": "Send DISCOUNT details!"},
    ]

    with httpx.Client(timeout=15.0) as client:
        # 1. Create Rules
        print("\nCreating 5 Keyword Automation Rules...")
        for r in rules:
            res = client.post(f"{target_url}/rules", json=r)
            print(f"Rule [{r['keyword']}]:", res.status_code, res.text)
            time.sleep(0.3)

        # 2. Dispatch Comment Events
        print("\nDispatching 7 Comment Webhook Events...")
        for i, item in enumerate(events_data):
            payload = {
                "event_id": f"evt_prod_{i}_{int(time.time())}",
                "event_type": "comment.created",
                "sent_at": "2026-08-16T23:00:00.000Z",
                "data": {
                    "comment_id": f"cmt_prod_{i}_{int(time.time())}",
                    "post_id": "post_instagram_101",
                    "text": item["text"],
                    "created_at": "2026-08-16T23:00:00.000Z",
                    "from": {
                        "user_id": item["user_id"],
                        "username": item["username"]
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
            print(f"Event [{item['username']} - '{item['text']}']:", res.status_code)
            time.sleep(0.4)

        # 3. Print Final Live Stats
        print("\nFetching Live Server Stats...")
        s_res = client.get(f"{target_url}/stats")
        print("Live Stats Output:", s_res.json())


if __name__ == "__main__":
    seed_multiple_rules()
