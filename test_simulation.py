import sys
import json
import time
import asyncio
import httpx
import hmac
import hashlib
from app.config import settings


def generate_sig(body: bytes, key: str) -> str:
    sig = hmac.new(key.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


async def run_local_500_event_simulation(target_url: str = "http://127.0.0.1:8000"):
    print("=" * 60)
    print("STARTING LOCAL 500-EVENT SIMULATION LOAD TEST")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Create a Rule
        print("1. Creating rule: PRICE -> 'Here is the price list: $99'...")
        rule_res = await client.post(
            f"{target_url}/rules",
            json={"keyword": "PRICE", "dm_message": "Here is the price list: $99"}
        )
        print("   Rule creation response:", rule_res.status_code, rule_res.json())

        # 2. Fire 500 webhook events (including duplicate event_ids and duplicate users)
        print("\n2. Dispatching 500 comment events over 10 seconds...")
        events_sent = 0
        duplicate_events = 0
        duplicate_users = 0
        
        start_time = time.time()

        tasks = []
        for i in range(500):
            # Mix of unique & duplicate events
            event_id = f"evt_sim_{i % 300}"  # 200 duplicate event_ids
            user_id = f"usr_sim_{i % 150}"   # 150 unique users commenting multiple times
            comment_id = f"cmt_sim_{i}"

            payload = {
                "event_id": event_id,
                "event_type": "comment.created",
                "sent_at": "2026-08-10T09:14:22.481Z",
                "data": {
                    "comment_id": comment_id,
                    "post_id": "post_sim_1",
                    "text": "PRICE please 🙏" if i % 2 == 0 else "What is the price?",
                    "created_at": "2026-08-10T09:14:21.900Z",
                    "from": {
                        "user_id": user_id,
                        "username": f"user_{i%150}"
                    }
                }
            }

            body = json.dumps(payload).encode("utf-8")
            sig = generate_sig(body, settings.PSEUDOGRAM_API_KEY)
            headers = {
                "X-PseudoGram-Signature": sig,
                "Content-Type": "application/json"
            }

            tasks.append(client.post(f"{target_url}/webhook", content=body, headers=headers))
            events_sent += 1

            if len(tasks) >= 50:
                responses = await asyncio.gather(*tasks)
                tasks = []
                await asyncio.sleep(0.5)  # Spread requests over time

        if tasks:
            await asyncio.gather(*tasks)

        elapsed = time.time() - start_time
        print(f"   Successfully dispatched 500 webhooks in {elapsed:.2f} seconds!")

        # 3. Poll /stats
        print("\n3. Polling /stats until queue settles...")
        for poll in range(15):
            await asyncio.sleep(1.0)
            stats_res = await client.get(f"{target_url}/stats")
            print(f"   [Poll {poll+1}/15] Stats:", stats_res.json())

        print("\n" + "=" * 60)
        print("SIMULATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    asyncio.run(run_local_500_event_simulation(url))
