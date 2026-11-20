"""Compare plusieurs variantes du prompt de génération de tests."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_tools.llm import is_offline, provider  # noqa: E402

SPEC = ROOT / "specs/pricing.feature"
GENERATED = ROOT / "tests/generated"


VARIANTS = {
    "Prompt fourni": [],
    "Sans code source": ["--no-source"],
    "+ exemple parfait": ["--prompt-file", "ai_tools/prompts/generate_tests_fewshot.md"],
    "Température 0.8": ["--temperature", "0.8"],
}


def count_tests(path: Path) -> int:
    return len(re.findall(r"^def test_", path.read_text(encoding="utf-8"), flags=re.M))


def measure_variant(name: str, extra: list[str], run_number: int) -> dict:
    output = GENERATED / f"test_pricing_variant_{run_number}.py"
    coverage_json = GENERATED / f"coverage_variant_{run_number}.json"

    command = [
        sys.executable,
        "ai_tools/generate_tests.py",
        str(SPEC.relative_to(ROOT)),
        "--source",
        "minishop/pricing.py",
        "--out",
        str(output.relative_to(ROOT)),
        "--no-run",
        *extra,
    ]

    started = time.monotonic()
    generation = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    elapsed = time.monotonic() - started

    if generation.returncode != 0:
        return {"name": name, "tests": 0, "failures": "génération échouée", "coverage": 0.0, "time": elapsed}

    test_run = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            str(output.relative_to(ROOT)),
            "--cov=minishop.pricing",
            "--cov-branch",
            "--cov-report",
            f"json:{coverage_json.relative_to(ROOT)}",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    failures = "0"
    if test_run.returncode != 0:
        match = re.search(r"(\d+) failed", test_run.stdout)
        failures = match.group(1) if match else "?"

    coverage = 0.0
    if coverage_json.exists():
        data = json.loads(coverage_json.read_text(encoding="utf-8"))
        coverage = float(data["totals"]["percent_covered"])

    return {
        "name": name,
        "tests": count_tests(output),
        "failures": failures,
        "coverage": coverage,
        "time": elapsed,
    }


def markdown_table(results: list[dict]) -> str:
    rows = [
        "| Variante | Nb tests | Tests en échec | Couverture branches | Temps |",
        "|---|---:|---:|---:|---:|",
    ]
    for result in results:
        rows.append(
            f"| {result['name']} | {result['tests']} | {result['failures']} | "
            f"{result['coverage']:.2f}% | {result['time']:.1f} s |"
        )
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "docs/prompt-comparison.md")
    args = parser.parse_args()

    if is_offline():
        print("[x] Aucun fournisseur LLM actif. Configurez LLM_PROVIDER et ses identifiants, ou démarrez Ollama.")
        return 2

    print(f"[+] Fournisseur : {provider()}")
    results = [measure_variant(name, extra, index) for index, (name, extra) in enumerate(VARIANTS.items(), start=1)]
    table = markdown_table(results)
    print(table)

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(table + "\n", encoding="utf-8")
    print(f"[+] Tableau écrit dans {args.report.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
