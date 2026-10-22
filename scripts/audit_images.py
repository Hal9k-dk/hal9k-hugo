#!/usr/bin/env python3
"""Audit imported cover images against WordPress attachment ownership.

Keep featured images attached to the article or explicitly used in its body.
For unrelated/invalid featured records use an actual article image instead.
Run with --fix to update front matter only; body content is never rewritten.
"""
import argparse
import collections
import json
from pathlib import Path
import re
from bs4 import BeautifulSoup
from wp_sql import read_tables

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--backup', type=Path, required=True)
parser.add_argument('--fix', action='store_true')
args = parser.parse_args()
tables = read_tables(args.backup / 'wordpress.sql', ['posts', 'postmeta'])
posts = {p['ID']: p for p in tables['posts']}
meta = collections.defaultdict(dict)
for row in tables['postmeta']:
    meta[row['post_id']][row['meta_key']] = row['meta_value']
manifest = json.loads((ROOT / 'migration/external-media.json').read_text())

def family(url):
    from urllib.parse import unquote, urlsplit
    name = Path(unquote(urlsplit(url).path)).name
    return re.sub(r'-\d+x\d+(?=\.)', '', name)

changes = []
for path in sorted((ROOT / 'content/posts').glob('*.html')):
    text = path.read_text()
    front, end = json.JSONDecoder().raw_decode(text)
    id_ = front['wordpress_id']
    aid = int(meta[id_].get('_thumbnail_id', 0))
    if not aid:
        continue
    attachment = posts.get(aid, {})
    if attachment.get('post_type') == 'attachment' and attachment.get('post_parent') == id_:
        continue
    body = text[end:]
    soup = BeautifulSoup(body, 'html.parser')
    images = [img.get('src') for img in soup.find_all('img') if img.get('src')]
    source = meta[aid].get('_wp_attached_file', '')
    body_sources = set(images)
    for remote, result in manifest.items():
        if result.get('local') in images:
            body_sources.add(remote)
    # Syndicated articles reuse wp-image IDs from other blogs; IDs alone are not evidence.
    if source and any(family(src) == family(source) for src in body_sources):
        continue
    old = front.get('image')
    new = images[0] if images else None
    if old == new:
        continue
    changes.append({'id': id_, 'title': front['title'], 'old_image': old, 'new_image': new, 'wordpress_featured_id': aid, 'featured_parent': attachment.get('post_parent'), 'reason': 'Featured record is not attached to or used by this article'})
    if args.fix:
        if new:
            front['image'] = new
        else:
            front.pop('image', None)
        path.write_text(json.dumps(front, ensure_ascii=False, indent=2) + text[end:])
if args.fix:
    (ROOT / 'migration/image-corrections.json').write_text(json.dumps(changes, ensure_ascii=False, indent=2) + '\n')
for change in changes:
    print(f"{change['id']}: {change['title']} -> {change['new_image'] or '(no cover)'}")
print(f'{len(changes)} unrelated covers {"corrected" if args.fix else "found"}.')
