#!/usr/bin/env python3
"""
Interactive CLI to run tasks with AgentMaster.
Usage: python run_task.py
"""

import asyncio
import json
import sys
import requests
import websockets
from datetime import datetime

BASE_URL = "http://localhost:8000"
BASE_WS = "ws://localhost:8000"

class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{text.center(70)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")

def get_user_input():
    """Get task objective and domain from user."""
    print_header("AGENTMASTER - Run New Task")

    print("Examples of tasks you can run:")
    print("  • Create a technical document or guide")
    print("  • Write a blog post or article")
    print("  • Generate code examples")
    print("  • Create training materials")
    print("  • Write documentation")
    print("")

    objective = input(f"{Colors.BLUE}Enter your objective:{Colors.RESET}\n> ").strip()

    if not objective:
        print(f"{Colors.RED}Objective cannot be empty!{Colors.RESET}")
        sys.exit(1)

    print(f"\n{Colors.BLUE}Enter domain (or press Enter for 'General'):{Colors.RESET}")
    print("  Examples: Content Generation, Documentation, Software Development")
    domain = input("> ").strip() or "General"

    print(f"\n{Colors.BLUE}Max recursion depth (1-5, default 5):{Colors.RESET}")
    depth_input = input("> ").strip()
    max_depth = int(depth_input) if depth_input and depth_input.isdigit() else 5
    max_depth = min(max(max_depth, 1), 5)  # Clamp to 1-5

    return {
        "objective": objective,
        "domain": domain,
        "config": {
            "max_recursion_depth": max_depth,
            "agent_timeout_seconds": 300,
            "critique_strictness": "standard"
        }
    }

async def monitor_execution(execution_id):
    """Monitor execution via WebSocket."""
    url = f"{BASE_WS}/ws/control-room/{execution_id}"

    print(f"\n{Colors.BLUE}Connecting to execution monitor...{Colors.RESET}")

    # Stats tracking
    stats = {
        "agents_planned": 0,
        "sub_agents": 0,
        "atomic_agents": 0,
        "agents_completed": 0,
        "agents_failed": 0,
        "critiques_approved": 0,
        "critiques_rejected": 0,
        "files_created": []
    }

    try:
        async with websockets.connect(url, ping_timeout=120) as ws:
            print(f"{Colors.GREEN}✓ Connected{Colors.RESET}\n")

            async for message in ws:
                event = json.loads(message)
                event_type = event.get("event_type")
                data = event.get("data", {})

                if event_type == "execution_started":
                    print(f"{Colors.GREEN}▶ Execution started - agents are being created and executed...{Colors.RESET}")

                elif event_type == "agent_created":
                    agent_type = data.get("agent_type", "unknown")
                    agent_name = data.get("agent_name", "")[:50]
                    icon = "🔷" if agent_type == "sub_agent" else "⚡"
                    print(f"{Colors.YELLOW}  + Planned: {icon} {agent_type} - {agent_name}...{Colors.RESET}")

                    # Track stats
                    stats["agents_planned"] += 1
                    if agent_type == "sub_agent":
                        stats["sub_agents"] += 1
                    else:
                        stats["atomic_agents"] += 1

                elif event_type == "agent_started":
                    agent_type = data.get("agent_type", "unknown")
                    agent_name = data.get("agent_name", "")[:60]
                    icon = "🔷" if agent_type == "sub_agent" else "⚡"
                    print(f"{Colors.BLUE}{icon} Executing: {agent_name}...{Colors.RESET}")

                elif event_type == "agent_completed":
                    agent_name = data.get("agent_name", "")[:60]
                    print(f"{Colors.GREEN}✓ Completed: {agent_name}{Colors.RESET}")
                    stats["agents_completed"] += 1

                elif event_type == "agent_failed":
                    agent_name = data.get("agent_name", "")[:60]
                    reason = data.get("reason", "Unknown")
                    print(f"{Colors.RED}✗ Failed: {agent_name} - {reason}{Colors.RESET}")
                    stats["agents_failed"] += 1

                elif event_type == "critique_round_started":
                    round_num = data.get("round", "?")
                    print(f"  {Colors.BLUE}  → Validating output (Round {round_num})...{Colors.RESET}")

                elif event_type == "critique_completed":
                    verdict = data.get("verdict")
                    confidence = data.get("confidence", 0)
                    if verdict == "approved":
                        print(f"  {Colors.GREEN}✓ Validation: {verdict} ({confidence}% confidence){Colors.RESET}")
                        stats["critiques_approved"] += 1
                    else:
                        print(f"  {Colors.YELLOW}⚠ Validation: {verdict} ({confidence}% confidence){Colors.RESET}")
                        stats["critiques_rejected"] += 1

                elif event_type == "execution_completed":
                    print(f"\n{Colors.GREEN}{Colors.BOLD}✓ EXECUTION COMPLETED!{Colors.RESET}\n")
                    return stats  # Return stats for final summary

                elif event_type == "execution_failed":
                    reason = data.get("reason", "Unknown")
                    print(f"\n{Colors.RED}Execution failed: {reason}{Colors.RESET}\n")
                    return stats

                elif event_type == "human_review_needed":
                    agent_name = data.get("agent_name", "")[:60]
                    print(f"  {Colors.YELLOW}⚠ Human review needed: {agent_name}{Colors.RESET}")

    except Exception as e:
        print(f"{Colors.RED}Monitor error: {e}{Colors.RESET}")

    return stats  # Return stats even if connection closes

async def main():
    # Get user input
    payload = get_user_input()

    print_header("Submitting Task")
    print(f"Objective: {payload['objective']}")
    print(f"Domain: {payload['domain']}")
    print(f"Max Depth: {payload['config']['max_recursion_depth']}")

    # Create execution
    try:
        response = requests.post(
            f"{BASE_URL}/api/executions",
            json=payload,
            timeout=10
        )

        if response.status_code != 200:
            print(f"{Colors.RED}Error: {response.status_code} - {response.text}{Colors.RESET}")
            return

        data = response.json()
        execution_id = data["id"]

        print(f"\n{Colors.GREEN}✓ Task submitted!{Colors.RESET}")
        print(f"Execution ID: {execution_id}")

    except Exception as e:
        print(f"{Colors.RED}Failed to submit task: {e}{Colors.RESET}")
        return

    # Monitor execution and get stats
    stats = await monitor_execution(execution_id)

    # Get final results
    try:
        response = requests.get(f"{BASE_URL}/api/executions/{execution_id}", timeout=5)
        if response.status_code == 200:
            result = response.json()

            print_header("Execution Summary")

            # Execution details
            print(f"{Colors.BOLD}Execution ID:{Colors.RESET} {execution_id}")
            print(f"{Colors.BOLD}Status:{Colors.RESET} {result['status']}")

            # Timing
            if result.get('created_at') and result.get('completed_at'):
                from datetime import datetime
                start = datetime.fromisoformat(result['created_at'].replace('Z', '+00:00'))
                end = datetime.fromisoformat(result['completed_at'].replace('Z', '+00:00'))
                duration = (end - start).total_seconds()
                print(f"{Colors.BOLD}Duration:{Colors.RESET} {duration:.1f} seconds")

            # Agent statistics
            print(f"\n{Colors.BOLD}Agent Statistics:{Colors.RESET}")
            print(f"  Total Agents Planned: {stats['agents_planned']}")
            print(f"  └─ Sub-Agents (decomposition): {stats['sub_agents']}")
            print(f"  └─ Atomic Agents (execution): {stats['atomic_agents']}")
            print(f"  Completed: {stats['agents_completed']}")
            print(f"  Failed: {stats['agents_failed']}")

            # Critique statistics
            print(f"\n{Colors.BOLD}Validation Results:{Colors.RESET}")
            print(f"  ✅ Approved: {stats['critiques_approved']}")
            print(f"  ❌ Rejected: {stats['critiques_rejected']}")

            # Find created files
            import os
            import glob
            from datetime import datetime, timedelta

            print(f"\n{Colors.BOLD}Created Files:{Colors.RESET}")

            # Look for markdown files created in the last 5 minutes
            now = datetime.now()
            five_min_ago = now - timedelta(minutes=5)

            md_files = glob.glob("*.md")
            recent_files = []

            for f in md_files:
                if os.path.isfile(f):
                    mtime = datetime.fromtimestamp(os.path.getmtime(f))
                    if mtime > five_min_ago:
                        size_kb = os.path.getsize(f) / 1024
                        recent_files.append((f, size_kb, mtime))

            if recent_files:
                # Sort by modification time (newest first)
                recent_files.sort(key=lambda x: x[2], reverse=True)

                for filename, size_kb, mtime in recent_files:
                    abs_path = os.path.abspath(filename)
                    print(f"\n  {Colors.GREEN}📄 {filename}{Colors.RESET}")
                    print(f"     Size: {size_kb:.1f} KB")
                    print(f"     Path: {abs_path}")
                    print(f"     Link: file://{abs_path}")
            else:
                print(f"  {Colors.YELLOW}No new files detected in the last 5 minutes{Colors.RESET}")
                print(f"  Check directory: {os.getcwd()}")

            # API Links
            print(f"\n{Colors.BOLD}API Links:{Colors.RESET}")
            print(f"  Execution Details: {BASE_URL}/api/executions/{execution_id}")
            print(f"  API Documentation: {BASE_URL}/docs")
            print(f"  Studio (Design Mode): {BASE_URL}/ws/studio/{execution_id}")
            print(f"  Control Room (Run Mode): {BASE_URL}/ws/control-room/{execution_id}")

    except Exception as e:
        print(f"{Colors.YELLOW}Could not retrieve final results: {e}{Colors.RESET}")

if __name__ == "__main__":
    print("\nMake sure the backend is running!")
    print("If not, run: cd backend_new && ./start.sh\n")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Cancelled by user{Colors.RESET}")
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
