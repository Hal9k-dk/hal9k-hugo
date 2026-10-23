# hal9k.dk — Hugo

A self-contained static replacement for the WordPress backup dated 2026-10-22.
No WordPress, database, PHP, Node, external theme, or asset pipeline is needed to build or serve this site.

## Local development

Install **Git LFS** and **Hugo extended 0.168.0** (the version pinned in CI). Before cloning, run `git lfs install`. For an existing checkout, download the media with:

```sh
git lfs install
git lfs pull
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

- `content/posts/`: 112 published articles (113 imported, one duplicate archived).
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

`check_site.py` currently expects 112 articles after deduplication and verifies the duplicate URL redirect. Update that baseline when intentionally adding or removing articles. It checks every built local link/media reference and all original public page URLs.

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

Media under `static/wp-content/uploads/`, `static/media/`, and `static/images/` is tracked with **Git LFS**, including existing history. Git stores small pointers; LFS stores roughly 850 MB of actual media. New files in these directories automatically use LFS via `.gitattributes`. Keep CSS, JavaScript, and content in ordinary Git. CI uses `actions/checkout` with `lfs: true` and verifies the objects before building. Once LFS files have been downloaded, builds work offline and the fileserver serves normal files, with no LFS support needed. GitHub LFS storage/download quotas apply, including CI downloads.

History was rewritten for the LFS migration; existing checkouts should be re-cloned after the rewritten branch is pushed. A normal push uploads new LFS objects through the installed pre-push hook.

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
- The duplicate “Floppy Disks” article (WordPress ID 9037) is archived in `migration/duplicates/`, outside published content. Its `-2` URL redirects via a Hugo alias to the original (ID 7557); both legacy WordPress IDs resolve to the original. There are now 112 published articles. `migration/report.json` remains the original import inventory.

## Re-running the importer (not part of normal editing)

This overwrites imported content, so run it in a scratch checkout if content has been edited. Requires Python 3, Beautiful Soup 4, and PHP CLI only for WordPress's original `wpautop` formatter. No WordPress bootstrapping or SQL execution occurs.

```sh
python3 scripts/migrate.py --backup /path/to/extracted-wordpress-backup
python3 scripts/fetch_media.py
hugo --gc --minify
```

`wp_sql.py` parses the selected SQL tables directly. `wpautop.php` loads only the core formatting file, not plugins or database credentials. The fetch step is optional and runs once; downloaded assets are committed, not fetched by CI. After re-import, review `migration/report.json`, restore intentional content fixes, and run the checker before committing.
