#!/usr/bin/env python3
"""Assemble the print wrapper around an extracted article.

Usage:
    build_page.py --content content.html --out article.html --title "标题"
                  [--images image_map.txt] [--css print.css] [--extra-js rules.js]
                  [--source-url URL] [--meta "作者：… | 发布时间：…"]
                  [--footer-note "…"] [--no-promote]

The wrapper contains the print stylesheet, the article markup, and one script
that runs before printing:

  1. rewrites <img> to the local copies from the map and drops unmapped ones
     (ads, icons, QR codes, animated gifs);
  2. optionally promotes headings: a paragraph whose only child is <strong>
     becomes a section heading (or a numbered step heading), and a paragraph
     starting with "N." / "N、" becomes a step heading;
  3. strips leftover CMS inline styles and empty layout shells, then runs the
     article-specific rules from --extra-js.

The image map is matched against img.getAttribute('data-src') / 'src', i.e. the
DECODED url, which is why download_images.py writes decoded keys.

--extra-js is inserted verbatim inside the same IIFE, so `root` (the #content
element) and `MAP` are in scope. See references/platform-notes.md for recipes.
"""

import argparse
import json
import os

DEFAULT_CSS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           os.pardir, 'assets', 'print.css')

CLEANUP_JS = r"""
(function () {
  var MAP = __IMG_MAP__;
  var root = document.getElementById('content');
  if (!root) { return; }

  root.querySelectorAll('img').forEach(function (img) {
    var src = img.getAttribute('data-src') || img.getAttribute('src') || '';
    var local = MAP[src];
    if (!local) { img.remove(); return; }
    img.setAttribute('src', local);
    ['data-src', 'data-w', 'data-ratio', 'width', 'height', 'style'].forEach(function (a) {
      img.removeAttribute(a);
    });
    img.setAttribute('class', 'shot');
    img.setAttribute('alt', '');
  });

  __PROMOTE__

  root.querySelectorAll('[style]').forEach(function (el) { el.removeAttribute('style'); });
  for (var pass = 0; pass < 6; pass++) {
    root.querySelectorAll('section, div, span, p, li').forEach(function (el) {
      if (el.querySelector('img, a, table, br')) { return; }
      var visible = el.textContent.replace(/[\s\u200b-\u200d\ufeff]/g, '');
      if (visible === '') { el.remove(); }
    });
  }

  __EXTRA__
  window.__docReady = true;
})();
"""

PROMOTE_JS = r"""
  root.querySelectorAll('p').forEach(function (p) {
    if (p.closest('table') || p.querySelector('img')) { return; }
    var only = p.children.length === 1 ? p.firstElementChild : null;
    var text = p.textContent.replace(/\s+/g, ' ').trim();
    var isStep = /^(\d{1,2})[.\u3001]/.test(text) && text.length < 160;
    if (only && /^(STRONG|B)$/.test(only.tagName)) {
      var head = document.createElement('h2');
      head.className = isStep ? 'step' : 'sec';
      head.innerHTML = only.innerHTML;
      p.replaceWith(head);
    } else if (isStep) {
      var step = document.createElement('h2');
      step.className = 'step';
      step.innerHTML = p.innerHTML;
      p.replaceWith(step);
    }
  });
"""


def read_map(path):
    mapping = {}
    if not path:
        return mapping
    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\n')
        if not line:
            continue
        url, _, local = line.partition('\t')
        mapping[url] = local
    return mapping


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--content', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--title', required=True)
    ap.add_argument('--images', default='')
    ap.add_argument('--css', default=DEFAULT_CSS)
    ap.add_argument('--extra-js', default='')
    ap.add_argument('--source-url', default='')
    ap.add_argument('--meta', default='')
    ap.add_argument('--footer-note', default='')
    ap.add_argument('--no-promote', action='store_true',
                    help='keep paragraphs as paragraphs; no heading heuristics')
    args = ap.parse_args()

    content = open(args.content, encoding='utf-8').read()
    css = open(args.css, encoding='utf-8').read()
    mapping = read_map(args.images)
    extra = open(args.extra_js, encoding='utf-8').read() if args.extra_js else ''

    js = (CLEANUP_JS
          .replace('__IMG_MAP__', json.dumps(mapping, ensure_ascii=False))
          .replace('__PROMOTE__', '' if args.no_promote else PROMOTE_JS)
          .replace('__EXTRA__', extra))

    head_extra = ''
    if args.meta:
        head_extra += '    <p class="meta">%s</p>\n' % args.meta
    if args.source_url:
        head_extra += ('    <p class="src">原文链接：<a href="%s">%s</a></p>\n'
                       % (args.source_url, args.source_url))

    footer = ''
    if args.footer_note:
        footer = ('  <footer class="doc-foot"><p>%s</p></footer>\n' % args.footer_note)

    html = (
        '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8" />\n'
        '<title>%s</title>\n<style>%s</style>\n</head>\n<body>\n'
        '  <header class="doc-head">\n    <h1>%s</h1>\n%s  </header>\n'
        '  <div id="content">\n%s\n  </div>\n%s'
        '  <script>%s</script>\n</body>\n</html>\n'
        % (args.title, css, args.title, head_extra, content, footer, js)
    )
    with open(args.out, 'w', encoding='utf-8') as f:
        f.write(html)

    print('wrote %s (%d chars, %d mapped images%s)'
          % (args.out, len(html), len(mapping),
             ', extra rules applied' if extra else ''))
    if not mapping:
        print('!! no image map: every <img> will be dropped')


if __name__ == '__main__':
    main()
