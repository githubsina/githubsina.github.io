#!/usr/bin/env python3
"""Bilingual text for the site: reads content/*.md and writes it into the canvas pages.

Each content file is a list of blocks:

    ## key.name
    EN: English text
    中: 中文

Lines starting with '>' are notes for the editor. A key with dots becomes nested
(note.tea.title -> t.note.tea.title in the page). Lists use numbered keys (award.1,
award.2 ...) and ' | ' between columns; the page code splits them.

usage: python3 _tools/content.py <folder with the .dc.html files>
       (export_site.py runs this itself before exporting)
"""
import json, pathlib, re, sys

REPO = pathlib.Path(__file__).resolve().parents[1]
CONTENT = REPO / 'content'

# which content files each canvas page uses
PAGES = {
    'Main.dc.html': ['common.md', 'home.md'],
    'Photography.dc.html': ['common.md', 'gallery.md'],
    'XRLab.dc.html': ['common.md', 'xr-lab.md', 'projects'],
    'Research.dc.html': ['common.md', 'research.md'],
    'Project.dc.html': ['common.md', 'projects'],
}
BLOCK = re.compile(r'/\*I18N\*/.*?/\*/I18N\*/', re.S)


def parse(path):
    out = {'en': {}, 'zh': {}}
    key = lang = None
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if line.startswith('## '):
            key, lang = line[3:].strip(), None
            continue
        if key is None or line.startswith('>') or line.startswith('# '):
            continue
        m = re.match(r'^(EN|ZH|中|中文)\s*[:：]\s?(.*)$', line, re.I)
        if m:
            lang = 'en' if m.group(1).upper() == 'EN' else 'zh'
            out[lang][key] = m.group(2).strip()
        elif lang and line:
            sep = ' ' if lang == 'en' else ''
            out[lang][key] = (out[lang][key] + sep + line).strip()
    for k in set(out['en']) | set(out['zh']):  # a missing language falls back to the other
        out['en'].setdefault(k, out['zh'].get(k, ''))
        out['zh'].setdefault(k, out['en'].get(k, ''))
    return out


def nest(flat):
    tree = {}
    for k, v in flat.items():
        node = tree
        parts = k.split('.')
        for p in parts[:-1]:
            node = node.setdefault(p, {})
            if not isinstance(node, dict):
                raise SystemExit(f'content key clash at "{k}"')
        node[parts[-1]] = v
    return tree


def table(sources):
    t = {'en': {}, 'zh': {}}
    for s in sources:
        if s == 'projects':
            for f in sorted((CONTENT / 'projects').glob('*.md')):
                key = re.sub(r'^\d+[-_ ]*', '', f.stem)
                d = parse(f)
                for L in t:
                    t[L].setdefault('projects', {})[key] = nest(d[L])
        else:
            d = parse(CONTENT / s)
            for L in t:
                t[L].update(nest(d[L]))
    return t


def sync(folder):
    folder = pathlib.Path(folder)
    for page, sources in PAGES.items():
        f = folder / page
        if not f.exists():
            continue
        s = f.read_text(encoding='utf-8')
        data = json.dumps(table(sources), ensure_ascii=False, separators=(',', ':'))
        data = data.replace('</', '<\\/')
        new, n = BLOCK.subn(lambda m: '/*I18N*/' + data + '/*/I18N*/', s)
        if n != 1:
            raise SystemExit(f'{page}: expected one /*I18N*/ block, found {n}')
        if new != s:
            f.write_text(new, encoding='utf-8')
        print('text', page)


if __name__ == '__main__':
    sync(sys.argv[1])
