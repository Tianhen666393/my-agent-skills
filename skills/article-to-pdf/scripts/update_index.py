#!/usr/bin/env python3
"""Create or refresh the index that sits next to the guide library.

Usage:
    update_index.py --library <dir> [--index <csv>] [--entry "file|software|version|url|note"]...

One row per PDF in <dir>, keyed by file name, so re-running never duplicates a
guide. `--entry` supplies the metadata for the guide you just produced; PDFs
without an entry still get a row so nothing goes missing.

Columns: 软件名, 版本, 文件名, 页数, 原文链接, 生成日期, 备注

Notes:
  * page count comes from pdfinfo when it can be found (bundled runtime, PATH or
    PDFINFO_PATH), otherwise from a /Type /Page count in the raw file;
  * 生成日期 is the file's modification time, i.e. when the PDF was produced;
  * the CSV is written as UTF-8 **with BOM** so Excel/WPS on a Chinese Windows
    shows the text correctly instead of mojibake.
"""

import argparse
import csv
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

COLUMNS = ['软件名', '版本', '文件名', '页数', '原文链接', '生成日期', '备注']


def find_pdfinfo():
    candidates = [os.environ.get('PDFINFO_PATH'),
                  shutil.which('pdfinfo'),
                  os.path.expanduser(
                      r'~\.cache\codex-runtimes\codex-primary-runtime\dependencies'
                      r'\native\poppler\Library\bin\pdfinfo.exe')]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def page_count(pdf_path, pdfinfo):
    if pdfinfo:
        try:
            # pdfinfo prints localized dates, so decode explicitly as UTF-8:
            # the locale default (GBK here) chokes on those bytes.
            proc = subprocess.run([pdfinfo, pdf_path], capture_output=True,
                                  encoding='utf-8', errors='replace', timeout=30)
            m = re.search(r'^Pages:\s+(\d+)', proc.stdout or '', re.M)
            if m:
                return m.group(1)
        except (OSError, subprocess.SubprocessError):
            pass
    data = open(pdf_path, 'rb').read()
    return str(len(re.findall(rb'/Type\s*/Page[^s]', data)))


def derive_software(file_name):
    name = os.path.splitext(file_name)[0]
    for marker in ['_安装教程', '安装教程', '_安装指南']:
        if marker in name:
            name = name.split(marker)[0]
            break
    return name or file_name


def read_existing(index_path):
    rows = {}
    if index_path and os.path.exists(index_path):
        with open(index_path, encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                key = (row.get('文件名') or '').strip()
                if key:
                    rows[key] = {c: (row.get(c) or '').strip() for c in COLUMNS}
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--library', required=True)
    ap.add_argument('--index', default='')
    ap.add_argument('--entry', action='append', default=[],
                    help='"file.pdf|software|version|url|note" (note optional)')
    args = ap.parse_args()

    library = args.library
    index_path = args.index or os.path.join(library, '安装教程索引.csv')
    rows = read_existing(index_path)
    pdfinfo = find_pdfinfo()

    for entry in args.entry:
        parts = [p.strip() for p in entry.split('|')]
        parts += [''] * (5 - len(parts))
        file_name, software, version, url, note = parts[:5]
        if file_name not in rows:
            rows[file_name] = dict.fromkeys(COLUMNS, '')
        rows[file_name].update({'软件名': software or rows[file_name]['软件名'],
                                '版本': version,
                                '原文链接': url,
                                '备注': note})

    pdfs = sorted(f for f in os.listdir(library) if f.lower().endswith('.pdf'))
    for name in pdfs:
        row = rows.setdefault(name, dict.fromkeys(COLUMNS, ''))
        if not row['软件名']:
            row['软件名'] = derive_software(name)
        path = os.path.join(library, name)
        row['文件名'] = name
        row['页数'] = page_count(path, pdfinfo)
        row['生成日期'] = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d')

    for name in list(rows):
        if name not in pdfs:
            print('note: row without a file, kept as-is:', name)

    ordered = [rows[n] for n in sorted(rows, key=lambda n: (rows[n]['软件名'], n))]
    with open(index_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(ordered)

    print('index: %s (%d rows, %s)' % (index_path, len(ordered),
                                       'pdfinfo' if pdfinfo else 'regex page count'))
    for row in ordered:
        print('  %s | %s | %s 页 | %s' % (row['软件名'], row['版本'] or '-',
                                          row['页数'], row['文件名']))


if __name__ == '__main__':
    sys.exit(main())
