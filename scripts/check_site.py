#!/usr/bin/env python3
"""Validate the built site using Python's standard library only."""
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit, urljoin

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'public'
errors = set()

class Links(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path = path
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in ('href', 'src', 'poster'):
            value = attrs.get(key, '')
            if not value or value.startswith(('#', 'mailto:', 'tel:', 'data:', '//')):
                continue
            u = urlsplit(value)
            if u.scheme or u.netloc:
                continue
            base = '/' + str(self.path.parent.relative_to(PUBLIC)) + '/'
            dest = PUBLIC / unquote(urlsplit(urljoin(base, value)).path).lstrip('/')
            if not dest.exists():
                errors.add(f'{self.path.relative_to(PUBLIC)}: missing {value}')
        if tag == 'script' and not attrs.get('src'):
            errors.add(f'{self.path.relative_to(PUBLIC)}: unexpected inline script')

if not (PUBLIC / 'index.html').exists():
    sys.exit('Build first: hugo --minify')
files = list(PUBLIC.rglob('*.html'))
for path in files:
    Links(path).feed(path.read_text())
report = json.loads((ROOT / 'migration/report.json').read_text())
for page in report['pages']:
    if page['published']:
        path = PUBLIC / unquote(page['url']).lstrip('/') / 'index.html'
        if not path.exists():
            errors.add(f'Migrated page not built: {page["url"]}')
# Imported non-public records must never enter the deployable content tree.
for source in (ROOT / 'content').rglob('*.html'):
    front, _ = json.JSONDecoder().raw_decode(source.read_text())
    if front.get('wordpress_id') and front.get('wordpress_status') != 'publish':
        errors.add(f'Non-published WordPress record in content: {source.relative_to(ROOT)}')
# /sponsorer/ is a new public section index, not the old unpublished page.
public_urls = {unquote(p['url']) for p in report['pages'] if p['published']} | {'/sponsorer/'}
for page in report['pages']:
    if not page['published'] and unquote(page['url']) not in public_urls:
        path = PUBLIC / unquote(page['url']).lstrip('/') / 'index.html'
        if path.exists():
            errors.add(f'Unpublished WordPress record was built: {page["url"]}')
index = json.loads((PUBLIC / 'index.json').read_text())
if len(index['articles']) != 112:
    errors.add(f'Expected 112 articles after deduplication, got {len(index["articles"])} (update this baseline when intentionally adding/removing articles)')
duplicate_url = '/floppy-disks-the-best-tv-remote-for-kids-2/'
canonical_url = '/floppy-disks-the-best-tv-remote-for-kids/'
if any(a['url'] == duplicate_url for a in index['articles']):
    errors.add('Duplicate Floppy Disks article is still indexed')
redirect = PUBLIC / duplicate_url.strip('/') / 'index.html'
if not redirect.exists() or not any(marker in redirect.read_text() for marker in ('http-equiv="refresh"', 'http-equiv=refresh')) or canonical_url not in redirect.read_text():
    errors.add('Duplicate Floppy Disks URL must redirect to the original')
for file in PUBLIC.rglob('*'):
    if not file.is_file():
        continue
    if file.suffix.lower() in {'.php', '.sql', '.tar', '.log'}:
        errors.add(f'Unexpected deployment file: {file}')
    with file.open('rb') as stream:
        if stream.read(80).startswith(b'version https://git-lfs.github.com/spec/v1'):
            errors.add(f'LFS pointer deployed instead of media (run git lfs pull): {file.relative_to(PUBLIC)}')
if errors:
    print('\n'.join(sorted(errors)))
    sys.exit(1)
print(f'PASS: {len(files)} HTML files, all local links/media and all migrated public URLs checked; 112 articles indexed; duplicate redirect checked.')
