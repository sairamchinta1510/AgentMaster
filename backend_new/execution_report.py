#!/usr/bin/env python3
"""
Generate execution report with agent hierarchy and input/output visualization.
"""

import sqlite3
import json
from datetime import datetime

EXECUTION_ID = "03834948-e62d-4f23-92e5-7986494fbf44"
DB_PATH = "agentmaster.db"

def get_execution_info():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, objective, domain, status, created_at, completed_at, root_agent_id
        FROM executions WHERE id = ?
    """, (EXECUTION_ID,))

    result = cursor.fetchone()
    conn.close()
    return result

def get_agents():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, parent_id, agent_type, depth, task_description, status,
               input_data, output_data, citations, created_at, started_at, completed_at
        FROM agents
        WHERE execution_id = ?
        ORDER BY depth, created_at
    """, (EXECUTION_ID,))

    agents = []
    for row in cursor.fetchall():
        agents.append({
            "id": row[0],
            "parent_id": row[1],
            "agent_type": row[2],
            "depth": row[3],
            "task_description": row[4],
            "status": row[5],
            "input_data": json.loads(row[6]) if row[6] else {},
            "output_data": json.loads(row[7]) if row[7] else {},
            "citations": json.loads(row[8]) if row[8] else [],
            "created_at": row[9],
            "started_at": row[10],
            "completed_at": row[11]
        })

    conn.close()
    return agents

def get_edges():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, from_agent_id, to_agent_id, data_description
        FROM edges
        WHERE execution_id = ?
    """, (EXECUTION_ID,))

    edges = []
    for row in cursor.fetchall():
        edges.append({
            "id": row[0],
            "from": row[1],
            "to": row[2],
            "description": row[3]
        })

    conn.close()
    return edges

def get_critiques(agent_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT round_number, critique_type, verdict, reasoning
        FROM critiques
        WHERE agent_id = ?
        ORDER BY round_number
    """, (agent_id,))

    critiques = []
    for row in cursor.fetchall():
        critiques.append({
            "round": row[0],
            "type": row[1],
            "verdict": row[2],
            "reasoning": row[3]
        })

    conn.close()
    return critiques

def get_tool_executions(agent_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT tool_name, tool_input, tool_output, status, started_at, completed_at
        FROM tool_executions
        WHERE agent_id = ?
        ORDER BY started_at
    """, (agent_id,))

    tools = []
    for row in cursor.fetchall():
        time_ms = 0
        if row[4] and row[5]:
            start = datetime.fromisoformat(row[4].replace("Z", "+00:00"))
            end = datetime.fromisoformat(row[5].replace("Z", "+00:00"))
            time_ms = (end - start).total_seconds() * 1000

        tools.append({
            "tool": row[0],
            "input": json.loads(row[1]) if row[1] else {},
            "output": json.loads(row[2]) if row[2] else {},
            "status": row[3],
            "time_ms": time_ms
        })

    conn.close()
    return tools

def print_report():
    print("=" * 100)
    print("AGENTMASTER EXECUTION REPORT")
    print("=" * 100)
    print()

    # Execution Info
    exec_info = get_execution_info()
    print(f"📋 EXECUTION: {exec_info[0]}")
    print(f"   Objective: {exec_info[1]}")
    print(f"   Domain: {exec_info[2]}")
    print(f"   Status: {exec_info[3]}")
    print(f"   Created: {exec_info[4]}")
    print(f"   Completed: {exec_info[5]}")
    print(f"   Root Agent: {exec_info[6]}")
    print()

    # Agents
    agents = get_agents()
    edges = get_edges()

    print("=" * 100)
    print("AGENT HIERARCHY")
    print("=" * 100)
    print()

    for agent in agents:
        indent = "  " * agent["depth"]
        icon = "🔷" if agent["agent_type"] == "sub_agent" else "⚡"
        status_icon = {
            "pending": "⏳",
            "running": "▶️",
            "completed": "✅",
            "failed": "❌",
            "human_review": "⚠️",
            "critique_phase": "🔍"
        }.get(agent["status"], "❓")

        print(f"{indent}{icon} [{agent['agent_type'].upper()}] {status_icon} {agent['status']}")
        print(f"{indent}   ID: {agent['id'][:8]}...")
        print(f"{indent}   Task: {agent['task_description'][:80]}...")
        print(f"{indent}   Depth: {agent['depth']}")

        if agent["parent_id"]:
            print(f"{indent}   Parent: {agent['parent_id'][:8]}...")

        # Input
        if agent["input_data"]:
            print(f"{indent}   📥 INPUT:")
            for key, value in agent["input_data"].items():
                if isinstance(value, str) and len(value) > 60:
                    value = value[:60] + "..."
                print(f"{indent}      {key}: {value}")

        # Output
        if agent["output_data"]:
            print(f"{indent}   📤 OUTPUT:")
            if isinstance(agent["output_data"], dict):
                for key, value in agent["output_data"].items():
                    if key == "decomposition":
                        print(f"{indent}      decomposition:")
                        print(f"{indent}         complexity_score: {value.get('complexity_score')}")
                        print(f"{indent}         reasoning: {value.get('reasoning')}")
                        print(f"{indent}         children_count: {len(value.get('children', []))}")
                    elif isinstance(value, str) and len(value) > 60:
                        print(f"{indent}      {key}: {value[:60]}...")
                    else:
                        print(f"{indent}      {key}: {value}")
            else:
                print(f"{indent}      {str(agent['output_data'])[:100]}...")

        # Citations
        if agent["citations"]:
            print(f"{indent}   📚 CITATIONS: {len(agent['citations'])} found")
            for i, citation in enumerate(agent["citations"][:3], 1):
                print(f"{indent}      {i}. [{citation.get('source_type')}] {citation.get('source', 'N/A')}")

        # Critiques
        critiques = get_critiques(agent["id"])
        if critiques:
            print(f"{indent}   🔍 CRITIQUE RESULTS:")
            unique_rounds = {}
            for c in critiques:
                key = f"Round {c['round']} ({c['type']})"
                if key not in unique_rounds:
                    unique_rounds[key] = c

            for key, c in unique_rounds.items():
                verdict_icon = "✅" if c["verdict"] == "passed" else "❌"
                print(f"{indent}      {verdict_icon} {key}: {c['verdict']}")
                if len(c['reasoning']) < 80:
                    print(f"{indent}         → {c['reasoning']}")

        # Tool Executions
        tools = get_tool_executions(agent["id"])
        if tools:
            print(f"{indent}   🔧 TOOLS USED: {len(tools)}")
            for tool in tools:
                print(f"{indent}      - {tool['tool']} ({tool['status']}, {tool['time_ms']}ms)")

        # Timing
        if agent["started_at"] and agent["completed_at"]:
            start = datetime.fromisoformat(agent["started_at"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(agent["completed_at"].replace("Z", "+00:00"))
            duration = (end - start).total_seconds()
            print(f"{indent}   ⏱️  Duration: {duration:.3f}s")

        print()

    # Edges
    if edges:
        print("=" * 100)
        print("AGENT DEPENDENCIES (EDGES)")
        print("=" * 100)
        print()
        for edge in edges:
            print(f"   {edge['from'][:8]}... → {edge['to'][:8]}...")
            if edge['description']:
                print(f"      Description: {edge['description']}")
        print()

    # Execution Graph (ASCII)
    print("=" * 100)
    print("EXECUTION GRAPH (ASCII)")
    print("=" * 100)
    print()

    def build_tree(agents, parent_id=None, depth=0):
        children = [a for a in agents if a.get("parent_id") == parent_id]
        for child in children:
            indent = "    " * depth
            icon = "🔷" if child["agent_type"] == "sub_agent" else "⚡"
            status = {
                "completed": "✅",
                "human_review": "⚠️",
                "failed": "❌",
                "pending": "⏳"
            }.get(child["status"], "❓")

            print(f"{indent}├─ {icon} [{child['agent_type']}] {status}")
            print(f"{indent}│   Task: {child['task_description'][:60]}...")
            print(f"{indent}│   ID: {child['id'][:8]}...")
            print(f"{indent}│")

            build_tree(agents, child["id"], depth + 1)

    root_agents = [a for a in agents if a.get("parent_id") is None or a.get("parent_id") == ""]
    for root in root_agents:
        icon = "🔷" if root["agent_type"] == "sub_agent" else "⚡"
        status = {
            "completed": "✅",
            "human_review": "⚠️",
            "failed": "❌",
            "pending": "⏳"
        }.get(root["status"], "❓")

        print(f"🌳 ROOT: {icon} [{root['agent_type']}] {status}")
        print(f"   Task: {root['task_description'][:60]}...")
        print(f"   ID: {root['id'][:8]}...")
        print()

        build_tree(agents, root["id"], 0)

    print()
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"   Total Agents: {len(agents)}")
    print(f"   Sub-Agents: {len([a for a in agents if a['agent_type'] == 'sub_agent'])}")
    print(f"   Atomic Agents: {len([a for a in agents if a['agent_type'] == 'atomic_agent'])}")
    print(f"   Completed: {len([a for a in agents if a['status'] == 'completed'])}")
    print(f"   Human Review: {len([a for a in agents if a['status'] == 'human_review'])}")
    print(f"   Failed: {len([a for a in agents if a['status'] == 'failed'])}")
    print(f"   Total Edges: {len(edges)}")
    print("=" * 100)

if __name__ == "__main__":
    print_report()
