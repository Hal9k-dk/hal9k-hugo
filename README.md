# hal9k.dk — Hugo

A self-contained static replacement for the WordPress backup dated 2026-10-22.
No WordPress, database, PHP, Node, external theme, or asset pipeline is needed to build or serve this site.

## Local development

Install **Hugo extended 0.168.0** (the version pinned in CI), then:

```sh
hugo server --bind 0.0.0.0
# Preview http://localhost:1313
```

Production build and validation:

```sh
hugo --gc --minify --panicOnWarning
python3 scripts/check_site.py
```

Deploy **only `public/`**. The fileserver needs directory indexes (`/slug/` → `/slug/index.html`), UTF-8, and preferably `404.html` as its error page. No rewrite engine or application server is needed. Redirect `www.hal9k.dk` and HTTP to `https://hal9k.dk/` at the server/proxy if desired.

## Editing content

- `content/posts/`: all 113 published WordPress articles.
- `content/pages/`: all 12 published WordPress pages; nested historical URLs are set explicitly in front matter.
- `content/sponsors/`: 10 historical sponsor acknowledgements.
- `content/legacy/`: 5 other published custom-type records (including old tests), preserved rather than silently dropped.
- `content/categories/`, `content/tags/`: taxonomy titles and original WordPress slugs.
- `static/wp-content/uploads/`: 2,477 original public media files, keeping existing URLs.
- `static/media/imported/`: 540 downloaded external images/media variants.
- `data/comments.json`: 24 approved public comments, without email addresses or IPs.
- `layouts/`, `static/css/site.css`, `static/js/site.js`: the local, responsive theme; no theme submodule.
- `migration/unpublished/`: 26 draft/private/pending records, outside Hugo's content tree and never deployed.

Imported articles are **HTML with JSON front matter**. This is Hugo's native content format: edit the title/date/URL at the top and the HTML below it. Preserving HTML avoids losing tables, code, captions and embedded project layouts. Keep `url` unchanged to preserve incoming links. Plain Markdown is supported for new articles:

```md
---
title: "Mit nye projekt"
date: 2026-10-22T19:00:00+02:00
type: posts
url: /mit-nye-projekt/
authors: ["Dit navn"]
categories: ["Projekter"]
tags: ["Arduino"]
image: /images/mit-projekt.jpg
---

Skriv artiklen her.
```

Place new images in `static/images/`, or use Hugo page bundles. Change `hugo.toml` for navigation/site settings. The home page shows all articles chronologically; `/artikler/` provides local client-side search. FAQ toggles use native `<details>`, YouTube embeds use youtube-nocookie.com, and galleries need no WordPress JavaScript. The original battery-life calculator has been reimplemented in `static/js/site.js`.

`check_site.py` currently expects the migration baseline of 113 articles. Update that baseline when intentionally adding or removing articles. It checks every built local link/media reference and all original public page URLs.

## CI and fileserver deployment

`.github/workflows/build.yml` builds and validates on pushes to `main`/`master` and pull requests, and always uploads a `hal9k-static` artifact. No migration or network media downloads happen during a build.

To enable SSH/rsync deployment, configure GitHub repository **variables**:

- `DEPLOY_HOST`: fileserver hostname
- `DEPLOY_USER`: SSH deployment user
- `DEPLOY_PATH`: a dedicated web root, e.g. `/var/www/hal9k.dk`

And **secrets**:

- `DEPLOY_SSH_KEY`: private deployment key
- `DEPLOY_KNOWN_HOSTS`: verified SSH host-key line(s)

Until `DEPLOY_HOST` is configured CI only produces an artifact. Deployment runs only after a successful build/check, never for PRs. `rsync --delete` mirrors `public/`, so the destination must be dedicated to this site. Give the deployment user access to that directory only. For another CI provider, the build command and `public/` artifact are all that is required.

The repo intentionally includes media in ordinary Git so a clean checkout builds offline; it is roughly 850 MB. No file requires Git LFS. If long-term media growth becomes a concern, move media to a separately managed static asset store while preserving its URLs.

## Migration details and outstanding items

See `migration/report.json` for the full imported-record inventory and `migration/external-media.json` for the external-media download manifest.

- Original `/postname/` article URLs and page hierarchy are retained. Child pages also have short aliases. Encoded Greek Ω in the resistor article URL was normalized for correct filesystem serving.
- Old `?p=ID`, `?page_id=ID`, and `?attachment_id=ID` links are resolved by the small site script. Already migrated links are rewritten directly. A plain fileserver cannot issue query-string-based server redirects without extra configuration.
- The old wiki link in the sausage-machine article now points to `wiki.hal9k.dk`.
- **Membership:** Formidable was a WordPress/database submission service. `/bliv-medlem/` now explicitly directs visitors to the board by email; it does not pretend to save registrations. Configure a membership-service link or a real form endpoint if online registration is required.
- **Map:** the retired mapsmarker shortcode is replaced with a direct OpenStreetMap address link.
- **Regnskab:** the backup contained a BeEF browser-hook script and a suspicious invoice/code-entry form. The public URL is preserved with a safe contact notice rather than reproducing that payload. The unmodified original remains in the source backup outside this repository.
- Two unique external media resources remain remote: an expired Facebook CDN image and a video exceeding the import size limit. Their original URLs are retained, and failures are recorded in the download manifest. External video players/other remote embeds still require the corresponding services.
- Accounts, member submissions, email logs, plugin credentials, caches, WordPress executables and revision history are not part of the deployment. All original records remain in the extracted backup next to this repo.
- Content is intentionally not deduplicated: the two published “Floppy Disks” articles have separate historical URLs and are both retained.

## Re-running the importer (not part of normal editing)

This overwrites imported content, so run it in a scratch checkout if content has been edited. Requires Python 3, Beautiful Soup 4, and PHP CLI only for WordPress's original `wpautop` formatter. No WordPress bootstrapping or SQL execution occurs.

```sh
python3 scripts/migrate.py --backup /path/to/extracted-wordpress-backup
python3 scripts/fetch_media.py
hugo --gc --minify
```

`wp_sql.py` parses the selected SQL tables directly. `wpautop.php` loads only the core formatting file, not plugins or database credentials. The fetch step is optional and runs once; downloaded assets are committed, not fetched by CI. After re-import, review `migration/report.json`, restore intentional content fixes, and run the checker before committing.
