#!/usr/bin/env python3
"""
End-to-end test for Claude AI training exercises pipeline.
Tests the full flow: design -> run -> verify HTML output
"""
import asyncio
import json
import sys
import websockets
from datetime import datetime

BASE_WS = "wss://agentmaster-ouabviezcq-ew.a.run.app"
BASE_HTTP = "https://agentmaster-ouabviezcq-ew.a.run.app"

# Read pipeline ID from file
with open('/tmp/new_pipeline_id.txt', 'r') as f:
    PIPELINE_ID = f.read().strip()

# Track what we see
design_complete = False
agents_designed = []
run_complete = False
html_output = None


def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


async def test_design_phase():
    """Connect to design WebSocket and verify agents are created correctly."""
    global design_complete, agents_designed

    print_section("PHASE 1: DESIGN - Generating Agents")

    url = f"{BASE_WS}/ws/design/{PIPELINE_ID}"
    print(f"Connecting to: {url}")

    try:
        async with websockets.connect(url, ping_timeout=300, open_timeout=30) as ws:
            event_count = 0
            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=600)
                    event = json.loads(raw)
                    event_type = event.get("type", "")
                    data = event.get("data", event)
                    event_count += 1

                    if event_type == "DESIGN_STARTED":
                        print(f"\n✓ Design started for: {data.get('objective', '')[:100]}...")

                    elif event_type == "BLUEPRINT_READY":
                        blueprint = data.get("blueprint", {})
                        
                        # Check if out of scope
                        if blueprint.get("out_of_scope"):
                            print(f"\n✗ REJECTED AS OUT OF SCOPE!")
                            print(f"   Reason: {blueprint.get('reason', 'Unknown')}")
                            return False
                        
                        agents = blueprint.get("agents", [])
                        print(f"\n✓ Blueprint ready with {len(agents)} agents:")
                        for i, agent in enumerate(agents, 1):
                            agent_name = agent.get("agent_name", "")
                            agent_desc = agent.get("description", "")
                            print(f"  {i}. {agent_name}")
                            print(f"     → {agent_desc}")
                            agents_designed.append({"name": agent_name, "desc": agent_desc})

                    elif event_type == "AGENT_STARTED":
                        agent_name = data.get("agent_name", "")
                        print(f"  [STARTED] {agent_name}")

                    elif event_type == "DESIGN_COMPLETE":
                        agent_count = data.get("agent_count", 0)
                        approved = data.get("approved_count", 0)
                        print(f"\n✓ Design complete: {approved}/{agent_count} agents approved")
                        design_complete = True
                        break

                    elif event_type == "ERROR":
                        print(f"\n✗ ERROR: {data.get('message', 'Unknown error')}")
                        return False

                except asyncio.TimeoutError:
                    print(f"\n✗ Timeout waiting for design events (received {event_count} events)")
                    return False

    except Exception as e:
        print(f"\n✗ Design phase failed: {e}")
        return False

    return design_complete


async def test_run_phase():
    """Create and execute a run, capture the HTML output."""
    global run_complete, html_output

    print_section("PHASE 2: RUN - Executing Pipeline")

    # Create run via HTTP
    import urllib.request
    import urllib.error

    create_run_url = f"{BASE_HTTP}/api/runs"
    create_run_data = json.dumps({
        "pipeline_id": PIPELINE_ID,
        "inputs": {}
    }).encode('utf-8')

    req = urllib.request.Request(
        create_run_url,
        data=create_run_data,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req) as response:
            run_data = json.loads(response.read().decode('utf-8'))
            run_id = run_data.get("id")
            print(f"✓ Run created: {run_id}")
    except urllib.error.URLError as e:
        print(f"✗ Failed to create run: {e}")
        return False

    # Connect to run WebSocket
    url = f"{BASE_WS}/ws/run/{run_id}"
    print(f"Connecting to: {url}")

    try:
        async with websockets.connect(url, ping_timeout=300, open_timeout=30) as ws:
            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=600)
                    event = json.loads(raw)
                    event_type = event.get("type", "")
                    data = event.get("data", event)

                    if event_type == "RUN_STARTED":
                        print(f"✓ Run started")

                    elif event_type == "AGENT_RESULT":
                        agent_name = data.get("agent_name", "")
                        status = data.get("status", "")
                        output = data.get("output", {})

                        # Look for HTML output
                        if "formatted_output" in output:
                            html_output = output["formatted_output"]
                            html_len = len(html_output)
                            print(f"  [RESULT] {agent_name} - {status}")
                            print(f"           → HTML output captured ({html_len} chars)")
                        else:
                            print(f"  [RESULT] {agent_name} - {status}")

                    elif event_type == "RUN_COMPLETE":
                        print(f"\n✓ Run complete")
                        run_complete = True
                        break

                    elif event_type == "ERROR":
                        print(f"\n✗ ERROR: {data.get('message', 'Unknown error')}")
                        return False

                except asyncio.TimeoutError:
                    print(f"\n✗ Timeout waiting for run events")
                    return False

    except Exception as e:
        print(f"\n✗ Run phase failed: {e}")
        return False

    return run_complete


def verify_html_output():
    """Verify the HTML contains Claude AI training exercises."""
    print_section("PHASE 3: VERIFICATION - Checking HTML Output")

    if not html_output:
        print("✗ No HTML output found!")
        return False

    # Check for HTML structure
    has_html_tag = "<html" in html_output.lower()
    has_body_tag = "<body" in html_output.lower()
    has_title = "<title" in html_output.lower()

    print(f"HTML Structure:")
    print(f"  ✓ Has <html> tag: {has_html_tag}")
    print(f"  ✓ Has <body> tag: {has_body_tag}")
    print(f"  ✓ Has <title> tag: {has_title}")

    # Check for Claude-specific content
    claude_mentions = html_output.lower().count("claude")
    prompt_mentions = html_output.lower().count("prompt")
    ai_mentions = html_output.lower().count("ai")

    print(f"\nClaude AI Content:")
    print(f"  • Mentions 'Claude': {claude_mentions} times")
    print(f"  • Mentions 'prompt': {prompt_mentions} times")
    print(f"  • Mentions 'AI': {ai_mentions} times")

    # Check for exercises
    import re
    h3_tags = re.findall(r'<h3[^>]*>([^<]+)</h3>', html_output, re.IGNORECASE)
    exercise_count = len(h3_tags)

    print(f"\nExercises Found: {exercise_count}")
    if h3_tags:
        print("  Exercise Titles:")
        for i, title in enumerate(h3_tags[:10], 1):
            print(f"    {i}. {title.strip()}")

    # Validation
    is_valid = (
        has_html_tag and
        has_body_tag and
        claude_mentions >= 5 and
        exercise_count >= 8  # Allow some flexibility
    )

    if is_valid:
        print(f"\n✓ HTML output is VALID - contains Claude AI training exercises")

        # Save to file
        output_file = f"claude_training_exercises_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_output)
        print(f"✓ Saved to: {output_file}")

        return True
    else:
        print(f"\n✗ HTML output is INVALID")
        if claude_mentions < 5:
            print(f"  - Not enough Claude mentions (found {claude_mentions}, expected >= 5)")
        if exercise_count < 8:
            print(f"  - Not enough exercises (found {exercise_count}, expected >= 8)")

        # Save for debugging anyway
        debug_file = f"debug_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(html_output if html_output else "No output")
        print(f"  Saved debug output to: {debug_file}")

        return False


async def main():
    """Run full end-to-end test."""
    print("=" * 80)
    print("  CLAUDE AI TRAINING EXERCISES - END-TO-END TEST")
    print("=" * 80)
    print(f"  Pipeline ID: {PIPELINE_ID}")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Phase 1: Design
    design_success = await test_design_phase()
    if not design_success:
        print("\n✗ FAILED at design phase")
        sys.exit(1)

    # Phase 2: Run
    run_success = await test_run_phase()
    if not run_success:
        print("\n✗ FAILED at run phase")
        sys.exit(1)

    # Phase 3: Verify
    verify_success = verify_html_output()
    if not verify_success:
        print("\n✗ FAILED at verification phase")
        sys.exit(1)

    # Success!
    print_section("TEST COMPLETE - ALL PHASES PASSED ✓")
    print(f"\nAgents Designed: {len(agents_designed)}")
    for agent in agents_designed:
        print(f"  • {agent['name']}")
    print(f"\nHTML Output: {len(html_output) if html_output else 0} characters")
    print(f"Ready for deployment!")

    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
