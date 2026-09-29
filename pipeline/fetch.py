"""
STEP 1 — get the raw data.

Scrapes the NYC Department of Investigation press release archive. Each month
of the archive is its own page:

    https://www.nyc.gov/site/doi/newsroom/press/<year>/<month>.page

and each page lists press releases as links to PDFs. We keep the index of
those releases — date, title, link — not the PDFs themselves.

Two modes:

  backfill    scrape every month in the window. Slow (~120 requests), done
              once. Triggered automatically when data/source.csv is missing,
              or on demand with DOI_BACKFILL=1.

  incremental scrape only the last few months and merge into the existing
              data/source.csv. This is what the daily job does.

data/source.csv is committed, so the history accumulates in the repository and
a bad scrape day cannot silently erase years of records.
"""
import os
import random
import re
import time
from datetime import date

import pandas as pd
import requests
from bs4 import BeautifulSoup

from common import DATA, load_config
from pdf_text import cache_path, release_money_context

RAW = DATA / "raw" / "source.csv"
INDEX = DATA / "source.csv"

BASE = "https://www.nyc.gov"
MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]

# A date written out in the page text, e.g. "August 28, 2024".
DATE_TEXT = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b",
    re.I,
)
PDF_HREF = re.compile(r"/assets/doi/press-releases/.+\.pdf$", re.I)

# Fields read off the month pages.
SCRAPED = ["date", "year", "month", "title", "pdf_url"]
# Fields read out of the release PDF itself (see pdf_text.py).
ENRICHED = ["money_context", "pdf_chars", "pdf_note", "pdf_fetched"]
COLUMNS = SCRAPED + ENRICHED


def months_in_window(years_back):
    """Every (year, month) from `years_back` years ago through this month."""
    today = date.today()
    out = []
    y, m = today.year - years_back, today.month
    while (y, m) <= (today.year, today.month):
        out.append((y, MONTHS[m - 1]))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


# nyc.gov sits behind a WAF that rejects anything that looks like a crawler:
# a bare product token, or a URL inside the User-Agent, both return 403. This
# string identifies us honestly without tripping it. Do not "tidy" it by
# adding a project URL — that is exactly what gets blocked.
USER_AGENT = "Mozilla/5.0 (research; mi-data-site)"


def _session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    return s


def parse_month(html, year, month_name):
    """Pull (date, title, pdf_url) out of one month page.

    The markup has changed over the years: sometimes the link text is the
    date and the title sits beside it, sometimes the reverse. So we read the
    whole containing block and sort out which part is which.
    """
    soup = BeautifulSoup(html, "html.parser")
    seen, rows = set(), []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not PDF_HREF.search(href):
            continue

        url = BASE + href if href.startswith("/") else href
        if url in seen:
            continue
        seen.add(url)

        link_text = " ".join(a.get_text(" ", strip=True).split())

        # Walk up to the block that holds both the date and the title.
        block = a
        for _ in range(4):
            if block.parent is None:
                break
            block = block.parent
            if block.name in ("td", "tr", "li", "p", "div"):
                break
        block_text = " ".join(block.get_text(" ", strip=True).split())

        m = DATE_TEXT.search(block_text)
        if m:
            iso = pd.to_datetime(
                f"{m.group(1)} {m.group(2)} {m.group(3)}", errors="coerce"
            )
            when = "" if pd.isna(iso) else iso.strftime("%Y-%m-%d")
            spelled = m.group(0)
        else:
            when, spelled = "", ""

        # The title is whichever text is not the date.
        title = link_text
        if not title or DATE_TEXT.fullmatch(title.strip().rstrip(".")):
            title = block_text
        if spelled:
            title = title.replace(spelled, " ")
        title = " ".join(title.split()).strip(" -–—|·• ")

        if not title:
            continue

        rows.append({
            "date": when,
            "year": year,
            "month": month_name,
            "title": title,
            "pdf_url": url,
        })

    return rows


def scrape(targets, session, pause=0.4):
    rows, missing = [], []
    for i, (year, month_name) in enumerate(targets, 1):
        url = f"{BASE}/site/doi/newsroom/press/{year}/{month_name}.page"
        try:
            r = session.get(url, timeout=60)
        except requests.RequestException as e:
            missing.append(f"{year}/{month_name} ({type(e).__name__})")
            continue

        if r.status_code == 404:
            missing.append(f"{year}/{month_name} (404)")
            continue
        if r.status_code != 200:
            missing.append(f"{year}/{month_name} (HTTP {r.status_code})")
            continue

        found = parse_month(r.text, year, month_name)
        rows.extend(found)
        print(f"  [{i:>3}/{len(targets)}] {year}/{month_name:<10} {len(found):>3} releases")

        # Be a considerate visitor to a public website.
        time.sleep(pause + random.uniform(0, 0.2))

    if missing:
        print(f"  no page for: {', '.join(missing)}")

    # A blocked scrape looks exactly like a quiet month unless we say so.
    # This happened for real: the WAF 403'd every page and the run "succeeded"
    # with zero rows. Fail here instead of publishing an empty dataset.
    if targets and len(missing) > max(2, 0.25 * len(targets)):
        raise SystemExit(
            f"FAIL: {len(missing)} of {len(targets)} month pages could not be "
            f"read. That is a blocked or moved source, not a quiet stretch."
        )

    return rows


def enrich_money(df, session, pause=0.3):
    """Read each not-yet-read PDF for the sentences that mention money.

    Only rows we have never tried are fetched, so the daily job downloads a
    handful of new releases rather than the whole decade again.
    """
    if os.environ.get("DOI_REPARSE") == "1":
        # Re-read every cached PDF. Use this after changing how money is
        # pulled out of the text; it costs no downloads.
        todo = df.index.tolist()
        print("reparse: re-reading every cached PDF")
    else:
        todo = df.index[df["pdf_fetched"] != "1"].tolist()

    limit = os.environ.get("DOI_PDF_LIMIT")
    if limit:
        todo = todo[: int(limit)]

    if not todo:
        print("no new PDFs to read")
        return df

    print(f"reading {len(todo)} press release PDFs")
    notes = 0
    for n, i in enumerate(todo, 1):
        url = df.at[i, "pdf_url"]
        was_cached = cache_path(url).exists()
        context, chars, note = release_money_context(url, session)
        df.at[i, "money_context"] = context
        df.at[i, "pdf_chars"] = str(chars)
        df.at[i, "pdf_note"] = note
        df.at[i, "pdf_fetched"] = "1"
        if note:
            notes += 1
        if n % 50 == 0 or n == len(todo):
            print(f"  [{n:>3}/{len(todo)}] read")
        if not was_cached:
            time.sleep(pause + random.uniform(0, 0.2))

    got = int((df.loc[todo, "money_context"].str.len() > 0).sum())
    print(f"  {got} of {len(todo)} mention a dollar figure; {notes} unreadable")
    return df


def fetch():
    cfg = load_config()
    years_back = int(cfg.get("years_back", 10))
    refresh_months = int(cfg.get("refresh_months", 3))

    RAW.parent.mkdir(parents=True, exist_ok=True)
    window = months_in_window(years_back)

    have_index = INDEX.exists()
    backfill = os.environ.get("DOI_BACKFILL") == "1" or not have_index

    if backfill:
        targets = window
        print(f"backfill: scraping {len(targets)} month pages "
              f"({targets[0][1]} {targets[0][0]} – {targets[-1][1]} {targets[-1][0]})")
    else:
        targets = window[-refresh_months:]
        print(f"incremental: refreshing the last {len(targets)} months")

    session = _session()
    fresh = pd.DataFrame(scrape(targets, session), columns=SCRAPED)

    if have_index:
        existing = pd.read_csv(INDEX, dtype=str).fillna("")
        for col in COLUMNS:
            if col not in existing.columns:
                existing[col] = ""
        combined = pd.concat([existing[SCRAPED], fresh], ignore_index=True)
    else:
        existing = pd.DataFrame(columns=COLUMNS)
        combined = fresh

    # A re-scraped month wins over the stored copy: keep the last occurrence.
    combined = combined.drop_duplicates(subset=["pdf_url"], keep="last")

    # Carry the PDF-derived fields across by URL. Without this, re-scraping
    # the last three months would blank out money data we already have and
    # re-download those PDFs every single day.
    combined = combined.merge(
        existing[["pdf_url"] + ENRICHED].drop_duplicates(subset=["pdf_url"]),
        on="pdf_url",
        how="left",
    )
    for col in ENRICHED:
        combined[col] = combined[col].fillna("")

    combined = enrich_money(combined, session)
    combined = combined.sort_values(["date", "title"], na_position="first")

    combined[COLUMNS].to_csv(INDEX, index=False)
    combined[COLUMNS].to_csv(RAW, index=False)

    added = len(combined) - len(existing)
    print(f"index now holds {len(combined)} releases ({added:+d} this run)")
    return RAW


if __name__ == "__main__":
    fetch()
