"""End-to-end test: design + run pipeline, print agent/critique stats."""
import asyncio, json, sys, urllib.request
import websockets

BASE_WS   = "wss://agentmaster-ouabviezcq-ew.a.run.app"
BASE_HTTP = "https://agentmaster-ouabviezcq-ew.a.run.app"
PIPELINE_ID = "215a83ac-1350-426f-b85d-f3b264f6d313"
GIT_REPO    = "https://github.com/sairamchinta1510/eu-dress-code.git"

# ── Stats trackers ────────────────────────────────────────────────────────────
design_agents   = {}   # agent_id -> {name, type, produced:bool}
design_critiques = {}  # critique_id -> {target, mode, iterations, verdicts:[]}
run_agents       = {}  # agent_id -> {name, status}
run_critiques    = {}  # agent_id -> {target, iterations, verdicts:[]}


def print_sep(title=""):
    print("\n" + "=" * 65)
    if title:
        print("  " + title)
        print("=" * 65)


async def run_design(pipeline_id):
    print_sep(f"DESIGN PHASE  pipeline={pipeline_id}")
    url = f"{BASE_WS}/ws/design/{pipeline_id}"
    async with websockets.connect(url, ping_timeout=300, open_timeout=30) as ws:
        while True:
            try:
                raw  = await asyncio.wait_for(ws.recv(), timeout=700)
                evt  = json.loads(raw)
                etype = evt.get("type", "")
                data  = evt.get("data", evt)

                # --- Track agents ---
                if etype == "AGENT_STARTED":
                    aid  = data.get("agent_id","")
                    name = data.get("agent_name","")
                    atype = data.get("agent_type","task")
                    design_agents.setdefault(aid, {"name": name, "type": atype, "produced": False})
                    print(f"  [STARTED]    {name} ({aid}) type={atype}")

                elif etype == "AGENT_PRODUCED":
                    aid = data.get("agent_id","")
                    spec = data.get("spec", {})
                    if aid in design_agents:
                        design_agents[aid]["produced"] = True
                        design_agents[aid]["type"] = spec.get("agent_type","task")
                    print(f"  [PRODUCED]   {aid}")

                elif etype == "AGENT_RESULT":
                    aid  = data.get("agent_id","")
                    name = data.get("agent_name","")
                    st   = data.get("status","")
                    out  = data.get("output") or {}
                    verdict = out.get("critique_verdict","")
                    if verdict:
                        iters = out.get("iterations","-")
                        score = out.get("quality_score","-")
                        issues = out.get("issues",[])
                        run_critiques.setdefault(aid, {"name": name, "target": out.get("target_agent",""), "iterations": iters, "verdicts": []})
                        run_critiques[aid]["verdicts"].append(verdict)
                        print(f"  [CRITIQUE]   {name} -> {verdict} iters={iters} score={score} issues={len(issues)}")
                    else:
                        print(f"  [RESULT]     {name} [{st}]")

                elif etype == "CRITIQUE_COMPLETE":
                    aid   = data.get("agent_id","")
                    iters = data.get("iterations","-")
                    verd  = data.get("verdict","")
                    score = data.get("quality_score","-")
                    crit  = data.get("critique", {})
                    mode  = "design"
                    design_critiques.setdefault(aid, {"target": aid, "mode": mode, "iterations": 0, "verdicts": []})
                    design_critiques[aid]["iterations"] = iters
                    design_critiques[aid]["verdicts"].append(verd)
                    print(f"  [CRIT-DONE]  agent={aid} iters={iters} verdict={verd} score={score}")

                elif etype == "CRITIQUE_ITERATION":
                    aid   = data.get("agent_id","")
                    it    = data.get("iteration","-")
                    verd  = data.get("verdict","")
                    score = data.get("quality_score","-")
                    mode  = data.get("mode","")
                    design_critiques.setdefault(aid, {"target": aid, "mode": mode, "iterations": 0, "verdicts": []})
                    design_critiques[aid]["iterations"] = it
                    design_critiques[aid]["verdicts"].append(verd)
                    print(f"  [CRIT-ITER]  {aid} iter={it} -> {verd} (score={score}) [{mode}]")

                elif etype == "CRITIQUE_FIX":
                    instr = str(data.get("fix_instructions",""))[:120]
                    print(f"  [FIX]        target={data.get('target_agent_id','')} iter={data.get('iteration')} -> {instr}")

                elif etype == "PHASE_UPDATE":
                    print(f"  [PHASE]      {data.get('message','')[:100]}")

                elif etype == "BLUEPRINT_READY":
                    bp = data.get("blueprint") or {}
                    agents = bp.get("agents",[])
                    print(f"\n  BLUEPRINT: {len(agents)} agent(s)")
                    for a in agents:
                        print(f"    - {a.get('agent_id')}: {a.get('agent_name')} [{a.get('agent_type','task')}]")

                elif etype == "DESIGN_COMPLETE":
                    bp = data.get("pipeline", {}).get("blueprint") or data.get("blueprint") or {}
                    agents = bp.get("agents",[])
                    print(f"\n  DESIGN_COMPLETE: {len(agents)} final agents in blueprint")
                    return data

                elif etype == "ERROR":
                    print(f"  [ERROR]      {str(data)[:300]}")
                    return None

            except asyncio.TimeoutError:
                print("  [TIMEOUT] waiting for design event")
                return None


async def create_run(pipeline_id, inputs):
    body = json.dumps({"pipeline_id": pipeline_id, "inputs": inputs}).encode()
    req  = urllib.request.Request(
        f"{BASE_HTTP}/api/runs", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        run = json.loads(resp.read())
    print(f"\n  Run created: {run['id']}")
    return run["id"]


async def run_pipeline(run_id):
    print_sep(f"RUN PHASE  run={run_id}")
    url = f"{BASE_WS}/ws/run/{run_id}"
    async with websockets.connect(url, ping_timeout=300, open_timeout=30) as ws:
        while True:
            try:
                raw   = await asyncio.wait_for(ws.recv(), timeout=700)
                evt   = json.loads(raw)
                etype = evt.get("type","")
                data  = evt.get("data", evt)

                if etype == "AGENT_STARTED":
                    aid  = data.get("agent_id","")
                    name = data.get("agent_name","")
                    run_agents[aid] = {"name": name, "status": "running"}
                    print(f"  [STARTED]    {name}")

                elif etype == "CODE_STATUS":
                    if data.get("phase") in ("PLAN","EXECUTE_CODE","REVIEW"):
                        print(f"  [CODE]       {data.get('agent_id','')} -> {data.get('phase')}")

                elif etype == "AGENT_RESULT":
                    aid  = data.get("agent_id","")
                    name = data.get("agent_name","")
                    st   = data.get("status","")
                    out  = data.get("output") or {}
                    err  = data.get("error","")
                    verdict = out.get("critique_verdict","")

                    if verdict:
                        iters  = out.get("iterations","-")
                        score  = out.get("quality_score","-")
                        issues = out.get("issues",[])
                        run_critiques.setdefault(aid, {"name": name, "target": out.get("target_agent",""), "iterations": iters, "verdicts": []})
                        run_critiques[aid]["verdicts"].append(verdict)
                        print(f"  [CRITIQUE]   {name} -> {verdict} iters={iters} score={score} issues={len(issues)}")
                        if issues:
                            for iss in issues[:3]:
                                print(f"               - {str(iss)[:100]}")
                    else:
                        run_agents[aid] = {"name": name, "status": st}
                        ok = "OK " if st == "completed" else "ERR"
                        print(f"  [{ok}]      {name} [{st}]")
                        if err:
                            print(f"               err: {str(err)[:150]}")
                        for k, v in out.items():
                            if not k.startswith("_") and v:
                                val = str(v)
                                if "diff" in k.lower() or k in ("patch","fixed_code"):
                                    print(f"\n  --- DIFF from {name} ---")
                                    print(val[:3000])
                                    print("  --- END DIFF ---\n")
                                else:
                                    print(f"               {k}: {val[:120]}")

                elif etype == "CRITIQUE_ITERATION":
                    aid  = data.get("agent_id","")
                    it   = data.get("iteration","-")
                    verd = data.get("verdict","")
                    score= data.get("quality_score","-")
                    run_critiques.setdefault(aid, {"name": aid, "target": "", "iterations": it, "verdicts": []})
                    run_critiques[aid]["iterations"] = it
                    run_critiques[aid]["verdicts"].append(verd)
                    print(f"  [CRIT-ITER]  {aid} iter={it} -> {verd} (score={score})")

                elif etype == "CRITIQUE_FIX":
                    instr = str(data.get("fix_instructions",""))[:150]
                    print(f"  [FIX]        target={data.get('target_agent_id','')} iter={data.get('iteration')} -> {instr}")

                elif etype == "RUN_COMPLETE":
                    st = data.get("status","")
                    print(f"\n  RUN_COMPLETE status={st}")
                    return data

                elif etype == "ERROR":
                    print(f"  [ERROR]      {str(data)[:300]}")
                    return None

            except asyncio.TimeoutError:
                print("  [TIMEOUT] waiting for run event")
                return None


def print_stats():
    print_sep("STATS SUMMARY")

    print(f"\n  DESIGN — Task Agents produced: {sum(1 for a in design_agents.values() if a.get('produced'))}")
    for aid, a in design_agents.items():
        mark = "(produced)" if a.get("produced") else "(started only)"
        print(f"    {aid}: {a['name']} [{a['type']}] {mark}")

    print(f"\n  DESIGN — Critique events tracked: {len(design_critiques)}")
    for cid, c in design_critiques.items():
        vlist = ", ".join(c["verdicts"][-5:])
        print(f"    {cid}: iters={c['iterations']} verdicts=[{vlist}]")

    print(f"\n  RUN — Agents executed: {len(run_agents)}")
    for aid, a in run_agents.items():
        print(f"    {aid}: {a['name']} [{a['status']}]")

    print(f"\n  RUN — Critique nodes: {len(run_critiques)}")
    for cid, c in run_critiques.items():
        vlist = ", ".join(str(v) for v in c["verdicts"][-5:])
        print(f"    {cid}: target={c['target']} iters={c['iterations']} verdicts=[{vlist}]")

    total_critique_runs = sum(len(c["verdicts"]) for c in {**design_critiques, **run_critiques}.values())
    print(f"\n  TOTAL critique iterations across all agents: {total_critique_runs}")
    print_sep()


async def main():
    # Design
    design_result = await run_design(PIPELINE_ID)
    if not design_result:
        print("[WARN] Design did not complete cleanly")

    print_stats()

    # Run
    run_id = await create_run(PIPELINE_ID, {
        "clone_url":                GIT_REPO,
        "repository_url":           GIT_REPO,
        "repo_url":                 GIT_REPO,
        "git_repo_url":             GIT_REPO,
        "error_message":            "[GoogleGenerativeAI Error]: Error fetching from https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent: [400 Bad Request] API key expired. Please renew the API key.",
        "log_data":                 "[GoogleGenerativeAI Error]: Error fetching from https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent: [400 Bad Request] API key expired. Please renew the API key.",
        "alert_message":            "[GoogleGenerativeAI Error]: API key expired. Please renew the API key.",
        "log_pattern_for_errors":   "error|Error|ERROR|exception|Exception|EXCEPTION",
        "log_pattern_for_warnings": "warn|Warn|WARN|warning|Warning",
    })
    run_result = await run_pipeline(run_id)
    print_stats()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(main())
