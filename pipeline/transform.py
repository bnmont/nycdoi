"""
STEP 2 — turn raw data into exactly what the site needs.

Takes the scraped index of DOI press releases and adds the judgement calls:

  record_type      is this an enforcement action, or a report/statement?
  category         what the person was accused of
  stage            how far the case had got
  amount_stolen    dollars taken, where the release says so
  amount_recouped  dollars recovered, where the release says so

Every rule lives in config.json, not here, so the taxonomy can be argued
with and changed without touching Python.

Writes three things:

  data/site_data.csv       one row per press release — the published dataset
  data/category_counts.csv one row per category — what the chart draws
  data/meta.json           counts and provenance for the footer
"""
import json
from collections import Counter
from datetime import datetime, timezone

import pandas as pd

from common import DATA, load_config, write_json
from fetch import RAW
from pdf_text import MONEY, SEP

ENFORCEMENT = "Enforcement action"
UNCATEGORISED = "Uncategorised"

MULTIPLIER = {"": 1, "k": 1_000, "thousand": 1_000, "million": 1_000_000,
              "billion": 1_000_000_000}


def first_match(text, rules, default):
    """Name of the first rule whose keywords appear in text. Order matters."""
    low = text.lower()
    for rule in rules:
        for kw in rule["keywords"]:
            if kw.lower() in low:
                return rule["name"]
    return default


def _value(match):
    try:
        value = float(match.group(1).replace(",", ""))
    except ValueError:
        return 0.0
    return value * MULTIPLIER.get((match.group(2) or "").lower().strip(), 1)


def parse_amount(fragment):
    """Largest dollar figure in a fragment of text, as a number."""
    return max((_value(m) for m in MONEY.finditer(fragment)), default=0.0)


def focal_amount(fragment):
    """The figure a fragment is *about*, not the biggest one in it.

    pdf_text.py builds one fragment per dollar figure, centred on that
    figure, so the one nearest the middle is the subject and the others are
    neighbours that happen to be in view. Taking the largest instead once
    reported $40 million of payroll hidden from an insurance fund as money
    stolen from labourers, when the release said $1.7 million five times.
    """
    matches = list(MONEY.finditer(fragment))
    if not matches:
        return 0.0
    middle = len(fragment) / 2
    nearest = min(matches, key=lambda m: abs((m.start() + m.end()) / 2 - middle))
    return _value(nearest)


def _consensus(candidates):
    """The figure the release repeats most, breaking ties by size.

    A press release states its headline number several times and its
    incidental numbers once. Counting beats comparing.
    """
    if not candidates:
        return 0.0, ""
    tally = Counter(amount for amount, _ in candidates)
    best = max(tally, key=lambda a: (tally[a], a))
    context = next(ctx for amount, ctx in candidates if amount == best)
    return best, context


def _scan(mentions, rules):
    """Sort each fragment's focal figure into stolen, recouped, or neither."""
    exclude = [w.lower() for w in rules["exclude"]]
    stolen_words = [w.lower() for w in rules["stolen"]]
    recouped_words = [w.lower() for w in rules["recouped"]]

    stolen, recouped = [], []

    for mention in mentions:
        mention = mention.strip()
        if not mention:
            continue
        low = mention.lower()

        # A salary stated next to a theft is still a salary, and the value
        # of a contract someone won is not money they took.
        if any(w in low for w in exclude):
            continue

        amount = focal_amount(mention)
        if amount <= 0:
            continue

        # Recovery language is the more specific signal, so test it first.
        if any(w in low for w in recouped_words):
            recouped.append((amount, mention))
        elif any(w in low for w in stolen_words):
            stolen.append((amount, mention))

    return _consensus(stolen), _consensus(recouped)


def classify_money(title, mentions, rules):
    """Dollars stolen and recovered, with the words each figure came from.

    The title wins when it states a figure: it is the release's own headline
    number, chosen by the people who wrote it, and it is never surrounded by
    the incidental figures that clutter the body text.
    """
    (t_stolen, t_sctx), (t_recouped, t_rctx) = _scan([title], rules)
    (b_stolen, b_sctx), (b_recouped, b_rctx) = _scan(mentions, rules)

    stolen, stolen_ctx = (t_stolen, t_sctx) if t_stolen else (b_stolen, b_sctx)
    recouped, recouped_ctx = (t_recouped, t_rctx) if t_recouped else (b_recouped, b_rctx)

    return stolen, stolen_ctx, recouped, recouped_ctx


def transform():
    cfg = load_config()
    df = pd.read_csv(RAW, dtype=str).fillna("")

    if df.empty:
        raise SystemExit("FAIL: the scraped index is empty — nothing to transform")

    df["title"] = df["title"].str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["year"] = df["date"].dt.year

    # --- the judgement calls -------------------------------------------
    df["record_type"] = df["title"].apply(
        lambda t: first_match(t, cfg["record_types"], ENFORCEMENT)
    )
    df["category"] = df["title"].apply(
        lambda t: first_match(t, cfg["categories"], UNCATEGORISED)
    )
    df["stage"] = df["title"].apply(
        lambda t: first_match(t, cfg["stages"], "")
    )

    # A report or a statement has no defendant and no case stage.
    not_enforcement = df["record_type"] != ENFORCEMENT
    df.loc[not_enforcement, "stage"] = ""

    # The title is the release's own headline figure, so read it alongside
    # the PDF text and let it win when the two disagree.
    money = df.apply(
        lambda r: classify_money(
            r["title"],
            str(r["money_context"]).split(SEP),
            cfg["money_rules"],
        ),
        axis=1,
        result_type="expand",
    )
    money.columns = ["amount_stolen", "amount_stolen_context",
                     "amount_recouped", "amount_recouped_context"]
    df = pd.concat([df, money], axis=1)

    # Blank, not zero: "no figure reported" is not "nothing was taken".
    for col in ("amount_stolen", "amount_recouped"):
        df[col] = df[col].replace(0.0, pd.NA).astype("Float64").round(0)
    # -------------------------------------------------------------------

    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    df = df.sort_values(["date", "title"], ascending=[False, True])

    published = [
        "date", "year", "category", "record_type", "stage",
        "amount_stolen", "amount_recouped", "title",
        "amount_stolen_context", "amount_recouped_context", "pdf_url",
    ]
    out = df[published]
    out.to_csv(DATA / "site_data.csv", index=False)

    # The chart counts enforcement actions only — filing a DOI report under
    # "Uncategorised" and drawing it next to bribery would be misleading.
    actions = df[df["record_type"] == ENFORCEMENT]
    counts = (
        actions.groupby("category")
        .agg(releases=("title", "size"),
             dollars_stolen=("amount_stolen", "sum"))
        .reset_index()
        .sort_values("releases", ascending=False)
    )
    counts.to_csv(DATA / "category_counts.csv", index=False)

    # Carry the last run's row count forward before overwriting meta.json.
    # validate_data.py runs after this file and would otherwise compare the
    # new count against itself, which can never fail.
    meta_path = DATA / "meta.json"
    previous_rows = None
    if meta_path.exists():
        try:
            previous_rows = json.loads(meta_path.read_text()).get("rows")
        except (ValueError, OSError):
            previous_rows = None

    now = datetime.now(timezone.utc)
    write_json(meta_path, {
        "rows": int(len(out)),
        "previous_rows": previous_rows,
        "enforcement_actions": int(len(actions)),
        "other_records": int(len(out) - len(actions)),
        "categories": int(counts["category"].nunique()),
        "uncategorised": int((actions["category"] == UNCATEGORISED).sum()),
        "with_amount_stolen": int(actions["amount_stolen"].notna().sum()),
        "with_amount_recouped": int(actions["amount_recouped"].notna().sum()),
        "first_date": str(out["date"].min()),
        "last_date": str(out["date"].max()),
        "updated": now.strftime("%B %d, %Y"),
        "updated_iso": now.isoformat(timespec="seconds"),
        "source_name": cfg["source_name"],
        "source_url": cfg["source_url"],
    })

    print(f"wrote {len(out)} releases to data/site_data.csv")
    print(f"  {len(actions)} enforcement actions across {len(counts)} categories")
    print(f"  {int((actions['category'] == UNCATEGORISED).sum())} uncategorised")
    print(f"  {int(actions['amount_stolen'].notna().sum())} with an amount stolen, "
          f"{int(actions['amount_recouped'].notna().sum())} with an amount recouped")
    return out


if __name__ == "__main__":
    transform()
