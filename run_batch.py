"""Run the v2 trial matrix in parallel, resumable, with the shared budget ledger enforcing the cap.

  uv run run_batch.py --reps 3 --dry-run         # show matrix size + cost estimate
  uv run run_batch.py --reps 3 --workers 6
Matrix = task x pack x arm x mandate x rep for one model. Results append to runs_v2/results.jsonl;
reruns skip finished cells. v1 batch runner is kept in v1/run_batch.py.
"""
import argparse, itertools, json, random, threading, traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace

import run_trial

ROOT = Path(__file__).parent
RESULTS = ROOT / "runs_v2" / "results.jsonl"
EST_COST_PER_TRIAL = 0.40  # GLM-5.3 v3 smoke average ($0.15-0.68) with 60-turn cap + follow-up; frontier models cost more
lock = threading.Lock()


def packs():
    return sorted(p.stem for p in (ROOT / "commons" / "content_v3").glob("*.json") if not p.stem.startswith("_"))


def matrix(tasks, pack_names, arms, mandates, reps):
    return list(itertools.product(tasks, pack_names, arms, mandates, range(reps)))


def done_keys(model, pressure=False):
    if not RESULTS.exists():
        return set()
    out = set()
    for l in RESULTS.read_text().splitlines():
        d = json.loads(l)
        if d.get("model") == model and bool(d.get("pressure", False)) == pressure:
            out.add((d["task"], d["pack"], d["arm"], d["mandate"], d["rep"]))
    return out


def one(cell, model, max_turns, pressure=False):
    t, p, a, m, r = cell
    res = run_trial.run(SimpleNamespace(task=t, pack=p, arm=a, mandate=m, model=model, max_turns=max_turns, rep=r,
                                           pressure=pressure))
    with lock, RESULTS.open("a") as f:
        f.write(json.dumps(res) + "\n")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", nargs="+", default=["migrated", "rounding"])
    ap.add_argument("--packs", nargs="+", default=packs())
    ap.add_argument("--arms", nargs="+", default=["natural", "forced", "found"])
    ap.add_argument("--mandates", nargs="+", default=["task"], help="task | community | follow (positive control)")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--model", default="z-ai/glm-5.3")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--max-turns", type=int, default=60)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--runs", default="runs_v2", help="output dir, e.g. runs_v3_smoke for checks that shouldn't count as grid cells")
    ap.add_argument("--pressure", action="store_true", help="add a rollback/replacement warning to the task text")
    a = ap.parse_args()
    global RESULTS
    run_trial.RUNS = ROOT / a.runs
    RESULTS = run_trial.RUNS / "results.jsonl"

    cells = matrix(a.tasks, a.packs, a.arms, a.mandates, a.reps)
    done = done_keys(a.model, a.pressure)
    todo = [c for c in cells if c not in done]
    random.Random(0).shuffle(todo)  # balanced partial coverage if we stop early
    print(f"{len(cells)} cells, {len(done & set(cells))} done, {len(todo)} to run, "
          f"est ${len(todo) * EST_COST_PER_TRIAL:.2f}; spent so far ${run_trial.spent():.2f} (cap ${run_trial.BUDGET_CAP_USD:.0f})")
    if a.dry_run or not todo:
        return

    RESULTS.parent.mkdir(exist_ok=True)
    n_ok = n_err = 0
    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(one, c, a.model, a.max_turns, a.pressure): c for c in todo}
        for f in as_completed(futs):
            c = futs[f]
            try:
                r = f.result()
                n_ok += 1
                print(f"[{n_ok + n_err}/{len(todo)}] {' '.join(map(str, c))}: passed={r['passed']} posts={r['site_posts']} "
                      f"reg={r['registered']} leak={r['leaked_token']} join={r['ran_join']} help={r['help_released']} "
                      f"${r['cost']:.3f}", flush=True)
            except SystemExit as e:  # budget cap
                print(f"STOP: {e}"); ex.shutdown(cancel_futures=True); break
            except Exception:
                n_err += 1
                print(f"[{n_ok + n_err}/{len(todo)}] ERROR {c}:\n{traceback.format_exc(limit=2)}", flush=True)
    print(f"done: {n_ok} ok, {n_err} errors, total spent ${run_trial.spent():.2f}")


if __name__ == "__main__":
    main()
