# Solution: Getting Correct HTML Output for Claude Training Exercises

## Problem Diagnosed

The system IS working correctly and generating agents dynamically. The issue is:

**The LLM misunderstood your objective** and created "Product Management" exercises instead of "Claude AI training" exercises.

### Current Output
- Exercise 1: Define core product vision and mission
- Exercise 2: Conduct a SWOT analysis
- Exercise 3: Develop user personas
- etc.

These are **generic product management exercises**, not Claude/AI training exercises.

## Root Cause

Your original objective was:
> "I want the output to be a HTML page with 10 Exercises. My team of 50 people, ranging from Product manager, Program managers need a basic Claude exercises to get familiarize with Claude. Can you suggest 10 exercises basic to integrating with office products, to improve productivity."

The system interpreted this as:
- Target audience: Product/Program managers
- Topic: Product management work
- Integration: Office products

Instead of:
- Target audience: Product/Program managers
- Topic: **Using Claude AI**
- Integration: Office products

## Solution

### Step 1: Clear the Cached Blueprint

```bash
PIPELINE_ID="613b142a-6761-4fc5-8092-42f24ebd5c4b"
curl -X POST https://agentmaster-ouabviezcq-ew.a.run.app/api/pipelines/$PIPELINE_ID/clear-blueprint
```

### Step 2: Create a New Pipeline with a Clearer Objective

**Better Objective:**

```
Generate an HTML page with 10 hands-on exercises to train Product Managers and Program Managers on using Claude AI effectively. 

Exercises should focus on:
- Basic Claude prompting techniques
- Using Claude for document analysis and summarization
- Integrating Claude API with Microsoft Office tools (Excel, Word, PowerPoint)
- Using Claude to automate workflows in Google Workspace (Docs, Sheets, Slides)
- Best practices for writing effective prompts
- Using Claude for meeting summaries and action items
- Leveraging Claude for project planning and task breakdown
- Using Claude Code for productivity automation

Each exercise should include:
- Title
- Description of what the user will learn
- Step-by-step instructions
- Expected outcome

Output must be a complete, self-contained HTML page with proper formatting.
```

### Step 3: Alternative - Modify the Existing Prompt

If the system is domain-constrained (Software Development/Observability only), you might need to frame it as:

```
Build a software development training pipeline that generates an HTML page containing 10 exercises for teaching developers, product managers, and program managers how to use Claude AI and Claude Code for productivity.

Focus areas:
- Claude API integration examples
- Automated documentation generation
- Code review with Claude
- CI/CD integration with Claude
- Using Claude for technical writing
- Automating office productivity tasks
- Building Claude-powered tools

Output: Complete HTML page with 10 structured exercises, each with title, learning objectives, step-by-step instructions, and code examples where applicable.
```

## Testing

After redesigning with the new objective:

1. Connect to WebSocket: `/ws/design/{{PIPELINE_ID}}`
2. Wait for agents to be generated
3. Create a run: `POST /api/runs`
4. Connect to: `/ws/run/{{RUN_ID}}`
5. Check the `formatted_output` field for the new HTML

## Expected Output

With the corrected objective, you should get exercises like:

1. **Introduction to Claude Prompting** - Learn basic prompt structure
2. **Summarizing Meeting Notes** - Use Claude to extract action items
3. **Excel Data Analysis** - Integrate Claude API to analyze spreadsheet data
4. **Automated Report Generation** - Use Claude to write status reports
5. **Code Documentation** - Generate docs with Claude Code
6. **Email Drafting Assistant** - Use Claude for professional communication
7. **Project Planning** - Break down initiatives with Claude
8. **Presentation Creation** - Generate PowerPoint outlines with Claude
9. **Technical Writing** - Use Claude for documentation
10. **Workflow Automation** - Build Claude-powered productivity tools

Each exercise would be in HTML format with proper instructions for hands-on practice.

## Quick Fix Script

```bash
#!/bin/bash
# fix-exercises.sh

PIPELINE_ID="613b142a-6761-4fc5-8092-42f24ebd5c4b"
BASE_URL="https://agentmaster-ouabviezcq-ew.a.run.app"

echo "Step 1: Clearing cached blueprint..."
curl -X POST "$BASE_URL/api/pipelines/$PIPELINE_ID/clear-blueprint"

echo -e "\n\nStep 2: Creating new pipeline with corrected objective..."

NEW_OBJECTIVE="Build a software development training pipeline that generates an HTML page containing 10 exercises for teaching developers, product managers, and program managers how to use Claude AI and Claude Code for productivity. Focus on: Claude API integration, automated documentation, code review with Claude, CI/CD integration, technical writing automation, office productivity automation. Output: Complete HTML page with 10 structured exercises including title, learning objectives, step-by-step instructions, and code examples."

curl -X POST "$BASE_URL/api/pipelines" \
  -H "Content-Type: application/json" \
  -d "{\"objective\": \"$NEW_OBJECTIVE\", \"name\": \"Claude Training Exercises (Corrected)\"}"

echo -e "\n\nNow connect to /ws/design/{{NEW_PIPELINE_ID}} to generate agents"
```
