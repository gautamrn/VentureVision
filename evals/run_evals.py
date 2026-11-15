"""Scores claim verdicts against evals/golden_dataset.jsonl.

  heuristic  model-free baseline; free, deterministic, runs in CI
  llm        the pipeline's verdict rules on gpt-4o-mini via OPENAI_API_KEY (costs API credits)

Usage, from the repo root with the backend venv:
  backend/.venv/Scripts/python evals/run_evals.py --mode heuristic --check-baseline
  backend/.venv/Scripts/python evals/run_evals.py --mode llm --publish

Every recorded run is written to evals/results/history/<run_id>.json.
"""

import argparse
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_DIR / "backend"))
SUMMARY_PATH = REPO_DIR / "frontend" / "src" / "data" / "evals" / "summary.json"


def shown(path: Path) -> Path:
    return path.relative_to(REPO_DIR) if path.is_relative_to(REPO_DIR) else path


def parseArgs(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=["heuristic", "llm"], required=True)
    parser.add_argument("--limit", type=int, help="score only the first N cases (smoke test; never recorded)")
    parser.add_argument("--no-record", action="store_true", help="do not write the run to results/history")
    parser.add_argument("--check-baseline", action="store_true", help="exit 1 if heuristic accuracy drops >3 points")
    parser.add_argument("--write-baseline", action="store_true", help="store this heuristic run as the baseline")
    parser.add_argument("--publish", action="store_true", help="rewrite the /evals page data from all stored runs")
    args = parser.parse_args(argv)
    if (args.check_baseline or args.write_baseline) and args.mode != "heuristic":
        parser.error("the baseline is defined for --mode heuristic only")
    return args


def main(argv: list[str]) -> int:
    args = parseArgs(argv)

    if args.mode == "llm":
        from dotenv import load_dotenv

        load_dotenv(REPO_DIR / ".env")
        load_dotenv(REPO_DIR / "backend" / ".env")

    from app.evals.dataset import datasetSha256, loadDataset, loadManifest
    from app.evals.harness import baselineOf, heuristicPredictor, llmPredictor, regressionMessage, runEvals
    from app.evals.results import buildSummary, loadBaseline, saveBaseline, saveRun

    manifest = loadManifest()
    cases = loadDataset()
    if args.limit:
        cases = cases[: args.limit]

    predictor = heuristicPredictor() if args.mode == "heuristic" else llmPredictor()
    model = None
    if args.mode == "llm":
        from app.verification import claimVerifier

        model = claimVerifier.llm.model_name

    print(f"{args.mode}: {len(cases)} cases from {manifest.name} v{manifest.version}")
    run = runEvals(
        cases,
        args.mode,
        predictor,
        model=model,
        datasetVersion=manifest.version,
        datasetSha=datasetSha256(),
        onCase=lambda o: print(f"  {'ok  ' if o.correct else 'MISS'} {o.id:<8} expected {o.expected:<12} got {o.predicted:<12} {o.detail}"),
    )

    print(f"\noverall {run.overall_accuracy}% ({sum(c.correct for c in run.cases)}/{run.case_count})")
    for score in run.labels:
        print(f"  {score.label:<12} {score.accuracy}% ({score.correct}/{score.total})")
    if args.mode == "llm":
        print(f"cost ${run.cost_usd:.4f}")

    if not args.no_record and not args.limit:
        print(f"recorded {shown(saveRun(run))}")
    if args.write_baseline:
        print(f"baseline {shown(saveBaseline(baselineOf(run)))}")
    if args.publish:
        SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY_PATH.write_text(buildSummary().model_dump_json(indent=2) + "\n", encoding="utf-8")
        print(f"published {shown(SUMMARY_PATH)}")

    if args.check_baseline:
        baseline = loadBaseline()
        if baseline is None:
            print("no stored baseline; run with --write-baseline first", file=sys.stderr)
            return 1
        failure = regressionMessage(run, baseline)
        if failure:
            print(f"REGRESSION: {failure}", file=sys.stderr)
            return 1
        print(f"baseline check passed: {run.overall_accuracy}% vs stored {baseline.overall_accuracy}%")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
