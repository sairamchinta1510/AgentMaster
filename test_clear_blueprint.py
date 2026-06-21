"""Test script to verify the clear-blueprint endpoint works."""
import requests

# Use the deployed instance
BASE_URL = "https://agentmaster-ouabviezcq-ew.a.run.app"

def test_clear_blueprint():
    # First, get list of pipelines
    print("Fetching pipelines...")
    response = requests.get(f"{BASE_URL}/api/pipelines")

    if response.status_code != 200:
        print(f"Failed to fetch pipelines: {response.status_code}")
        print(response.text)
        return

    pipelines = response.json()
    if not pipelines:
        print("No pipelines found. Create one first.")
        return

    # Take the first pipeline
    pipeline_id = pipelines[0]["id"]
    print(f"\nTesting with pipeline: {pipeline_id}")
    print(f"Objective: {pipelines[0]['objective']}")
    print(f"Agent count: {pipelines[0]['agent_count']}")

    # Get the full pipeline
    print(f"\nFetching pipeline details...")
    response = requests.get(f"{BASE_URL}/api/pipelines/{pipeline_id}")

    if response.status_code != 200:
        print(f"Failed to fetch pipeline: {response.status_code}")
        return

    pipeline = response.json()
    blueprint_agents_before = len(pipeline.get("blueprint", {}).get("agents", []))
    print(f"Blueprint has {blueprint_agents_before} agents")

    # Clear the blueprint
    print(f"\nClearing blueprint...")
    response = requests.post(f"{BASE_URL}/api/pipelines/{pipeline_id}/clear-blueprint")

    if response.status_code == 200:
        print("✅ Blueprint cleared successfully!")
        cleared_pipeline = response.json()
        blueprint_agents_after = len(cleared_pipeline.get("blueprint", {}).get("agents", []))
        print(f"Blueprint now has {blueprint_agents_after} agents")

        if blueprint_agents_after == 0:
            print("✅ Success: Blueprint is empty")
        else:
            print(f"⚠️  Warning: Blueprint still has agents")
    else:
        print(f"❌ Failed to clear blueprint: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_clear_blueprint()
