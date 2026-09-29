# NYC DOI enforcement actions

Every press release the New York City Department of Investigation has issued
in the last ten years, tagged by what people were accused of, how far the case
had got, and how much money the release says was stolen or recovered.

Built from the MI data-site template. The dataset refreshes itself daily and
publishes to <https://bnmont.github.io/nycdoi/>.

## Start here

```bash
pip install -r requirements.txt
python pipeline/run_update.py
start site\index.html
```

The scraped index is committed as `data/source.csv`, so this runs without
touching the network beyond the last three months.

## Where the data comes from

DOI publishes press releases as one HTML page per month:

    https://www.nyc.gov/site/doi/newsroom/press/<year>/<month>.page

There is no API and no open-data feed; NYC Open Data carries only DOI monthly
totals, and those stop in 2015. So `pipeline/fetch.py` reads the month pages,
follows each link to the release PDF, and keeps the sentences that mention
money. `robots.txt` permits this; the scraper identifies itself and pauses
between requests.

Two things about that scraper are load-bearing and easy to break:

- **The User-Agent must not contain a URL or a `product/version` token.**
  The nyc.gov WAF returns 403 for anything that reads like a crawler. The
  string in `fetch.py` is deliberate; tidying it will silently break every
  request.
- **`data/source.csv` is committed on purpose.** The daily job re-scrapes only
  the last three months and merges. That keeps the job cheap, keeps the PDF
  downloads to whatever is new, and means a bad scrape day cannot erase years
  of records.

To rebuild everything from scratch:

```bash
DOI_BACKFILL=1 python pipeline/fetch.py     # re-scrape all 121 months
DOI_REPARSE=1 python pipeline/fetch.py      # re-read cached PDFs, no downloads
```

## What one row means

One press release, not one defendant. A release naming five people is one row.
Per-defendant extraction is the obvious next step and is not done yet.

Every rule that assigns a category, a record type, a case stage, or a dollar
figure lives in `config.json`. Edit the rulebook there; no Python required.

### The dollar columns need care

DOI states a defendant's **annual salary** in most enforcement releases, often
a clause away from the amount they are accused of stealing. A classifier that
takes the largest figure on the page reports a correction officer's $76,488
salary as money he stole. So a figure is only published when the words around
it say what it is, and `amount_stolen_context` / `amount_recouped_context`
carry the exact sentence behind every number.

Blank means no figure was reported, never zero. Only about a third of releases
state one, so **these columns must not be summed as a total loss to the city.**

`tests/test_money.py` pins this behaviour with real fragments that were once
extracted wrongly. Run it after any edit to `money_rules`:

```bash
python tests/test_money.py
```

## Publishing

Already done for this repo: Pages is set to GitHub Actions, and the deploy
token carries the `workflow` scope. Push to `main` and the workflow builds,
commits refreshed data, and republishes. The Actions tab has a Run button.

Scheduled workflows pause after about two months of no repository activity.
GitHub emails you; one commit turns it back on.

## When something breaks

`validate_data.py` refuses to publish a broken run, and the live site keeps the
last good data. The checks that fire most often:

| Failure | What it usually means |
|---|---|
| `N of M month pages could not be read` | the WAF is blocking — check the User-Agent |
| `X% of enforcement actions are Uncategorised` | the category rulebook needs a new keyword |
| `amount_* reaches $N, past the sanity limit` | a figure was misread — look at its context column |
| `row count fell from N to M` | the source moved or broke; do not "fix" by lowering the bar |

A failed Actions run is a log you can hand to Claude verbatim.
