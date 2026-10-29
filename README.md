# hal9k.dk — Hugo

A self-contained static replacement for the WordPress backup dated 2026-10-22.
No WordPress, database, PHP, Node, external theme, or asset pipeline is needed to build or serve this site.

## Local development

Install **Git LFS** and **Hugo extended 0.168.0**. Before cloning, run `git lfs install`. For an existing checkout, download the media with:

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

GitHub Actions (`.github/workflows/build.yml`) deploys only on pushes to `main`, never on pull requests or pushes to other branches. CI does not check out the repository, download LFS media, build Hugo, upload artifacts, or copy site output. It only connects as `deploy` on port `2222` and runs `git pull`. The server handles Git LFS, submodules, Hugo builds, and atomic publication.

### Configure GitHub Actions

In the repository, open **Settings → Secrets and variables → Actions**:

1. Under **Secrets**, add `ROOT_KEY`: the complete SSH private deployment key, including its header/footer and line breaks. It must work non-interactively (no passphrase prompt). Despite the secret's name, SSH connects as `deploy`, not root. Install the matching public key in the server's deployment account, with only the permissions needed to trigger deployment.
2. Under **Secrets**, add `DEPLOY_KNOWN_HOSTS`: the verified server host-key entry (or entries). For this nonstandard SSH port, the entry must identify `[drillpress.hal9k.dk]:2222`, for example `[drillpress.hal9k.dk]:2222 ssh-ed25519 <server-public-host-key>`. This is the server's public host key, not the deployment user's key.
3. Under **Variables**, add `DEPLOY_HOST` with value `drillpress.hal9k.dk` (hostname only, without a username, scheme, or port). The deployment user and port are fixed in the workflow.

Obtain the server host key from its administrator or a trusted server console and verify its fingerprint through an independent trusted channel. You may collect a candidate locally with `ssh-keyscan -p 2222 drillpress.hal9k.dk > known_hosts`, but **do not trust that output until its fingerprint has been independently verified**. Store the verified file contents in `DEPLOY_KNOWN_HOSTS`; CI never discovers or automatically accepts host keys. Update this secret after verifying any legitimate host-key rotation, and update its hostname if `DEPLOY_HOST` changes.

The job writes both secrets to temporary files with owner-only permissions and removes them on exit. It uses `BatchMode=yes`, `IdentitiesOnly=yes`, and `StrictHostKeyChecking=yes`, with the supplied known-hosts file as its trust source. Private keys are not printed. Missing configuration, authentication/host-key errors, or a nonzero remote command status fail the job. Deployments are serialized without cancelling an active deployment.

The SSH command is equivalent to:

```sh
ssh -o BatchMode=yes -o IdentitiesOnly=yes \
    -o StrictHostKeyChecking=yes \
    -o UserKnownHostsFile=/path/to/verified-known_hosts \
    -o GlobalKnownHostsFile=/dev/null \
    -i /path/to/private-key \
    -p 2222 deploy@drillpress.hal9k.dk 'git pull'
```

The server must arrange for this command to run in the correct persistent checkout (or route it through a restricted deployment command), and propagate deployment failures as a nonzero exit status. Never serve the source checkout or its `.git` directory; the server publishes only the generated site atomically. No `DEPLOY_USER`, `DEPLOY_PATH`, or rsync configuration is required.

### Git LFS

Media under `static/wp-content/uploads/`, `static/media/`, and `static/images/` is tracked with **Git LFS**, including existing history. Git stores small pointers; LFS stores roughly 850 MB of actual media. New files in these directories automatically use LFS via `.gitattributes`. Keep CSS, JavaScript, and content in ordinary Git. The persistent server checkout retains `.git/lfs/objects` so LFS can reuse downloaded objects. Once media has been downloaded, builds work offline and the published site serves normal files. GitHub LFS storage/download quotas apply to developer and server downloads.

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
