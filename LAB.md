# The lab, start to finish

You need a GitHub account, the Claude app, and the tools from the setup sheet.
Everything you build here lands in your own account and stays yours.

## Before you write anything

Open a terminal and check you are signed in as the account you want the work
under. If you have two GitHub accounts, this is where people go wrong.

```bash
gh auth status
```

Wrong account, or not signed in at all:

```bash
gh auth login                             # GitHub.com, HTTPS, browser
gh auth refresh -h github.com -s workflow # lets you edit the daily job later
```

Choose HTTPS rather than SSH. It avoids a whole category of key problems.

## Then hand this to Claude

Open the Claude app, start Claude Code in a folder where you keep projects,
and paste this. Read what it proposes before saying yes — it will ask.

```
I'm building a small self-updating data site from a template. Work
through this with me in order, showing me what you're doing at each
step, and stopping where I've asked you to stop.

1. Check git, python3 and gh are installed, and tell me if anything is
   missing.

2. Ask me for a short repo name, then create my own copy of the
   template and clone it:
   gh repo create <my-username>/<name> --public --clone \
     --template Manhattan-Institute/mi-data-site-starter

3. Turn on Pages, which a template copy does not inherit:
   gh api -X POST repos/<my-username>/<name>/pages -f build_type=workflow

4. cd into the clone, read README.md and CLAUDE.md, and follow the
   conventions there for everything that follows.

5. Ask me for: the project title, the one-sentence finding, where my
   data is, the dataset's name and link, and what belongs in the
   method note. Fill in config.json.

6. Put my data in place of data/source.csv, set label_column and
   value_column to match, and adjust pipeline/transform.py as needed.

7. Run `python pipeline/run_update.py` and open site/index.html so I
   can see it. Iterate with me on templates/index.html — never site/.

8. Commit and push, then run the job and watch it:
   gh workflow run "Update data and publish" -R <my-username>/<name>
   gh run watch -R <my-username>/<name>

9. Tell me the live URL and confirm the page loads.

10. Run the /publish command for the metadata, favicon and preview
    image pass, then show me the page at 390px wide.

Rules:
- Stop and ask before adding a dependency or changing anything under
  .github/workflows.
- Never commit an API key. If the pipeline needs one, tell me and I
  will add it as a repository secret myself.
- Nothing from Virtuous, Snowflake, Piano, or any licensed dataset
  goes in this repo. It is public. Ask me if you are unsure about a
  file I give you.
- If a command fails, show me the actual error before trying a fix.
```

## The two moments Claude cannot do for you

Signing in to GitHub in the browser, and approving anything your machine asks
to install. Everything else it runs itself.

## If your laptop will not cooperate

Say so rather than fighting it. There is a browser-based setup that needs
nothing installed, and you will not miss the build time.

## What you leave with

A repository in your own account, a live site at
`https://<your-username>.github.io/<repo>/`, and a job that refreshes it every
morning without you. Your name on every commit.

If you want a custom domain, the workshop handout covers it — the Institute
reimburses it.
