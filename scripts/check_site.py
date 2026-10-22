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
index = json.loads((PUBLIC / 'index.json').read_text())
if len(index['articles']) != 113:
    errors.add(f'Expected 113 imported articles, got {len(index["articles"])} (update this baseline when intentionally adding/removing articles)')
for file in PUBLIC.rglob('*'):
    if file.is_file() and file.suffix.lower() in {'.php', '.sql', '.tar', '.log'}:
        errors.add(f'Unexpected deployment file: {file}')
if errors:
    print('\n'.join(sorted(errors)))
    sys.exit(1)
print(f'PASS: {len(files)} HTML files, all local links/media and all migrated public URLs checked; 113 articles indexed.')
