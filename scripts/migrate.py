#!/usr/bin/env python3
"""Reproducible, offline WordPress -> Hugo migration. See README.md."""
import argparse
import collections
import html
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import parse_qs, unquote, urlsplit
from bs4 import BeautifulSoup, Comment
from wp_sql import read_tables

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--backup', type=Path, default=ROOT / 'wordpress-backup')
args = parser.parse_args()
backup = args.backup.resolve()
site = ROOT
site.mkdir(exist_ok=True)
data = read_tables(backup / 'wordpress.sql', ['posts', 'postmeta', 'terms', 'term_taxonomy', 'term_relationships', 'users', 'comments'])
posts = {p['ID']: p for p in data['posts']}
meta = collections.defaultdict(dict)
for m in data['postmeta']:
    meta[m['post_id']][m['meta_key']] = m['meta_value']
terms = {t['term_id']: t for t in data['terms']}
taxonomies = {t['term_taxonomy_id']: t for t in data['term_taxonomy']}
relationships = collections.defaultdict(list)
for r in data['term_relationships']:
    relationships[r['object_id']].append(taxonomies[r['term_taxonomy_id']])
authors = {u['ID']: u['display_name'] for u in data['users']}
content_types = {'post', 'page', 'sponsor', 'sponsorat', 'event', 'test'}
selected = [p for p in posts.values() if p['post_type'] in content_types and p['post_status'] in {'publish', 'draft', 'pending', 'private', 'future'}]
report = {'source': 'BackWPup 2026-10-22', 'counts': {}, 'pages': [], 'sanitized': [], 'missing_media': [], 'external_media': [], 'excluded_uploads': [], 'notes': [
    'Regnskab (1857) quarantined: BeEF browser hook and suspicious invoice-approval form. Original retained ONLY in source backup.',
    'Formidable membership form replaced with explicit email contact; no form submissions or member records are exported.',
    'Private, pending, password-protected and draft records are stored outside Hugo content in migration/unpublished, never deployed.',
    'Only year-organized public uploads are copied; plugin caches, PHP, logs and Formidable uploads are not published.',
    'External media remain external unless fetched with scripts/fetch_media.py.',
]}

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')

def slug(p):
    return unquote(p['post_name']) or f"wordpress-{p['ID']}"

def permalink(p):
    if p['post_type'] == 'page':
        parent = posts.get(p['post_parent'])
        return (permalink(parent) if parent else '/') + slug(p) + '/'
    if p['post_type'] == 'post':
        return '/' + slug(p) + '/'
    return '/' + p['post_type'] + '/' + slug(p) + '/'

urls = {p['ID']: permalink(p) for p in selected}
attachment_urls = {}
for p in posts.values():
    if p['post_type'] == 'attachment':
        file = meta[p['ID']].get('_wp_attached_file')
        if file:
            attachment_urls[p['ID']] = '/wp-content/uploads/' + file

hosts = {'hal9k.dk', 'www.hal9k.dk', 'wp.hal9k.dk'}
def local_url(value):
    value = html.unescape(value).strip()
    u = urlsplit(value)
    if u.hostname and u.hostname not in hosts:
        return value
    query = parse_qs(u.query)
    for key in ['p', 'page_id', 'attachment_id']:
        if key in query and query[key][0].isdigit():
            id_ = int(query[key][0])
            dest = attachment_urls.get(id_) or urls.get(id_)
            if dest:
                return dest + ('#' + u.fragment if u.fragment else '')
    path = u.path
    if '/wp-content/uploads/' in path:
        return path[path.index('/wp-content/uploads/'):] + ('?' + u.query if u.query else '')
    if path.startswith('/wordpress/'):
        path = path[len('/wordpress'):]
    if u.hostname in hosts:
        return (path or '/') + ('?' + u.query if u.query else '') + ('#' + u.fragment if u.fragment else '')
    return value

# Only public media directories, never copy executable code or form submissions.
allowed = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf', '.svg', '.mp4', '.webm', '.mp3', '.ogg', '.wav', '.zip'}
uploads = backup / 'wp-content/uploads'
media_count = 0
for file in sorted(uploads.rglob('*')):
    if not file.is_file():
        continue
    rel = file.relative_to(uploads)
    if re.fullmatch(r'20\d\d', rel.parts[0]) and file.suffix.lower() in allowed:
        dest = site / 'static/wp-content/uploads' / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, dest)
        media_count += 1
    else:
        report['excluded_uploads'].append(str(rel))

def attrs(text):
    result = {}
    for m in re.finditer(r'([\w-]+)\s*=\s*(?:"([^"]*)"|\x27([^\x27]*)\x27|([^\s]+))', text):
        result[m[1]] = next(v for v in m.groups()[1:] if v is not None)
    return result

def youtube(text):
    text = text.strip(' =\"\x27\r\n')
    u = urlsplit(text if '://' in text else 'https://' + text)
    id_ = parse_qs(u.query).get('v', [u.path.strip('/').split('/')[-1]])[0] if ('/' in text or '?' in text) else text
    if re.fullmatch(r'[A-Za-z0-9_-]{11}', id_):
        return f'<div class="video"><iframe loading="lazy" title="YouTube video" src="https://www.youtube-nocookie.com/embed/{id_}" allowfullscreen></iframe></div>'
    return f'<p><a href="{html.escape(text, quote=True)}">Video</a></p>'

def convert(p):
    text = p['post_content'].replace('\r\n', '\n')
    if p['ID'] == 1857:
        return '<aside class="notice"><p>Denne side er midlertidigt taget ud af drift af sikkerhedshensyn. Kontakt <a href="mailto:bestyrelse@hal9k.dk">bestyrelsen</a> for oplysninger om foreningens regnskab.</p></aside>'
    text = re.sub(r'\[caption([^\]]*)\](.*?)\[/caption\]', lambda m: '<figure class="caption">' + m[2] + '</figure>', text, flags=re.S)
    text = re.sub(r'\[toggle([^\]]*)\](.*?)\[/toggle\]', lambda m: '<details><summary>' + html.escape(attrs(m[1]).get('title', 'Læs mere')) + '</summary>' + m[2] + '</details>', text, flags=re.S)
    def gallery(match):
        a = attrs(match[1])
        ids = [int(i) for i in a.get('ids', a.get('include', '')).split(',') if i.strip().isdigit()]
        if not ids:
            ids = [v['ID'] for v in sorted(posts.values(), key=lambda v: (v['menu_order'], v['ID'])) if v['post_parent'] == p['ID'] and v['post_type'] == 'attachment' and v['post_mime_type'].startswith('image/')]
            if a.get('orderby') == 'title':
                ids.sort(key=lambda i: posts[i]['post_title'])
        images = []
        for i in ids:
            src = attachment_urls.get(i)
            if src:
                alt = html.escape(meta[i].get('_wp_attachment_image_alt') or posts[i]['post_title'], quote=True)
                images.append(f'<figure><a href="{src}"><img loading="lazy" src="{src}" alt="{alt}"></a></figure>')
        return '<div class="gallery">' + ''.join(images) + '</div>'
    text = re.sub(r'\[gallery([^\]]*)\]', gallery, text)
    text = re.sub(r'\[youtube([^\]]*)\](?:\[/youtube\])?', lambda m: youtube(m[1]), text)
    text = re.sub(r'\[embed\](.*?)\[/embed\]', lambda m: youtube(m[1]) if 'youtu' in m[1] else '<p><a href="' + html.escape(m[1], quote=True) + '">Se indhold</a></p>', text, flags=re.S)
    text = re.sub(r'\[formidable[^\]]*\]', '<aside class="notice"><h2>Indmeldelse</h2><p>Den tidligere tilmeldingsformular er ikke tilgængelig på denne hjemmeside. Kontakt <a href="mailto:bestyrelse@hal9k.dk?subject=Indmeldelse%20i%20Hal9k">bestyrelsen om indmeldelse</a>, eller kig forbi en torsdag. Send ikke følsomme oplysninger via e-mail.</p></aside>', text)
    text = re.sub(r'\[mapsmarker[^\]]*\]', '<p><a class="button" href="https://www.openstreetmap.org/search?query=Sofiendalsvej%2080%2C%209200%20Aalborg">Find Sofiendalsvej 80 på OpenStreetMap ↗</a></p>', text)
    return text

raw = [convert(p) for p in selected]
# Use WordPress's own paragraph formatter to preserve classic-editor line breaks.
proc = subprocess.run(['php', str(ROOT / 'scripts/wpautop.php'), str(backup)], input=json.dumps(raw), text=True, capture_output=True, check=True)
formatted = json.loads(proc.stdout)
external = set()
missing = set()
for p, text in zip(selected, formatted):
    soup = BeautifulSoup(text, 'html.parser')
    for comment in soup.find_all(string=lambda x: isinstance(x, Comment)):
        comment.extract()
    for tag in list(soup.find_all(['script', 'object', 'embed', 'base', 'link', 'meta'])):
        report['sanitized'].append({'id': p['ID'], 'element': tag.name})
        tag.decompose()
    for tag in list(soup.select('button.lightbox-trigger')):
        tag.decompose()
    for tag in soup.find_all(True):
        for key in list(tag.attrs):
            if key.lower().startswith(('on', 'data-wp-')):
                del tag[key]
        for key in ['href', 'src', 'poster', 'action']:
            if key not in tag.attrs:
                continue
            value = local_url(tag[key])
            if re.match(r'^\s*(javascript|vbscript|data):', value, re.I):
                del tag[key]
                continue
            tag[key] = value
            if key in ['src', 'poster']:
                if value.startswith('/wp-content/uploads/') and not (site / 'static' / unquote(urlsplit(value).path).lstrip('/')).exists():
                    missing.add(value)
                elif value.startswith(('https://', 'http://')) and tag.name in ['img', 'source', 'video', 'audio']:
                    external.add(value)
        if tag.get('srcset'):
            tag['srcset'] = ', '.join(' '.join([local_url(part.split()[0])] + part.split()[1:]) for part in tag['srcset'].split(',') if part.split())
        if tag.name == 'img':
            tag['loading'] = 'lazy'
            tag.attrs.setdefault('alt', '')
            tag.attrs.pop('fetchpriority', None)
        if tag.name == 'iframe':
            tag['loading'] = 'lazy'
            tag.attrs.setdefault('title', 'Indlejret indhold')
            if str(tag.get('src', '')).startswith('http://'):
                tag['src'] = tag['src'].replace('http://', 'https://', 1)
    body = str(soup)
    published = p['post_status'] == 'publish' and not p['post_password']
    section = {'post': 'posts', 'page': 'pages', 'sponsorat': 'sponsors'}.get(p['post_type'], 'legacy')
    dest = site / 'content' / section / (slug(p) + '.html') if published else ROOT / 'migration/unpublished' / (str(p['ID']) + '.html')
    front = {'title': html.unescape(p['post_title']) or ('RTX' if p['ID'] == 1302 else f"WordPress {p['ID']}"), 'date': p['post_date'].replace(' ', 'T') + '+02:00', 'lastmod': p['post_modified'].replace(' ', 'T') + '+02:00', 'url': urls[p['ID']], 'type': 'posts' if p['post_type'] == 'post' else 'pages', 'wordpress_id': p['ID'], 'wordpress_type': p['post_type'], 'wordpress_status': p['post_status'], 'authors': [authors.get(p['post_author'], 'Hal9k')], 'draft': not published}
    front['aliases'] = []
    if p['post_type'] == 'page' and p['post_parent']:
        front['aliases'].append('/' + slug(p) + '/')
    for tax, name in [('category', 'categories'), ('post_tag', 'tags')]:
        front[name] = list(dict.fromkeys(terms[t['term_id']]['name'] for t in relationships[p['ID']] if t['taxonomy'] == tax))
    image = attachment_urls.get(int(meta[p['ID']].get('_thumbnail_id', 0)))
    if not image:
        img = soup.find('img')
        image = img.get('src') if img else None
    if image:
        front['image'] = image
    if p['post_excerpt']:
        front['description'] = BeautifulSoup(p['post_excerpt'], 'html.parser').get_text(' ', strip=True)
    write(dest, json.dumps(front, ensure_ascii=False, indent=2) + '\n\n' + body + '\n')
    report['pages'].append({'id': p['ID'], 'title': front['title'], 'type': p['post_type'], 'status': p['post_status'], 'url': urls[p['ID']], 'published': published, 'file': str(dest.relative_to(ROOT))})

# Public approved comments only; no emails, IPs, user IDs, or moderation records.
comments = collections.defaultdict(list)
for c in data['comments']:
    if str(c['comment_approved']) != '1' or c['comment_type'] not in ('', 'comment'):
        continue
    if not any(p['ID'] == c['comment_post_ID'] and p['post_status'] == 'publish' and not p['post_password'] for p in selected):
        continue
    comments[str(c['comment_post_ID'])].append({'author': c['comment_author'], 'date': c['comment_date'], 'text': BeautifulSoup(c['comment_content'], 'html.parser').get_text('\n', strip=True)})
write(site / 'data/comments.json', json.dumps(comments, ensure_ascii=False, indent=2))
write(site / 'data/wordpress_urls.json', json.dumps({str(p['ID']): urls[p['ID']] for p in selected if p['post_status'] == 'publish' and not p['post_password']} | {str(k): v for k, v in attachment_urls.items()}, ensure_ascii=False, indent=2))
# Term bundles preserve the original WordPress taxonomy slugs.
for t in taxonomies.values():
    if t['taxonomy'] not in ['category', 'post_tag']:
        continue
    term = terms[t['term_id']]
    section = 'categories' if t['taxonomy'] == 'category' else 'tags'
    base = 'category' if section == 'categories' else 'tag'
    write(site / 'content' / section / term['slug'] / '_index.md', json.dumps({'title': term['name'], 'url': f"/{base}/{term['slug']}/"}, ensure_ascii=False) + '\n')
write(site / 'content/posts/_index.md', '---\ntitle: Artikler\nurl: /artikler/\n---\n')
write(site / 'content/pages/_index.md', '---\ntitle: Alle sider\nurl: /sider/\n---\n')
write(site / 'content/sponsors/_index.md', '---\ntitle: Sponsorer\nurl: /sponsorer/\n---\n')
report['counts'] = dict(collections.Counter(p['post_type'] for p in selected if p['post_status'] == 'publish' and not p['post_password']))
report['counts']['unpublished_preserved'] = sum(not p['published'] for p in report['pages'])
report['counts']['media_files'] = media_count
report['counts']['approved_comments'] = sum(map(len, comments.values()))
report['missing_media'] = sorted(missing)
report['external_media'] = sorted(external)
write(ROOT / 'migration/report.json', json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps(report['counts'], indent=2))
print(f'Missing local media: {len(missing)}; external media URLs: {len(external)}')
