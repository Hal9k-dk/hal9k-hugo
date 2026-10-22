#!/usr/bin/env python3
"""Vendor external article media and rewrite URLs. Run once, not during CI."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, quote
from html import unescape
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
files = list((ROOT / 'content').rglob('*.html'))
texts = {p: p.read_text() for p in files}
urls = set()
for text in texts.values():
    for match in re.finditer(r'(?:src|poster|srcset)="([^"]+)"', text):
        for part in match[1].split(','):
            value = part.strip().split()[0] if part.strip() else ''
            if value.startswith(('http://', 'https://')) and re.search(r'\.(?:jpe?g|png|gif|webp|svg|mp4|webm|mp3|ogg)(?:\?|$)', value, re.I):
                urls.add(value)
# Include featured-image front matter values.
for text in texts.values():
    for url in re.findall(r'"image": "(https?://[^" ]+)"', text):
        urls.add(url)
media = ROOT / 'static/media/imported'
media.mkdir(parents=True, exist_ok=True)
manifest_path = ROOT / 'migration/external-media.json'
manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

def fetch(url):
    suffix = Path(urlsplit(url).path).suffix.lower()
    name = hashlib.sha256(url.encode()).hexdigest()[:20] + suffix
    target = media / name
    if not target.exists():
        request = Request(quote(unescape(url.replace('http://', 'https://', 1)), safe=':/?=&%+@'), headers={'User-Agent': 'Hal9k-static-migration/1.0'})
        with urlopen(request, timeout=35) as response:
            if not response.headers.get('Content-Type', '').startswith(('image/', 'video/', 'audio/')):
                raise ValueError('Not media: ' + response.headers.get('Content-Type', ''))
            payload = response.read(95 * 1024 * 1024 + 1)
            if len(payload) > 95 * 1024 * 1024:
                raise ValueError('Media too large')
            target.write_bytes(payload)
    return '/media/imported/' + name

with ThreadPoolExecutor(max_workers=12) as pool:
    tasks = {pool.submit(fetch, url): url for url in sorted(urls)}
    for task in as_completed(tasks):
        url = tasks[task]
        try:
            manifest[url] = {'local': task.result()}
        except Exception as exc:
            manifest[url] = {'error': str(exc)}
for path, text in texts.items():
    for url in sorted(manifest, key=len, reverse=True):
        if 'local' in manifest[url]:
            text = text.replace(url, manifest[url]['local'])
    path.write_text(text)
manifest_path.parent.mkdir(exist_ok=True)
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
print(f'External media: {sum("local" in v for v in manifest.values())} downloaded, {sum("error" in v for v in manifest.values())} unavailable')
