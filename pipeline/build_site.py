"""
STEP 4 — render the site from the data.

Reads templates/index.html, fills it in, and writes site/. The site folder is
generated output: edit the template, not the result.

Two tables go in: the category counts that the chart draws, and the releases
themselves. The full dataset, including the supporting quotes behind every
dollar figure, is copied out as data.csv for download.
"""
import json
import shutil

import pandas as pd
from jinja2 import Template

from common import DATA, SITE, TEMPLATES, load_config


def money(value):
    """$1,200,000 -> '$1.2M'. Blank stays blank."""
    if value is None or pd.isna(value):
        return ""
    value = float(value)
    for limit, suffix, divisor in (
        (1_000_000_000, "B", 1_000_000_000),
        (1_000_000, "M", 1_000_000),
        (1_000, "K", 1_000),
    ):
        if value >= limit:
            trimmed = f"{value / divisor:.1f}".rstrip("0").rstrip(".")
            return f"${trimmed}{suffix}"
    return f"${value:,.0f}"


def build():
    cfg = load_config()
    df = pd.read_csv(DATA / "site_data.csv")
    counts = pd.read_csv(DATA / "category_counts.csv")
    meta = json.loads((DATA / "meta.json").read_text())

    label_col, value_col = cfg["label_column"], cfg["value_column"]
    chart = counts.sort_values(value_col, ascending=False)
    chart_rows = chart.to_dict(orient="records")
    max_value = int(chart[value_col].max()) if len(chart) else 1

    total_stolen = df["amount_stolen"].sum(skipna=True)
    total_recouped = df["amount_recouped"].sum(skipna=True)

    releases = df.copy()
    releases["stolen_display"] = releases["amount_stolen"].map(money)
    releases["recouped_display"] = releases["amount_recouped"].map(money)
    releases = releases.fillna("")

    html = Template((TEMPLATES / "index.html").read_text(encoding="utf-8")).render(
        cfg=cfg,
        meta=meta,
        chart_rows=chart_rows,
        label_col=label_col,
        value_col=value_col,
        max_value=max_value,
        releases=releases.to_dict(orient="records"),
        total_stolen=money(total_stolen),
        total_recouped=money(total_recouped),
    )

    SITE.mkdir(exist_ok=True)
    (SITE / "index.html").write_text(html, encoding="utf-8")

    # The raw data, downloadable from the site.
    shutil.copy(DATA / "site_data.csv", SITE / "data.csv")
    shutil.copy(DATA / "category_counts.csv", SITE / "categories.csv")

    for asset in ("favicon.svg", "preview.png"):
        src = TEMPLATES / asset
        if src.exists():
            shutil.copy(src, SITE / asset)

    print(f"built site/index.html from {len(releases)} releases")


if __name__ == "__main__":
    build()
