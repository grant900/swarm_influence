"""Run the trial matrix in parallel, resumable, with the shared budget ledger enforcing the cap.

  uv run run_batch.py --reps 3 --dry-run         # show matrix size + cost estimate
  uv run run_batch.py --reps 3 --workers 6       # pilot
Arms natural/forced run on every pack; arm `none` runs on control only (the forum is not mentioned,
so the pack only matters as a baseline). Results append to runs/results.jsonl; reruns skip finished cells.
"""
import argparse, itertools, json, random, threading, traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace

import run_trial

ROOT = Path(__file__).parent
RESULTS = ROOT / "runs" / "results.jsonl"
EST_COST_PER_TRIAL = 0.02  # rough, from smoke trials (~$0.01) with headroom
lock = threading.Lock()


def packs():
    return sorted(p.stem for p in (ROOT / "commons" / "content").glob("*.json") if not p.stem.startswith("_"))


def matrix(tasks, pack_names, arms, reps):
    cells = []
    for t, p, a, r in itertools.product(tasks, pack_names, arms, range(reps)):
        if a == "none" and p != "control":
            continue
        cells.append((t, p, a, r))
    if "none" in arms and "control" not in pack_names:
        cells += [(t, "control", "none", r) for t in tasks for r in range(reps)]
    return cells


def done_keys(model, interactive=False, pressure=False):
    if not RESULTS.exists():
        return set()
    out = set()
    for l in RESULTS.read_text().splitlines():
        d = json.loads(l)
        if d.get("model") == model and bool(d.get("interactive", False)) == interactive \
                and bool(d.get("pressure", False)) == pressure:
            out.add((d["task"], d["pack"], d["arm"], d["rep"]))
    return out


def one(cell, model, max_turns, interactive=False, pressure=False):
    t, p, a, r = cell
    res = run_trial.run(SimpleNamespace(task=t, pack=p, arm=a, model=model, max_turns=max_turns, rep=r,
                                           interactive=interactive, pressure=pressure))
    with lock, RESULTS.open("a") as f:
        f.write(json.dumps(res) + "\n")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", nargs="+", default=["slugify", "csvstats", "lrucache"])
    ap.add_argument("--packs", nargs="+", default=packs())
    ap.add_argument("--arms", nargs="+", default=["natural", "forced", "none"])
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--model", default="z-ai/glm-5.3")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--max-turns", type=int, default=30)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--pressure", action="store_true", help="add a rollback/replacement warning to the task text")
    ap.add_argument("--interactive", action="store_true", help="swarm replies to the agent's posts")
    a = ap.parse_args()

    cells = matrix(a.tasks, a.packs, a.arms, a.reps)
    done = done_keys(a.model, a.interactive, a.pressure)
    todo = [c for c in cells if c not in done]
    random.Random(0).shuffle(todo)  # balanced partial coverage if we stop early
    print(f"{len(cells)} cells, {len(done & set(cells))} done, {len(todo)} to run, "
          f"est ${len(todo) * EST_COST_PER_TRIAL:.2f}; spent so far ${run_trial.spent():.2f} (cap ${run_trial.BUDGET_CAP_USD:.0f})")
    if a.dry_run or not todo:
        return

    RESULTS.parent.mkdir(exist_ok=True)
    n_ok = n_err = 0
    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(one, c, a.model, a.max_turns, a.interactive, a.pressure): c for c in todo}
        for f in as_completed(futs):
            c = futs[f]
            try:
                r = f.result()
                n_ok += 1
                print(f"[{n_ok + n_err}/{len(todo)}] {c[0]} {c[1]} {c[2]} rep{c[3]}: passed={r['passed']} "
                      f"gets={r['site_gets']} posts={r['site_posts']} ${r['cost']:.3f}", flush=True)
            except SystemExit as e:  # budget cap
                print(f"STOP: {e}"); ex.shutdown(cancel_futures=True); break
            except Exception:
                n_err += 1
                print(f"[{n_ok + n_err}/{len(todo)}] ERROR {c}:\n{traceback.format_exc(limit=2)}", flush=True)
    print(f"done: {n_ok} ok, {n_err} errors, total spent ${run_trial.spent():.2f}")


if __name__ == "__main__":
    main()
