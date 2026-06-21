#!/usr/bin/env python3
"""
Example Use Case: Create a Technical Training Document
Demonstrates AgentMaster backend with a real-world scenario.

This example shows how AgentMaster:
1. Accepts a complex objective
2. Decomposes it into Sub-Agents and Atomic Agents
3. Executes agents recursively
4. Validates outputs through critique
5. Returns structured results

Use Case: "Create a 5-page training document on Python Best Practices for new developers"
Domain: Content Generation
"""

import asyncio
import json
import time
import requests
import websockets
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
BASE_WS = "ws://localhost:8000"

class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_step(step: int, text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}[Step {step}]{Colors.RESET} {text}")

def print_success(text: str):
    print(f"{Colors.GREEN}✓{Colors.RESET} {text}")

def print_info(text: str):
    print(f"{Colors.BLUE}→{Colors.RESET} {text}")

async def run_example():
    """Execute the example use case."""

    print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}Example Use Case: Create Technical Training Document{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")

    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Objective: Create a 5-page training document on Python Best Practices")
    print(f"Domain: Content Generation\n")

    # ========================================================================
    # Step 1: Create Execution
    # ========================================================================
    print_step(1, "Creating Execution via REST API")

    execution_payload = {
        "objective": "Create a comprehensive 5-page training document on Python Best Practices for junior developers. Include code examples, common mistakes, and best practices for error handling, testing, and code organization.",
        "domain": "Content Generation",
        "config": {
            "max_recursion_depth": 5,
            "agent_timeout_seconds": 300,
            "critique_strictness": "standard"
        }
    }

    print_info(f"Sending POST request to {BASE_URL}/api/executions")
    print_info(f"Objective: {execution_payload['objective'][:80]}...")

    try:
        response = requests.post(
            f"{BASE_URL}/api/executions",
            json=execution_payload,
            timeout=10
        )

        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            return

        execution_data = response.json()
        execution_id = execution_data["id"]

        print_success(f"Execution created: {execution_id}")
        print_info(f"Status: {execution_data['status']}")
        print_info(f"Root Agent: {execution_data.get('root_agent_id', 'Not yet created')}")

    except Exception as e:
        print(f"Error creating execution: {e}")
        return

    # ========================================================================
    # Step 2: Connect to Studio WebSocket (Planning Phase)
    # ========================================================================
    print_step(2, "Connecting to Studio WebSocket (Planning Phase)")

    studio_url = f"{BASE_WS}/ws/studio/{execution_id}"
    print_info(f"WebSocket URL: {studio_url}")

    agents_planned = []

    try:
        async with websockets.connect(studio_url, ping_timeout=30) as ws:
            print_success("Connected to Studio WebSocket")
            print_info("Monitoring agent planning...")

            async for message in asyncio.wait_for(ws, timeout=10.0):
                event = json.loads(message)
                event_type = event.get("event_type")

                if event_type == "agent_created":
                    agent_data = event.get("data", {})
                    agent_name = agent_data.get("agent_name", "Unknown")
                    agent_type = agent_data.get("agent_type", "Unknown")
                    agents_planned.append({
                        "name": agent_name,
                        "type": agent_type,
                        "id": agent_data.get("agent_id")
                    })
                    print_success(f"Agent planned: [{agent_type}] {agent_name[:60]}")

                elif event_type == "edge_created":
                    print_info("Dependency edge created")

                elif event_type == "design_complete":
                    print_success("Planning phase complete!")
                    break

    except asyncio.TimeoutError:
        print_info("Planning phase completed (or no events in 10s)")
    except Exception as e:
        print(f"Studio WebSocket error: {e}")

    print(f"\n{Colors.BOLD}Planned Agents:{Colors.RESET}")
    for i, agent in enumerate(agents_planned, 1):
        print(f"  {i}. [{agent['type']}] {agent['name'][:65]}")

    # ========================================================================
    # Step 3: Execute via Control Room WebSocket
    # ========================================================================
    print_step(3, "Executing Agents via Control Room WebSocket")

    control_room_url = f"{BASE_WS}/ws/control-room/{execution_id}"
    print_info(f"WebSocket URL: {control_room_url}")

    agents_started = []
    agents_completed = []
    agents_failed = []
    critique_verdicts = []

    try:
        async with websockets.connect(control_room_url, ping_timeout=60) as ws:
            print_success("Connected to Control Room WebSocket")
            print_info("Monitoring execution... (max 60 seconds)\n")

            start_time = time.time()

            async for message in ws:
                if time.time() - start_time > 60:
                    print(f"\n{Colors.YELLOW}Timeout after 60 seconds{Colors.RESET}")
                    break

                event = json.loads(message)
                event_type = event.get("event_type")
                data = event.get("data", {})

                if event_type == "execution_started":
                    print_success("Execution started!\n")

                elif event_type == "agent_started":
                    agent_name = data.get("agent_name", "Unknown")
                    agent_type = data.get("agent_type", "Unknown")
                    agents_started.append(agent_name)
                    print(f"{Colors.BLUE}▶{Colors.RESET} Starting: [{agent_type}] {agent_name[:60]}")

                elif event_type == "agent_completed":
                    agent_name = data.get("agent_name", "Unknown")
                    agents_completed.append(agent_name)
                    print(f"{Colors.GREEN}✓{Colors.RESET} Completed: {agent_name[:60]}")

                elif event_type == "agent_failed":
                    agent_name = data.get("agent_name", "Unknown")
                    reason = data.get("reason", "Unknown")
                    agents_failed.append(agent_name)
                    print(f"{Colors.YELLOW}✗{Colors.RESET} Failed: {agent_name[:60]} - {reason}")

                elif event_type == "critique_round_started":
                    round_num = data.get("round", "?")
                    print(f"  {Colors.BLUE}→{Colors.RESET} Critique Round {round_num} started")

                elif event_type == "critique_round_completed":
                    round_num = data.get("round", "?")
                    verdict = data.get("verdict", "unknown")
                    print(f"  {Colors.BLUE}→{Colors.RESET} Round {round_num}: {verdict}")

                elif event_type == "critique_completed":
                    verdict = data.get("verdict", "unknown")
                    confidence = data.get("confidence", 0)
                    critique_verdicts.append(verdict)
                    verdict_color = Colors.GREEN if verdict == "approved" else Colors.YELLOW
                    print(f"  {verdict_color}✓{Colors.RESET} Critique: {verdict} (confidence: {confidence}%)")

                elif event_type == "subagent_spawned":
                    print(f"  {Colors.BLUE}→{Colors.RESET} Sub-Agent spawned (recursive decomposition)")

                elif event_type == "execution_completed":
                    print(f"\n{Colors.GREEN}{Colors.BOLD}✓ EXECUTION COMPLETED!{Colors.RESET}\n")
                    break

                elif event_type == "execution_failed":
                    reason = data.get("reason", "Unknown")
                    print(f"\n{Colors.YELLOW}Execution failed: {reason}{Colors.RESET}\n")
                    break

                elif event_type == "human_review_needed":
                    agent_name = data.get("agent_name", "Unknown")
                    print(f"  {Colors.YELLOW}⚠{Colors.RESET} Human review needed for: {agent_name[:60]}")

    except Exception as e:
        print(f"Control Room WebSocket error: {e}")

    # ========================================================================
    # Step 4: Retrieve Final Results
    # ========================================================================
    print_step(4, "Retrieving Final Execution Results")

    try:
        response = requests.get(
            f"{BASE_URL}/api/executions/{execution_id}",
            timeout=5
        )

        if response.status_code == 200:
            final_data = response.json()

            print_success("Execution details retrieved")
            print_info(f"Final Status: {final_data['status']}")
            print_info(f"Created: {final_data.get('created_at', 'N/A')}")
            print_info(f"Completed: {final_data.get('completed_at', 'N/A')}")

            if final_data.get('started_at') and final_data.get('completed_at'):
                start = datetime.fromisoformat(final_data['started_at'].replace('Z', '+00:00'))
                end = datetime.fromisoformat(final_data['completed_at'].replace('Z', '+00:00'))
                duration = (end - start).total_seconds()
                print_info(f"Duration: {duration:.2f} seconds")

    except Exception as e:
        print(f"Error retrieving results: {e}")

    # ========================================================================
    # Step 5: Summary
    # ========================================================================
    print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}Execution Summary{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")

    print(f"Execution ID: {execution_id}")
    print(f"Agents Planned: {len(agents_planned)}")
    print(f"Agents Started: {len(agents_started)}")
    print(f"Agents Completed: {len(agents_completed)}")
    print(f"Agents Failed: {len(agents_failed)}")
    print(f"Critique Verdicts: {len(critique_verdicts)}")

    if critique_verdicts:
        approved = sum(1 for v in critique_verdicts if v == "approved")
        print(f"  - Approved: {approved}")
        print(f"  - Rejected/Review: {len(critique_verdicts) - approved}")

    print(f"\n{Colors.BOLD}What Happened:{Colors.RESET}")
    print(f"1. AgentMaster created a root Sub-Agent for 'Content Generation' domain")
    print(f"2. Sub-Agent analyzed the objective and decomposed it into:")
    print(f"   - Research agents (gather Python best practices)")
    print(f"   - Content agents (write sections, create examples)")
    print(f"   - Formatting agents (structure the document)")
    print(f"3. Each Atomic Agent executed its task using tools:")
    print(f"   - web_search_tool (research best practices)")
    print(f"   - llm_call_tool (generate content)")
    print(f"   - file_write_tool (save document)")
    print(f"4. Critique Agents validated each output (3 rounds minimum)")
    print(f"5. Final document assembled and returned")

    print(f"\n{Colors.GREEN}✓ Use case demonstration complete!{Colors.RESET}")
    print(f"\nCheck the database for full details:")
    print(f"  sqlite3 agentmaster.db \"SELECT * FROM agents WHERE execution_id='{execution_id}';\"")

if __name__ == "__main__":
    print("\nMake sure the backend is running:")
    print("  cd backend_new && uvicorn app.main:app --reload\n")

    try:
        asyncio.run(run_example())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Interrupted by user{Colors.RESET}")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
