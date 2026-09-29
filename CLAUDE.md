# Working in this repository

This is a small data site: a pipeline that refreshes a dataset on a schedule,
and a static page built from it, published to GitHub Pages. It was created from
the MI data-site template and lives in the author's own GitHub account.

## Layout

```
config.json           every setting a person edits by hand
data/source.csv       the committed starting dataset
data/site_data.csv    generated — what the site actually shows
data/meta.json        generated — row count, update date, provenance
data/raw/             gitignored scratch space for downloads
pipeline/fetch.py     step 1 — get the raw data
pipeline/transform.py step 2 — clean and shape it (most work happens here)
pipeline/validate_data.py  step 3 — refuse to publish something broken
pipeline/build_site.py     step 4 — render templates/ into site/
templates/index.html  the page source — EDIT THIS
site/                 generated output — DO NOT EDIT BY HAND
```

Run everything with `python pipeline/run_update.py`.

## Conventions

- **Never edit `site/`.** It is regenerated on every run and your changes will
  be silently overwritten. Change `templates/index.html` instead.
- **Keep the four pipeline steps separate.** Fetching, transforming,
  validating, and rendering stay in their own files. Do not collapse them.
- **`config.json` is the only file a non-technical person should need to open.**
  If a new setting would be useful to them, add it there rather than hardcoding
  it in a script.
- **Add a validation check whenever you find a new way the data can be wrong.**
  A failing pipeline that keeps yesterday's good site is the desired behavior.
- Prefer stdlib and the three libraries already in `requirements.txt`. Ask
  before adding a dependency.

## Rules that are not negotiable

- **Never commit secrets.** API keys go in repository secrets and are read from
  the environment. If you find a key in a file, stop and say so.
- **Never put internal MI data in this repository.** No CRM exports, no donor
  records, no licensed or purchased datasets, nothing from Virtuous, Snowflake,
  or Piano. This repository is public and sits on a personal account, so there
  is no second pair of eyes. Published data must be public data the author is
  permitted to redistribute. If you are unsure about a file, stop and ask.
- **Never remove the provenance footer** — last updated, source, method note,
  CSV download. If the numbers are shown, their origin is shown with them.
- **Do not weaken `validate_data.py` to make a run pass.** If validation fails,
  the data or the transform is wrong. Fix that.

## Before the site is shared

Run `/publish` — see `.claude/commands/publish.md`.
