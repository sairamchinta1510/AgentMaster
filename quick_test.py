#!/usr/bin/env python3
"""Quick test to verify the design phase works."""
import asyncio
import json
import websockets

PIPELINE_ID = open('/tmp/new_pipeline_id.txt').read().strip()
BASE_WS = "wss://agentmaster-ouabviezcq-ew.a.run.app"

async def test():
    url = f"{BASE_WS}/ws/design/{PIPELINE_ID}"
    print(f"Connecting to: {url}")
    print(f"Pipeline ID: {PIPELINE_ID}\n")

    async with websockets.connect(url, ping_timeout=300) as ws:
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=300)
            event = json.loads(raw)
            etype = event.get("type", "")
            data = event.get("data", event)

            if etype == "BLUEPRINT_READY":
                bp = data.get("blueprint", {})

                if bp.get("out_of_scope"):
                    print(f"❌ REJECTED: {bp.get('reason')}")
                    return False

                agents = bp.get("agents", [])
                domain = bp.get("domain", "")

                print(f"✅ ACCEPTED!")
                print(f"Domain: {domain}")
                print(f"Agents: {len(agents)}")
                for i, a in enumerate(agents[:5], 1):
                    print(f"  {i}. {a.get('agent_name')}")
                return True

            elif etype == "DESIGN_COMPLETE":
                print("✅ Design complete!")
                break

            elif etype == "ERROR":
                print(f"❌ Error: {data.get('message')}")
                return False

asyncio.run(test())
