#!/usr/bin/env python3
"""Pull the article container out of a saved page.

Usage:
    extract_content.py <page.html> <element-id> <out.html>

The first element carrying id="<element-id>" is located and its inner HTML is
written to <out.html>. Closing tags are matched by depth, so the whole
container survives deeply nested CMS markup (WeChat nests dozens of sections).

Known ids: CSDN -> content_views, WeChat 公众号 -> js_content
"""

import re
import sys
from collections import Counter


def find_inner(html, element_id):
    m = re.search(r'<([a-zA-Z0-9]+)\b[^>]*\bid="%s"' % re.escape(element_id), html)
    if not m:
        raise SystemExit('no element with id="%s" in this page' % element_id)
    tag = m.group(1)
    inner_start = html.index('>', m.start()) + 1
    pattern = re.compile(r'<(/?)%s\b' % re.escape(tag), re.I)
    depth = 0
    i = m.start()
    while True:
        mm = pattern.search(html, i)
        if not mm:
            raise SystemExit('unclosed <%s id="%s">' % (tag, element_id))
        depth += -1 if mm.group(1) else 1
        if depth == 0:
            return tag, html[inner_start:mm.start()]
        i = mm.end()


def main(argv):
    if len(argv) != 4:
        raise SystemExit(__doc__.strip())
    page, element_id, out_path = argv[1], argv[2], argv[3]

    html = open(page, encoding='utf-8', errors='replace').read()
    tag, inner = find_inner(html, element_id)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(inner)

    tags = Counter(t.lower() for t in re.findall(r'<\s*([a-zA-Z0-9]+)', inner))
    images = re.findall(r'<img[^>]*>', inner)
    text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', inner)).strip()

    print('%s#%s -> %s (%d chars of html)' % (tag, element_id, out_path, len(inner)))
    print('tags:', tags.most_common(12))
    print('images:', len(images), '| headings:', {t: tags.get(t, 0) for t in ('h1', 'h2', 'h3')})
    print('text chars:', len(text))
    print('first 120:', text[:120])

    if len(text) < 200:
        print('!! very little text: check the container id, or the article may be JS-rendered')
    if 'visibility: hidden' in inner or 'opacity: 0' in inner:
        print('note: container hides itself until JS runs - the wrapper CSS must override it')


if __name__ == '__main__':
    main(sys.argv)
