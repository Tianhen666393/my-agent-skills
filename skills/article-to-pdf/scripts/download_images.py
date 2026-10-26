#!/usr/bin/env python3
"""Download every image of an extracted article and write a URL -> file map.

Usage:
    download_images.py <content.html> <out-dir> [--referer URL] [--map FILE]

Details that matter:
  * `data-src` wins over `src` (lazy-loaded galleries put the real URL there);
  * map keys are the DECODED attribute values - exactly what the browser's
    getAttribute() returns. The raw HTML escapes `&` as `&amp;`, and a map with
    escaped keys never matches inside the DOM, which silently drops every image;
  * files are named in document order (01.png, 02.png, ...) so the map keeps the
    article's image order, and each file is verified by its magic bytes.
"""

import argparse
import os
import re
import struct
import urllib.error
import urllib.request
from html import unescape

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')


def image_size(data):
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        w, h = struct.unpack('>II', data[16:24])
        return w, h, 'png'
    if data[:6] in (b'GIF87a', b'GIF89a'):
        w, h = struct.unpack('<HH', data[6:10])
        return w, h, 'gif'
    if data[:2] == b'\xff\xd8':
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                          0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack('>HH', data[i + 5:i + 9])
                return w, h, 'jpeg'
            i += 2 + struct.unpack('>H', data[i + 2:i + 4])[0]
    return None, None, 'unknown'


def collect_urls(content_html):
    urls = []
    for tag in re.findall(r'<img[^>]*>', content_html):
        for attr in ('data-src', 'src'):
            m = re.search(r'\b%s="([^"]+)"' % attr, tag)
            if m:
                urls.append(unescape(m.group(1)))
                break
    return urls


def extension(url, kind):
    m = re.search(r'wx_fmt=([a-z0-9]+)', url)
    if m:
        return m.group(1)
    if kind != 'unknown':
        return 'jpg' if kind == 'jpeg' else kind
    tail = os.path.splitext(url.split('?')[0])[1].lstrip('.').lower()
    return tail if tail and len(tail) <= 4 else 'png'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('content')
    ap.add_argument('out_dir')
    ap.add_argument('--referer', default='')
    ap.add_argument('--map', dest='map_path', default='')
    ap.add_argument('--skip', type=int, default=0,
                    help='skip the first N images (e.g. decorative header art)')
    args = ap.parse_args()

    content = open(args.content, encoding='utf-8', errors='replace').read()
    urls = collect_urls(content)[args.skip:]
    os.makedirs(args.out_dir, exist_ok=True)
    map_path = args.map_path or os.path.join(args.out_dir, 'image_map.txt')

    headers = {'User-Agent': UA, 'Accept-Language': 'zh-CN,zh;q=0.9'}
    if args.referer:
        headers['Referer'] = args.referer

    mapping, failures = [], []
    # Map values are relative to the directory that holds the image folder, so a
    # wrapper page written next to that folder resolves them as-is ("images/01.png").
    base_dir = os.path.dirname(os.path.abspath(args.out_dir))
    for index, url in enumerate(urls, start=1):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read()
        except (urllib.error.URLError, OSError) as exc:
            failures.append((index, url, str(exc)))
            print('%02d  FAILED  %s' % (index, exc))
            continue

        w, h, kind = image_size(data)
        name = '%02d.%s' % (index, extension(url, kind))
        path = os.path.join(args.out_dir, name)
        with open(path, 'wb') as f:
            f.write(data)
        mapping.append((url, os.path.relpath(os.path.abspath(path), base_dir).replace('\\', '/')))
        print('%02d  %7d B  %s  %sx%s  %s' % (index, len(data), kind, w, h, url[:70]))

    with open(map_path, 'w', encoding='utf-8') as f:
        for url, path in mapping:
            f.write('%s\t%s\n' % (url, path))

    print('downloaded %d/%d -> %s' % (len(mapping), len(urls), map_path))
    gifs = [u for u, _ in mapping if u.split('?')[0].endswith('.gif')]
    if gifs:
        print('note: %d animated gif(s) - a PDF can only show a static frame' % len(gifs))
    if failures:
        raise SystemExit('some images failed: %s' % [i for i, _, _ in failures])


if __name__ == '__main__':
    main()
