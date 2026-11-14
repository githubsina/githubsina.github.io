#!/usr/bin/env python3
"""Export the portfolio design canvas (.dc.html pages) into static pages for this site.

usage: python3 _tools/export_site.py <folder with the .dc.html files> <blob map json> [extra blob dir]

The blob map is {asset id: local file}. Pages are written to the repo root, assets to
assets/site/. Re-run after changing the canvas.
"""
import json, os, re, shutil, sys, pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
SRC = pathlib.Path(sys.argv[1])
BLOBS = json.load(open(sys.argv[2]))
EXTRA = pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 else None
OUT_ASSETS = REPO / 'assets' / 'site'
OUT_ASSETS.mkdir(parents=True, exist_ok=True)

PAGES = {
    'Main.dc.html': ('index.html', 'Qinglan Shan', 'Qinglan Shan: mixed reality, embodied learning and HCI. Portfolio, projects, research and photographs.'),
    'Photography.dc.html': ('gallery.html', 'Gallery · Qinglan Shan', 'Photographs by Qinglan Shan: St. Moritz, travel, landscape and street.'),
    'XRLab.dc.html': ('xr-lab.html', 'XR Lab · Qinglan Shan', 'Selected interactive work in mixed and virtual reality.'),
    'Research.dc.html': ('research.html', 'Research · Qinglan Shan', 'Research and publications on learning in mixed reality.'),
    'Project.dc.html': ('project.html', 'Project · Qinglan Shan', 'Project details.'),
}

# asset id -> published file name (id + original extension)
if EXTRA and EXTRA.exists():
    for f in EXTRA.iterdir():
        m = re.match(r'([0-9a-f]{32})(\.\w+)$', f.name)
        if m: BLOBS.setdefault(m.group(1), str(f))
names = {}
for i, path in BLOBS.items():
    ext = os.path.splitext(path)[1].lower() or '.bin'
    names[i] = i + ext

def convert(text):
    for src, (dst, _, _) in PAGES.items():
        text = text.replace(src, dst)
    text = text.replace('/_blob/', 'assets/site/')
    used = set()
    def sub(m):
        i = m.group(0)
        if i in names:
            used.add(i); return names[i]
        return i
    text = re.sub(r'(?<![0-9a-f])[0-9a-f]{32}(?![0-9a-f.])', sub, text)
    return text, used

all_used = set()
for src, (dst, title, desc) in PAGES.items():
    s = (SRC / src).read_text()
    xdc = re.search(r'<x-dc>(.*)</x-dc>', s, re.S).group(1)
    helmets = ''.join(re.findall(r'<helmet>(.*?)</helmet>', xdc, re.S))
    body = re.sub(r'<helmet>.*?</helmet>', '', xdc, flags=re.S).strip()
    logic = re.search(r'<script type="text/x-dc"[^>]*>(.*?)</script>', s, re.S).group(1)
    helmets, u1 = convert(helmets); body, u2 = convert(body); logic, u3 = convert(logic)
    all_used |= u1 | u2 | u3
    page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="icon" href="favicon.png">
{helmets.strip()}
<link rel="stylesheet" href="assets/site/site.css">
</head>
<body>
<div id="dc-root"></div>
<template id="dc-template">
{body}
</template>
<script type="text/x-dc" id="dc-logic">{logic}</script>
<script src="assets/site/runtime.js"></script>
<script src="assets/site/site.js"></script>
</body>
</html>
'''
    (REPO / dst).write_text(page)
    print('wrote', dst)

for i in sorted(all_used):
    target = OUT_ASSETS / names[i]
    if not target.exists() or target.stat().st_size != os.path.getsize(BLOBS[i]):
        shutil.copyfile(BLOBS[i], target)
missing = [i for i in all_used if not (OUT_ASSETS / names[i]).exists()]
print('assets', len(all_used), 'missing', missing)
