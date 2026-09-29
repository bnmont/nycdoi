"""
STEP 3 — refuse to publish something broken.

This runs before every commit. If it raises, the workflow stops and the live
site keeps yesterday's good data instead of getting today's bad data.

The checks here were each written because of a way this dataset has actually
gone wrong, or could plausibly go wrong without anyone noticing:

  - a WAF block returns pages with no releases on them
  - a markup change silently stops dates parsing
  - a keyword edit sends most releases into "Uncategorised"
  - a number parse turns "$2.5 million" into two and a half dollars,
    or a salary into a theft
"""
import json
import sys
from datetime import date

import pandas as pd

from common import DATA, load_config

# Above this, a run is more likely broken than newsworthy.
MAX_PLAUSIBLE_AMOUNT = 2_000_000_000
# Above this share of unmatched titles, the rulebook needs attention.
MAX_UNCATEGORISED = 0.30


def validate():
    cfg = load_config()
    path = DATA / "site_data.csv"
    counts_path = DATA / "category_counts.csv"

    if not path.exists():
        raise SystemExit("FAIL: data/site_data.csv does not exist")
    if not counts_path.exists():
        raise SystemExit("FAIL: data/category_counts.csv does not exist")

    df = pd.read_csv(path)
    counts = pd.read_csv(counts_path)
    problems = []

    if df.empty:
        problems.append("the dataset is empty")

    required = ["date", "year", "category", "record_type", "title", "pdf_url",
                "amount_stolen", "amount_recouped"]
    for col in required:
        if col not in df.columns:
            problems.append(f"missing required column: {col}")

    # The chart reads these two from category_counts.csv.
    for col in (cfg["label_column"], cfg["value_column"]):
        if col not in counts.columns:
            problems.append(f"category_counts.csv is missing column: {col}")

    if problems:                      # nothing below is safe without columns
        _fail(problems)

    if df["title"].isna().any() or (df["title"].astype(str).str.len() < 10).any():
        problems.append("some rows have a missing or implausibly short title")

    # Dates must parse, sit inside the window, and not be in the future.
    parsed = pd.to_datetime(df["date"], errors="coerce")
    if parsed.isna().any():
        problems.append(f"{int(parsed.isna().sum())} rows have an unparseable date")
    else:
        today = pd.Timestamp(date.today())
        if (parsed > today).any():
            problems.append(f"{int((parsed > today).sum())} rows are dated in the future")
        oldest_allowed = today - pd.DateOffset(years=int(cfg["years_back"]) + 1)
        if (parsed < oldest_allowed).any():
            problems.append("some rows predate the configured window")

    if df["pdf_url"].duplicated().any():
        problems.append(f"{int(df['pdf_url'].duplicated().sum())} duplicated releases")

    # A rulebook edit that stops matching is the likeliest quiet failure.
    actions = df[df["record_type"] == "Enforcement action"]
    if len(actions) == 0:
        problems.append("no enforcement actions at all — the record_type rules are wrong")
    else:
        share = (actions["category"] == "Uncategorised").mean()
        if share > MAX_UNCATEGORISED:
            problems.append(
                f"{share:.0%} of enforcement actions are Uncategorised "
                f"(limit {MAX_UNCATEGORISED:.0%}) — the category rulebook needs work"
            )

    # Money must be positive, sane, and traceable to the words it came from.
    for col, ctx in (("amount_stolen", "amount_stolen_context"),
                     ("amount_recouped", "amount_recouped_context")):
        amounts = pd.to_numeric(df[col], errors="coerce")
        if (amounts <= 0).any():
            problems.append(f"{col} has non-positive values")
        if (amounts > MAX_PLAUSIBLE_AMOUNT).any():
            biggest = amounts.max()
            problems.append(
                f"{col} reaches ${biggest:,.0f}, past the ${MAX_PLAUSIBLE_AMOUNT:,} "
                "sanity limit — likely a misparsed figure"
            )
        if ctx in df.columns:
            orphaned = amounts.notna() & df[ctx].isna()
            if orphaned.any():
                problems.append(
                    f"{int(orphaned.sum())} rows report {col} with no supporting "
                    "quote — every published figure must be traceable"
                )

    # Guard against a broken source silently gutting the site.
    meta_path = DATA / "meta.json"
    if meta_path.exists():
        previous = json.loads(meta_path.read_text()).get("previous_rows")
        if previous and len(df) < previous * 0.5:
            problems.append(
                f"row count fell from {previous} to {len(df)} — "
                "that looks like a broken source, not real change"
            )

    if problems:
        _fail(problems)

    print(f"validation passed: {len(df)} releases, {len(actions)} enforcement actions")
    return df


def _fail(problems):
    print("VALIDATION FAILED:", file=sys.stderr)
    for p in problems:
        print(f"  - {p}", file=sys.stderr)
    raise SystemExit(1)


if __name__ == "__main__":
    validate()
