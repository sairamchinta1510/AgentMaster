"""Run an existing run by ID and print all events."""
import asyncio, json, sys
import websockets

BASE_WS = "wss://agentmaster-ouabviezcq-ew.a.run.app"
RUN_ID  = "c4e7f383-505d-4978-82c7-b66dd5f38884"


async def main():
    url = f"{BASE_WS}/ws/run/{RUN_ID}"
    print(f"Connecting to {url}\n")
    async with websockets.connect(url, ping_timeout=300, open_timeout=30) as ws:
        while True:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=700)
                evt = json.loads(raw)
                etype = evt.get("type", "")
                data  = evt.get("data", evt)

                if etype == "AGENT_STARTED":
                    print(f"[STARTED]   {data.get('agent_name')}")

                elif etype == "CODE_STATUS":
                    if data.get("phase") in ("PLAN", "EXECUTE_CODE"):
                        print(f"  [CODE]    {data.get('agent_id')} -> {data.get('phase')}")

                elif etype == "AGENT_RESULT":
                    name = data.get("agent_name", "")
                    st   = data.get("status", "")
                    out  = data.get("output") or {}
                    err  = data.get("error", "")
                    verdict = out.get("critique_verdict", "")

                    if verdict:
                        print(f"[CRITIQUE]  {name} -> {verdict} iters={out.get('iterations')} score={out.get('quality_score')}")
                        for iss in (out.get("issues") or [])[:3]:
                            print(f"            - {str(iss)[:120]}")
                    else:
                        ok = "OK " if st == "completed" else "ERR"
                        print(f"[{ok}]     {name} [{st}]")
                        if err:
                            print(f"            err: {str(err)[:250]}")
                        for k, v in out.items():
                            if not k.startswith("_") and v:
                                val = str(v)
                                if "diff" in k.lower() or k in ("patch", "fixed_code", "diff_output"):
                                    print(f"\n{'='*60}")
                                    print(f"DIFF from {name} [{k}]:")
                                    print(val[:5000])
                                    print(f"{'='*60}\n")
                                else:
                                    print(f"            {k}: {val[:180]}")

                elif etype == "CRITIQUE_ITERATION":
                    print(f"[CRIT-ITER] {data.get('agent_id')} iter={data.get('iteration')} "
                          f"-> {data.get('verdict')} score={data.get('quality_score')}")

                elif etype == "CRITIQUE_FIX":
                    print(f"[FIX]       -> {str(data.get('fix_instructions',''))[:180]}")

                elif etype == "RUN_COMPLETE":
                    print(f"\nRUN_COMPLETE  status={data.get('status')}")
                    return

                elif etype == "ERROR":
                    print(f"[ERROR]     {str(data)[:400]}")
                    return

            except asyncio.TimeoutError:
                print("[TIMEOUT] waiting for run event")
                return


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(main())
