#!/usr/bin/env python3
"""Final comprehensive test - design + run + verify."""
import asyncio, json, sys, websockets
from datetime import datetime

PIPELINE_ID = "95333310-8143-453d-8e89-c9720c034d3e"
BASE_WS = "wss://agentmaster-ouabviezcq-ew.a.run.app"
BASE_HTTP = "https://agentmaster-ouabviezcq-ew.a.run.app"

async def run_test():
    print("=" * 80)
    print("FINAL E2E TEST - Claude AI Training Exercises")
    print("=" * 80)

    # Step 2: Create and execute run
    print("\n[2/2] RUNNING PIPELINE...")
    import urllib.request

    # Create run
    req_data = json.dumps({"pipeline_id": PIPELINE_ID, "inputs": {}}).encode()
    req = urllib.request.Request(f"{BASE_HTTP}/api/runs", data=req_data,
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        run_id = json.loads(resp.read())["id"]
    print(f"✓ Run created: {run_id}")

    # Execute via WebSocket
    url = f"{BASE_WS}/ws/run/{run_id}"
    html_output = None

    async with websockets.connect(url, ping_timeout=300) as ws:
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=300)
            event = json.loads(raw)
            etype = event.get("type", "")
            data = event.get("data", event)

            if etype == "RUN_STARTED":
                print("✓ Run started")
            elif etype == "AGENT_RESULT":
                name = data.get("agent_name", "")
                status = data.get("status", "")
                output = data.get("output", {})

                if "formatted_output" in output:
                    html_output = output["formatted_output"]
                    print(f"✓ {name} ({status}) - HTML captured ({len(html_output)} chars)")
                else:
                    print(f"✓ {name} ({status})")
            elif etype == "RUN_COMPLETE":
                print("✓ Run complete!")
                break

    # Validate
    print("\n" + "=" * 80)
    print("VALIDATION")
    print("=" * 80)

    if not html_output:
        print("❌ No HTML output")
        return False

    claude_count = html_output.lower().count("claude")
    h3_count = html_output.count("<h3")

    print(f"✓ HTML size: {len(html_output)} characters")
    print(f"✓ 'Claude' mentions: {claude_count}")
    print(f"✓ Exercises (H3 tags): {h3_count}")

    # Save
    filename = f"claude_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(filename, 'w') as f:
        f.write(html_output)
    print(f"\n✅ Saved to: {filename}")

    # Show preview
    print("\nPreview:")
    print(html_output[:500] + "...")

    if claude_count >= 5 and h3_count >= 8:
        print("\n✅ TEST PASSED!")
        return True
    else:
        print(f"\n⚠️  Incomplete: Need ≥5 Claude mentions & ≥8 exercises")
        return False

try:
    result = asyncio.run(run_test())
    sys.exit(0 if result else 1)
except Exception as e:
    print(f"\n❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
