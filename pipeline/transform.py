"""
STEP 2 — turn raw data into exactly what the site needs.

This is the file you will spend the most time in. Cleaning, filtering,
joining, and computing go here. It must produce two things:

  data/site_data.csv   the published dataset, one row per thing shown
  data/meta.json       row count, update date, and provenance for the footer
"""
from datetime import datetime, timezone

import pandas as pd

from common import DATA, load_config, write_json
from fetch import RAW


def transform():
    cfg = load_config()
    df = pd.read_csv(RAW)

    # --- your work goes here -------------------------------------------
    df = df.dropna(subset=[cfg["label_column"], cfg["value_column"]])
    df = df.sort_values(cfg["value_column"], ascending=False)
    # -------------------------------------------------------------------

    out = DATA / "site_data.csv"
    df.to_csv(out, index=False)

    write_json(DATA / "meta.json", {
        "rows": int(len(df)),
        "updated": datetime.now(timezone.utc).strftime("%B %d, %Y"),
        "updated_iso": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_name": cfg["source_name"],
        "source_url": cfg["source_url"],
    })

    print(f"wrote {len(df)} rows to data/site_data.csv")
    return df


if __name__ == "__main__":
    transform()
