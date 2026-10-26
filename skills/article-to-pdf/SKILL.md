---
name: article-to-pdf
description: 将网页教程文章（CSDN、微信公众号等）转为含原文、截图和页码的离线 A4 PDF。用户明确要求“制作安装教程”“教程转PDF”“安装指南转PDF”时使用；不适用于本地 Word、Excel、图片转 PDF。
---

# Article to PDF

Turn a web tutorial article into a print-quality A4 PDF. The author's words are
reproduced as-is; what changes is the packaging: site chrome is stripped,
screenshots are downloaded so the PDF works offline, and the content is
re-typeset for paper.

Use this for tutorial / how-to articles. For other PDF work (forms, extraction,
programmatic generation) use the `pdf` skill instead.

## 触发与成品约定

用户明确要求“制作安装教程”“教程转PDF”“安装指南转PDF”，或点名 `$article-to-pdf` 执行时使用；讨论、引用或转述这些词不执行操作。

成品默认写入 `C:\Users\tianhen\Documents\软件安装指南\`，命名 `<软件名>_<版本>_安装教程.pdf`，不带来源平台或公众号名；用户另行指定时按其要求。完成后刷新 `安装教程索引.csv` 和 `安装教程索引.xlsx`。截图保留原水印，不擅自修图去水印。完整命名与输出规则见 [references/platform-notes.md](references/platform-notes.md)。

本地 Word、Excel、图片转 PDF 使用对应能力，不套用网页文章流程。

## Deliverable

One A4 PDF, written into the user's installation-guide library and named after
the subject unless the user names it. Report the full path, the page count, and
every removal or edit you made. Keep intermediates (page HTML, downloaded
images, wrapper page, QA renders) under `work/<slug>/`.

The library lives outside the task folder on purpose: task folders are named
after the date and the source URL, so a guide left there is hard to find again.
The exact path, the naming rule and the flat-vs-folders convention are in
`references/platform-notes.md` under "Output library".

Once the PDF is in place, refresh the library index so the collection stays
searchable. The CSV is the source of truth; the workbook is the sortable view
the user actually opens (`安装教程索引.csv` and `安装教程索引.xlsx`):

```bash
python scripts/update_index.py --library "<library>" --entry "<file>|<software>|<version>|<url>|<note>"
node scripts/build_index_xlsx.mjs "<library>"
```

Standing preferences of this user: answer in Simplified Chinese, state a short
plan before the real run, keep their files (clean up through
`C:\.agent_trash\YYYY-MM-DD\`, never with a delete command), and confirm before
anything that publishes or sends. Concrete command lines with their wording are
in `references/platform-notes.md`.

## Pipeline

1. **Fetch** the page:
   `curl.exe -sSL -A "<desktop Chrome UA>" -H "Accept-Language: zh-CN,zh;q=0.9" -o page_raw.html <url>`
   CSDN and `mp.weixin.qq.com` both serve the article server-side; no login is
   needed. Rough sizes of a healthy response: CSDN 150 KB+, WeChat 1 MB+.
2. **Extract the article container**:
   `scripts/extract_content.py page_raw.html content_views content.html` (CSDN)
   or `... js_content content.html` (WeChat). It matches closing tags by depth,
   so the whole container comes out of deeply nested markup.
3. **Localize the images**:
   `scripts/download_images.py content.html <work>/images --referer <origin>`.
   It prints a `url<TAB>path` map next to the files. Sanity-check the counts
   before continuing; a wrong count usually means the wrong container.
4. **Decide what to keep**, then write the article-specific rules as a small JS
   file (recipes in `references/platform-notes.md`). Default: the article body
   only - drop like/share controls, comments, recommendation lists, QR codes,
   account-promo graphics and animated GIFs. To tell decorative/promo art apart from real step screenshots, build a numbered thumbnail contact sheet with Pillow (`python -m pip install pillow`); to keep a plain-text section label on the same page as its steps, promote it to `h2.sec`. Both recipes: `references/platform-notes.md`, section "Image contact sheet and orphan section labels".
5. **Assemble the page**: `scripts/build_page.py --content content.html --out
   article.html --title "<title>" --images image_map.txt --css
   assets/print.css [--source-url <url>] [--meta "<byline>"] [--extra-js
   rules.js]`. Add `--footer-note`, `--meta` or `--source-url` only when the user
   explicitly asks for attribution: default PDFs carry no byline and no
   source-URL line (source links live in the library index CSV). Use
   `--no-promote` if the heading heuristics misfire.
6. **Print**: `scripts/print_pdf.mjs article.html <out.pdf> "<headerLeft>"
   "<headerRight>" "<footerLeft>"`, writing `<out.pdf>` straight into the guide
   library. Header and footer text are optional.
7. **Verify every page before delivering** - this step is not optional:
   - `scripts/inspect_layout.mjs article.html` renders the page in print media
     and flags images whose aspect ratio changed (stretched screenshots).
   - Render the PDF with the bundled Poppler (`pdftoppm -png -r 100 <pdf>
     <prefix>`) and actually look at every page: clipped text, images broken
     across pages, stretch, overlap, orphan headings, near-empty last pages.
   - Confirm no leftover site UI and no missing-glyph boxes.

## Hard-won constraints

- **Never put `@page { margin: 0 }` in the CSS.** Chrome then paints the content
  across the whole sheet and the print margins are gone; leave page geometry to
  the print call.
- **Size images with `max-width` + `max-height` only.** An explicit `width`
  together with `max-height` makes Chrome clamp the height while keeping the
  width, squashing the screenshot (about 3% vertically).
- **Raw HTML escapes `&` as `&amp;`, the DOM returns it decoded.** Image maps
  must hold the decoded URL (what `getAttribute` returns). A map built from the
  raw source never matches, and every image is silently dropped.
- **WeChat's `#js_content` starts at `visibility: hidden; opacity: 0`.** The
  wrapper CSS must override both or the article prints blank.
- **Keep article text verbatim.** Do not rewrite, translate, reorder or "fix"
  the author's steps, version numbers or links. If the text looks stale (steps
  that still mention 1.12.1 under a 1.12.3 title), leave it and mention it.
- **Screenshots often carry the author's watermark.** Do not retouch images
  unless the user asks: a watermark sits on top of real content, so removing it
  costs information and needs the user's decision.
- **A PDF open in a viewer is locked.** Writing fails with `EBUSY`; the print
  script writes a temp file and replaces the target, and reports when it stays
  locked so you can ask the user to close the preview.
- **Verify rather than assume.** `Page.printToPDF` can fail after the document
  summary is printed, leaving the previous file in place; confirm the file was
  written and re-render it.
- **Chinese paths and script encodings.** Run file operations that touch Chinese
  paths inline in the current pwsh session: a `.ps1` handed to Windows
  PowerShell 5.1 is decoded as GBK and turns the path into mojibake (it can even
  create a garbage-named folder). Decode child-process output explicitly as
  UTF-8, write CSV for the user as UTF-8 with BOM, and run Python validation
  with `-X utf8` when reading UTF-8 skill files containing Chinese.

## Files

| Path | Purpose |
| --- | --- |
| `scripts/extract_content.py` | Pull an article container (by element id) out of a saved page. |
| `scripts/download_images.py` | Download article images with the right Referer; emit the URL-to-file map. |
| `scripts/build_page.py` | Assemble the print wrapper: content + CSS + image map + optional rules. |
| `scripts/print_pdf.mjs` | Headless Chrome/Edge print with header, footer and page numbers. |
| `scripts/inspect_layout.mjs` | Measure images under print media to catch stretching before printing. |
| `scripts/update_index.py` | Create/refresh the guide-library index CSV (one row per PDF, page counts and dates read back from the files). |
| `scripts/build_index_xlsx.mjs` | Turn that CSV into the sorted, filterable `安装教程索引.xlsx` the user browses. |
| `assets/print.css` | A4 baseline: reset, typography, step headings, image and table rules. |
| `references/platform-notes.md` | CSDN / WeChat specifics, removal recipes, QA checklist, example command lines. |
