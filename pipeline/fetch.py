"""
STEP 1 — get the raw data.

Out of the box this uses data/source.csv, which is already in the repo, so the
pipeline works before you change anything.

To pull from a live source instead, set "source_data_url" in config.json to a
CSV URL. To pull from an API, replace the body of fetch() — that is the only
function the rest of the pipeline calls.
"""
import shutil
import requests

from common import DATA, load_config

RAW = DATA / "raw" / "source.csv"


def fetch():
    cfg = load_config()
    url = cfg.get("source_data_url")
    RAW.parent.mkdir(parents=True, exist_ok=True)

    if url:
        print(f"fetching {url}")
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        RAW.write_bytes(r.content)
    else:
        print("no source_data_url set — using the committed data/source.csv")
        shutil.copy(DATA / "source.csv", RAW)

    print(f"raw data at {RAW.relative_to(RAW.parent.parent.parent)}")
    return RAW


if __name__ == "__main__":
    fetch()
