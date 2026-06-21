#!/bin/bash
set -e

PIPELINE_ID=$(cat /tmp/new_pipeline_id.txt)
BASE_URL="https://agentmaster-ouabviezcq-ew.a.run.app"

echo "=========================================="
echo "  FULL E2E TEST"
echo "  Pipeline: $PIPELINE_ID"
echo "=========================================="

echo -e "\n[1/3] Waiting for design to complete..."
sleep 10

echo "[2/3] Creating run..."
RUN_ID=$(curl -s -X POST "$BASE_URL/api/runs" \
  -H "Content-Type: application/json" \
  -d "{\"pipeline_id\": \"$PIPELINE_ID\", \"inputs\": {}}" | jq -r '.id')

echo "✓ Run created: $RUN_ID"

echo -e "\n[3/3] Waiting for run to complete (this may take 2-5 minutes)..."
sleep 60

echo -e "\n\n=========================================="
echo "  CHECKING RESULTS"
echo "=========================================="

curl -s "$BASE_URL/api/runs/$RUN_ID" | jq '{
  status,
  results: [.results[] | {
    agent: .agent_name,
    status,
    has_html: (.output.formatted_output != null),
    html_length: (.output.formatted_output | length // 0)
  }]
}'

echo -e "\n\nExtracting HTML output..."
HTML=$(curl -s "$BASE_URL/api/runs/$RUN_ID" | jq -r '.results[] | select(.output.formatted_output != null) | .output.formatted_output' | head -1)

if [ -n "$HTML" ]; then
    OUTPUT_FILE="claude_exercises_$(date +%Y%m%d_%H%M%S).html"
    echo "$HTML" > "$OUTPUT_FILE"
    echo "✅ HTML saved to: $OUTPUT_FILE"

    echo -e "\nHTML Preview (first 500 chars):"
    echo "$HTML" | head -c 500
    echo "..."

    # Count exercises
    EXERCISE_COUNT=$(echo "$HTML" | grep -o '<h3' | wc -l | tr -d ' ')
    CLAUDE_COUNT=$(echo "$HTML" | grep -i -o 'claude' | wc -l | tr -d ' ')

    echo -e "\n\nValidation:"
    echo "  • H3 headings (exercises): $EXERCISE_COUNT"
    echo "  • 'Claude' mentions: $CLAUDE_COUNT"

    if [ "$EXERCISE_COUNT" -ge 8 ] && [ "$CLAUDE_COUNT" -ge 5 ]; then
        echo -e "\n✅ TEST PASSED - HTML contains Claude AI training exercises!"
    else
        echo -e "\n⚠️  Warning: HTML may not contain expected content"
    fi
else
    echo "❌ No HTML output found"
    exit 1
fi
