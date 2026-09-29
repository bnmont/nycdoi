"""
STEP 3 — refuse to publish something broken.

This runs before every commit. If it raises, the workflow stops and the live
site keeps yesterday's good data instead of getting today's bad data.

Add your own checks as you learn what "wrong" looks like for your dataset.
"""
import json
import sys

import pandas as pd

from common import DATA, load_config


def validate():
    cfg = load_config()
    path = DATA / "site_data.csv"

    if not path.exists():
        raise SystemExit("FAIL: data/site_data.csv does not exist")

    df = pd.read_csv(path)
    problems = []

    if df.empty:
        problems.append("the dataset is empty")

    for col in (cfg["label_column"], cfg["value_column"]):
        if col not in df.columns:
            problems.append(f"missing required column: {col}")

    if cfg["label_column"] in df.columns and df[cfg["label_column"]].isna().any():
        problems.append("some rows have no label")

    # Guard against a broken source silently gutting the site.
    meta_path = DATA / "meta.json"
    if meta_path.exists():
        previous = json.loads(meta_path.read_text()).get("rows")
        if previous and len(df) < previous * 0.5:
            problems.append(
                f"row count fell from {previous} to {len(df)} — "
                "that looks like a broken source, not real change"
            )

    if problems:
        print("VALIDATION FAILED:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        raise SystemExit(1)

    print(f"validation passed: {len(df)} rows")
    return df


if __name__ == "__main__":
    validate()
