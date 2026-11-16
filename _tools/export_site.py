#!/usr/bin/env python3
"""Export the portfolio design canvas (.dc.html pages) into static pages for this site.

usage: python3 _tools/export_site.py <folder with the .dc.html files> [more media dirs]

Original media live in _media_src/<asset id>.<ext> (not published). Each export writes
light versions to assets/site/: photos and stickers as WebP, videos re-encoded to
640x480 (macOS avconvert), audio copied. Fonts are self-hosted (assets/site/fonts.css),
so nothing loads from Google (slow or blocked in mainland China).
Re-run after changing the canvas or the text in content/ (it also writes that text into the\ncanvas copies in <folder>, so they can be published back to the canvas).
"""
import os, re, shutil, subprocess, sys, pathlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import content

REPO = pathlib.Path(__file__).resolve().parents[1]
SRC = pathlib.Path(sys.argv[1])
MEDIA = [REPO / '_media_src'] + [pathlib.Path(p) for p in sys.argv[2:]]
OUT = REPO / 'assets' / 'site'
OUT.mkdir(parents=True, exist_ok=True)
content.sync(SRC)  # words in both languages come from content/*.md

PAGES = {
    'Main.dc.html': ('index.html', 'Qinglan Shan', 'Qinglan Shan: mixed reality, embodied learning and HCI. Portfolio, projects, research and photographs.'),
    'Photography.dc.html': ('gallery.html', 'Gallery · Qinglan Shan', 'Photographs by Qinglan Shan: St. Moritz, travel, landscape and street.'),
    'XRLab.dc.html': ('xr-lab.html', 'XR Lab · Qinglan Shan', 'Selected interactive work in mixed and virtual reality.'),
    'Research.dc.html': ('research.html', 'Research · Qinglan Shan', 'Research and publications on learning in mixed reality.'),
    'Project.dc.html': ('project.html', 'Project · Qinglan Shan', 'Project details.'),
}
ID = re.compile(r'([0-9a-f]{32})(\.\w+)$')

sources = {}
for d in MEDIA:
    if d.exists():
        for f in d.iterdir():
            m = ID.match(f.name)
            if m: sources.setdefault(m.group(1), f)

def is_video(path):
    b = path.read_bytes(); i = b.find(b'hdlr')
    while i != -1:
        if b[i + 12:i + 16] == b'vide': return True
        i = b.find(b'hdlr', i + 4)
    return False

def fresh(dst, src):
    return dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime and dst.stat().st_size > 0

def build_asset(i):
    src = sources[i]; ext = src.suffix.lower()
    if ext in ('.jpg', '.jpeg', '.png', '.webp'):
        dst = OUT / (i + '.webp')
        if not fresh(dst, src):
            size, q = ('1800x1800>', '78') if ext in ('.jpg', '.jpeg') else ('1000x1000>', '84')
            subprocess.run(['magick', str(src), '-auto-orient', '-resize', size, '-strip', '-quality', q,
                            '-define', 'webp:method=6', '-define', 'webp:alpha-quality=92', str(dst)], check=True)
        return dst.name
    if ext == '.mp4' and is_video(src):
        dst = OUT / (i + '.mp4')
        if not fresh(dst, src):
            subprocess.run(['avconvert', '-s', str(src), '-o', str(dst), '-p', 'Preset640x480', '--replace'],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return dst.name
    dst = OUT / (i + ext)
    if not fresh(dst, src): shutil.copyfile(src, dst)
    return dst.name

names = {}
def convert(text):
    for src, (dst, _, _) in PAGES.items():
        text = text.replace(src, dst)
    text = text.replace('/_blob/', 'assets/site/')
    def sub(m):
        i = m.group(0)
        if i in sources:
            if i not in names: names[i] = build_asset(i)
            return names[i]
        return i
    return re.sub(r'(?<![0-9a-f])[0-9a-f]{32}(?![0-9a-f.])', sub, text)

FONT_LINK = re.compile(r'<link[^>]*fonts\.(?:googleapis|gstatic)\.com[^>]*>')
for src, (dst, title, desc) in PAGES.items():
    s = (SRC / src).read_text()
    xdc = re.search(r'<x-dc>(.*)</x-dc>', s, re.S).group(1)
    helmets = ''.join(re.findall(r'<helmet>(.*?)</helmet>', xdc, re.S))
    body = re.sub(r'<helmet>.*?</helmet>', '', xdc, flags=re.S).strip()
    logic = re.search(r'<script type="text/x-dc"[^>]*>(.*?)</script>', s, re.S).group(1)
    helmets = FONT_LINK.sub('', convert(helmets)); body = convert(body); logic = convert(logic)
    # videos start when they scroll into view (site.js), not all at once
    body = body.replace('preload="metadata"', 'preload="none"')
    logic = logic.replace('const p = v.play();', 'const p = window.__lazyPlay ? window.__lazyPlay(v) : v.play();')
    page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="icon" href="favicon.png">
<link rel="stylesheet" href="assets/site/fonts.css">
{helmets.strip()}
<link rel="stylesheet" href="assets/site/site.css">
</head>
<body>
<div id="dc-root"></div>
<template id="dc-template">
{body}
</template>
<script type="text/x-dc" id="dc-logic">{logic}</script>
<script src="assets/site/site.js"></script>
<script src="assets/site/runtime.js"></script>
</body>
</html>
'''
    (REPO / dst).write_text(page)
    print('wrote', dst)

# drop published media no page uses any more
keep = set(names.values())
for f in OUT.iterdir():
    if ID.match(f.name) and f.name not in keep: f.unlink()
total = sum((OUT / n).stat().st_size for n in keep)
print('assets', len(keep), 'size %.1f MB' % (total / 1e6))
