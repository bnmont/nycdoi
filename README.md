# Data site starter

A dataset that refreshes itself on a schedule, and a published page built from
it. Modeled on
[flock-crime-tracker](https://github.com/CharlesFainLehman/flock-crime-tracker).

Use this template to make your own copy. The repository is yours — your
account, your name on every commit.

## Start here

```bash
pip install -r requirements.txt
python pipeline/run_update.py
open site/index.html          # Windows: start site\index.html
```

That works immediately, using the sample data in `data/source.csv`. Once you
see a page, make it yours in this order:

1. **`config.json`** — title, headline, description, source, your name.
2. **`data/source.csv`** — replace with your data, or set `source_data_url` in
   config to pull a CSV from the web. Set `label_column` and `value_column` to
   match your columns.
3. **`pipeline/transform.py`** — the cleaning and shaping. Most of your work.
4. **`templates/index.html`** — how it looks. Ask Claude; that is what it's for.

Never edit `site/`. It is regenerated every run.

## Publishing it

1. **Settings → Pages → Source: GitHub Actions.** Do this once, before the
   first run, or the deploy step fails. A template copies files, not settings,
   so this does not come across on its own.
2. Push to `main`. The workflow builds and deploys.
3. **Actions tab → Update data and publish → Run workflow** to trigger it by
   hand at any time.

The site lands at `https://<your-username>.github.io/<repo>/`. For a custom
domain, see the workshop handout.

Publishing needs the repository to be public, unless you have GitHub Pro.

## The daily job

`.github/workflows/update.yml` runs the pipeline every morning, commits any
changed data, and republishes. The commit history becomes a record of what
changed and when.

If you edit anything under `.github/workflows/`, your push will be rejected
unless your credentials carry the `workflow` scope. Fix it once with:

```bash
gh auth refresh -h github.com -s workflow
```

If your pipeline calls an API, add the key under **Settings → Secrets and
variables → Actions** and reference it in the workflow's `env:` block. Never
put a key in a file.

Scheduled workflows pause after about two months of no repository activity.
GitHub emails you; one commit turns it back on.

## When something breaks

The Actions tab holds the log for every run. A failed run is a log you can hand
to Claude verbatim — that is usually faster than describing the problem.

If validation fails, that is the system working. The live site keeps the last
good data until the underlying problem is fixed.
