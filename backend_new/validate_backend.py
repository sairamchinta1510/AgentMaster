#!/usr/bin/env python3
"""
Backend Validation CLI
Tests AgentMaster backend endpoints and functionality before frontend integration.

Usage:
    python validate_backend.py                    # Full validation
    python validate_backend.py --quick            # Quick health check only
    python validate_backend.py --execution        # Test full execution flow
"""

import asyncio
import json
import sys
import time
from datetime import datetime
import requests
import websockets
from typing import Dict, Any, List

# Configuration
BASE_URL = "http://localhost:8000"
BASE_WS = "ws://localhost:8000"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}✓{Colors.RESET} {text}")

def print_error(text: str):
    print(f"{Colors.RED}✗{Colors.RESET} {text}")

def print_info(text: str):
    print(f"{Colors.BLUE}ℹ{Colors.RESET} {text}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {text}")

def test_health_check() -> bool:
    """Test basic health endpoint."""
    print_header("1. Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Server is healthy: {data}")
            return True
        else:
            print_error(f"Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to server. Is it running?")
        print_info("Start server with: cd backend_new && uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print_error(f"Health check error: {e}")
        return False

def test_create_execution() -> str:
    """Test creating an execution."""
    print_header("2. Create Execution")

    payload = {
        "objective": "Echo 'Hello AgentMaster' to test the system",
        "domain": "Testing",
        "config": {
            "max_recursion_depth": 5,
            "agent_timeout_seconds": 60
        }
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/executions",
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            exec_id = data["id"]
            print_success(f"Execution created: {exec_id}")
            print_info(f"Status: {data['status']}")
            print_info(f"Objective: {data['objective']}")
            print_info(f"Domain: {data['domain']}")
            if data.get('root_agent_id'):
                print_info(f"Root agent: {data['root_agent_id']}")
            return exec_id
        else:
            print_error(f"Failed to create execution: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None
    except Exception as e:
        print_error(f"Create execution error: {e}")
        return None

def test_get_execution(execution_id: str) -> bool:
    """Test retrieving an execution."""
    print_header("3. Get Execution")

    try:
        response = requests.get(
            f"{BASE_URL}/api/executions/{execution_id}",
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            print_success(f"Retrieved execution: {execution_id}")
            print_info(f"Status: {data['status']}")
            print_info(f"Created: {data.get('created_at', 'N/A')}")
            return True
        else:
            print_error(f"Failed to get execution: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Get execution error: {e}")
        return False

async def test_studio_websocket(execution_id: str) -> bool:
    """Test Studio WebSocket connection."""
    print_header("4. Studio WebSocket (Planning Phase)")

    try:
        url = f"{BASE_WS}/ws/studio/{execution_id}"
        print_info(f"Connecting to: {url}")

        async with websockets.connect(url, ping_timeout=10, open_timeout=10) as ws:
            print_success("Connected to Studio WebSocket")

            # Wait for some events (timeout after 5 seconds)
            try:
                event_count = 0
                async for message in asyncio.wait_for(ws, timeout=5.0):
                    event = json.loads(message)
                    event_type = event.get("event_type", "unknown")
                    print_info(f"Event: {event_type}")
                    event_count += 1

                    if event_count >= 3:  # Got some events, that's enough
                        break
            except asyncio.TimeoutError:
                print_warning("No events received in 5 seconds (this is OK if planning complete)")

            print_success("Studio WebSocket test complete")
            return True

    except Exception as e:
        print_error(f"Studio WebSocket error: {e}")
        return False

async def test_control_room_websocket(execution_id: str) -> Dict[str, Any]:
    """Test Control Room WebSocket and monitor execution."""
    print_header("5. Control Room WebSocket (Execution Phase)")

    events_received = []
    agents_completed = []

    try:
        url = f"{BASE_WS}/ws/control-room/{execution_id}"
        print_info(f"Connecting to: {url}")

        async with websockets.connect(url, ping_timeout=30, open_timeout=10) as ws:
            print_success("Connected to Control Room WebSocket")
            print_info("Monitoring execution... (max 30 seconds)")

            start_time = time.time()

            async for message in ws:
                if time.time() - start_time > 30:
                    print_warning("Timeout after 30 seconds")
                    break

                event = json.loads(message)
                event_type = event.get("event_type", "unknown")
                events_received.append(event_type)

                print_info(f"Event: {event_type}")

                if event_type == "agent_created":
                    agent_id = event["data"].get("agent_id")
                    agent_name = event["data"].get("agent_name", "")
                    print_info(f"  → Agent created: {agent_name[:50]}")

                elif event_type == "agent_started":
                    agent_name = event["data"].get("agent_name", "")
                    print_info(f"  → Agent started: {agent_name[:50]}")

                elif event_type == "agent_completed":
                    agent_name = event["data"].get("agent_name", "")
                    agents_completed.append(agent_name)
                    print_success(f"  → Agent completed: {agent_name[:50]}")

                elif event_type == "agent_failed":
                    agent_name = event["data"].get("agent_name", "")
                    print_error(f"  → Agent failed: {agent_name[:50]}")

                elif event_type == "critique_completed":
                    verdict = event["data"].get("verdict")
                    print_info(f"  → Critique verdict: {verdict}")

                elif event_type == "execution_completed":
                    print_success("Execution completed!")
                    break

                elif event_type == "execution_failed":
                    print_error("Execution failed")
                    break

            return {
                "success": True,
                "events_count": len(events_received),
                "agents_completed": len(agents_completed),
                "events": events_received
            }

    except Exception as e:
        print_error(f"Control Room WebSocket error: {e}")
        return {"success": False, "error": str(e)}

def test_database_check() -> bool:
    """Verify database file exists and has tables."""
    print_header("6. Database Verification")

    import sqlite3
    import os

    db_path = "/Users/schinta/AgentMaster/backend_new/agentmaster.db"

    if not os.path.exists(db_path):
        print_error(f"Database not found at: {db_path}")
        return False

    print_success(f"Database file exists: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        expected_tables = ['executions', 'agents', 'edges', 'critiques', 'tool_executions', 'agent_templates']

        for table in expected_tables:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print_success(f"Table '{table}': {count} records")
            else:
                print_error(f"Table '{table}': MISSING")

        conn.close()
        return True

    except Exception as e:
        print_error(f"Database check error: {e}")
        return False

async def full_validation():
    """Run complete backend validation."""
    print(f"\n{Colors.BOLD}AgentMaster Backend Validation{Colors.RESET}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    results = {
        "health": False,
        "create_execution": False,
        "get_execution": False,
        "studio_ws": False,
        "control_room_ws": False,
        "database": False
    }

    # Test 1: Health check
    results["health"] = test_health_check()
    if not results["health"]:
        print_error("\nBackend is not running. Please start it first:")
        print_info("cd backend_new && uvicorn app.main:app --reload")
        return False

    # Test 2-3: REST API
    execution_id = test_create_execution()
    if execution_id:
        results["create_execution"] = True
        results["get_execution"] = test_get_execution(execution_id)

    # Test 4: Studio WebSocket
    if execution_id:
        results["studio_ws"] = await test_studio_websocket(execution_id)

    # Test 5: Control Room WebSocket (runs execution)
    if execution_id:
        ws_result = await test_control_room_websocket(execution_id)
        results["control_room_ws"] = ws_result.get("success", False)

        if results["control_room_ws"]:
            print_info(f"\nExecution Summary:")
            print_info(f"  Events received: {ws_result['events_count']}")
            print_info(f"  Agents completed: {ws_result['agents_completed']}")

    # Test 6: Database check
    results["database"] = test_database_check()

    # Final summary
    print_header("Validation Summary")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    for test_name, passed_test in results.items():
        status = "PASS" if passed_test else "FAIL"
        color = Colors.GREEN if passed_test else Colors.RED
        print(f"{color}{status}{Colors.RESET} - {test_name}")

    print(f"\n{Colors.BOLD}Overall: {passed}/{total} tests passed{Colors.RESET}")

    if passed == total:
        print_success("\n✓ Backend is fully functional and ready for frontend integration!")
        return True
    else:
        print_error(f"\n✗ {total - passed} test(s) failed. Please review errors above.")
        return False

async def quick_validation():
    """Quick health check only."""
    print_header("Quick Health Check")

    if test_health_check():
        print_success("\nBackend is running and healthy!")
        print_info("Run 'python validate_backend.py' for full validation")
        return True
    else:
        return False

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        success = asyncio.run(quick_validation())
    else:
        success = asyncio.run(full_validation())

    sys.exit(0 if success else 1)
