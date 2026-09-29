Do the publishing pass on this site before it gets shared.

1. Read config.json. Fill in anything still holding placeholder text, asking me
   for what you cannot work out: title, headline, description, site_url,
   source_name, source_url, method_note, author.

2. Check templates/index.html has all of: a <title> that reads well in a tab
   and in search results, a meta description under 160 characters, Open Graph
   tags using property= (not name=) with absolute https URLs, a
   twitter:card, a favicon link, and an apple-touch-icon.

3. Generate templates/preview.png at 1200x630 — the headline in large type on
   the accent color, readable at thumbnail size. Confirm build_site.py copies
   it into site/.

4. Generate templates/favicon.svg if the default is still in place. A monogram
   or single glyph in the accent color.

5. Confirm the provenance footer shows the last-updated date, the source with a
   link, the method note, and the CSV download.

6. Rebuild with `python pipeline/run_update.py`, then show me site/index.html
   at 390px wide and fix whatever breaks. Check dark mode too.

7. List anything you could not do and needs me.
