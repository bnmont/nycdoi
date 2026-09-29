"""
STEP 4 — render the site from the data.

Reads templates/index.html, fills it in, and writes site/. The site folder is
generated output: edit the template, not the result.
"""
import json
import shutil

import pandas as pd
from jinja2 import Template

from common import DATA, SITE, TEMPLATES, load_config


def build():
    cfg = load_config()
    df = pd.read_csv(DATA / "site_data.csv")
    meta = json.loads((DATA / "meta.json").read_text())

    rows = df.to_dict(orient="records")
    values = df[cfg["value_column"]].tolist()

    html = Template((TEMPLATES / "index.html").read_text()).render(
        cfg=cfg,
        meta=meta,
        rows=rows,
        columns=list(df.columns),
        label_col=cfg["label_column"],
        value_col=cfg["value_column"],
        max_value=max(values) if values else 1,
        data_json=json.dumps(rows),
    )

    SITE.mkdir(exist_ok=True)
    (SITE / "index.html").write_text(html)

    # The raw data, downloadable from the site.
    shutil.copy(DATA / "site_data.csv", SITE / "data.csv")

    for asset in ("favicon.svg", "preview.png"):
        src = TEMPLATES / asset
        if src.exists():
            shutil.copy(src, SITE / asset)

    print(f"built site/index.html from {len(rows)} rows")


if __name__ == "__main__":
    build()
