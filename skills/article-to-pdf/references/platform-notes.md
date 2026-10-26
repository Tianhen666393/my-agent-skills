# Platform notes, removal recipes, QA checklist

Read this when the extraction counts look wrong, when you need to decide what to
strip, or before delivering a PDF.

## CSDN blog posts (`blog.csdn.net`)

- Article container: `div#content_views`. Everything the reader sees is there,
  already server-rendered; no login or JS is required.
- The page contains ~90 `<img>` tags, but only the article images matter: they
  are the ones inside the container and are served from `i-blog.csdnimg.cn`.
  Download with `--referer https://blog.csdn.net/` to be safe.
- Step titles are standalone bold paragraphs (`<p><strong>1.解压…</strong></p>`),
  which the default heading heuristic turns into `h2.sec`. The author sometimes
  wraps image-only paragraphs in `<strong>` too - the cleanup unwraps those
  before promoting headings, so don't pre-process them by hand.
- Below `#content_views` sits site chrome worth ignoring: like/collect buttons,
  comment threads, the recommendation list, and the paid-article overlay.

## WeChat 公众号 posts (`mp.weixin.qq.com/s/...`)

- Article container: `div#js_content`, which carries `style="visibility: hidden;
  opacity: 0;"` until WeChat's own JS reveals it. `assets/print.css` already
  overrides both, but keep that rule if you write your own stylesheet.
- Images live on `mmbiz.qpic.cn` (article graphics) and `mmecoa.qpic.cn`
  (account assets). `--referer https://mp.weixin.qq.com/` works for both.
- Typical junk inside the container: an `mp-common-profile` account card,
  78×57 decorative header art, section-divider graphics, a closing QR-code
  banner, and animated GIFs (a PDF can only show a still frame, so usually drop
  them). Map only the numbered step screenshots and delete the rest by omission.
- The markup is dozens of nested `<section>`s with heavy inline styling. The
  wrapper reset (`#content *`) plus style stripping is what makes it readable;
  never try to keep the original visual design.
- Rows or paragraphs that only promote the account (help-centre links, resource
  indexes, "关注公众号" lines) are usually unwanted. Remove them when the user
  asks for a clean copy; ask first when the text is part of the instructions.

## Removal recipes (`--extra-js`)

The snippet runs inside the cleanup IIFE with `root` (the `#content` element)
and `MAP` in scope.

```js
// drop a table row that only links to the account's album pages
root.querySelectorAll('table tr').forEach(function (tr) {
  var t = tr.textContent.replace(/\s+/g, '');
  if (t.indexOf('下载帮助') >= 0 || t.indexOf('更多内容') >= 0) tr.remove();
});

// drop a specific helper line
root.querySelectorAll('p').forEach(function (p) {
  if (p.textContent.indexOf('文件无法解压') >= 0) p.remove();
});

// 移除清空后的空表格行/空表格（如“软件下载”表格底部的推广行残留）
root.querySelectorAll('tr').forEach(function (tr) {
  if (!tr.textContent.trim() && !tr.querySelector('img, table')) tr.remove();
});
root.querySelectorAll('table').forEach(function (tb) {
  if (!tb.textContent.trim() && !tb.querySelector('img')) tb.remove();
});

// drop every image that is not a numbered screenshot
root.querySelectorAll('img').forEach(function (img) {
  var src = img.getAttribute('src') || '';
  if (!/\/images\/(0[5-9]|1[0-9]|20)\./.test(src)) img.remove();
});
```

## Extra facts worth remembering

- **Map encoding.** `download_images.py` writes decoded URLs because the DOM
  returns decoded attribute values. If you build a map by hand from the raw
  HTML, run it through `html.unescape` first - otherwise `&amp;` never matches
  and every image is dropped without an error.
- **Popper/Poppler for QA.** The bundled runtime ships renderers at
  `%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe`
  (and `pdfinfo.exe`). `pdftoppm -png -r 100 file.pdf page` then inspect the
  PNGs; at 100 dpi one pixel is 1/100 inch, which makes it easy to check the
  0.55in margins and spot bleed-through.
- **A4 geometry.** Paper 8.27 × 11.69 in, margins 0.55 in left/right/top and
  0.62 in bottom, so the content box is ~688 × 1010 CSS px and a `4.7in`
  image cap fits two large screenshots per page.
- **Preview locks.** `outputs/*.pdf` may be open in the app's viewer; the print
  script writes a temp file and retries the replace, and tells you when the
  target stays locked.

## Image contact sheet and orphan section labels

- **图片联系表（用 Pillow 判定装饰图）。** 清理前要区分装饰图/推广图和真正的步骤截图时，用 Pillow 把所有候选图拼成一张带编号的缩略图联系表，一次性目视筛查，比逐张打开快得多。本机已装 Pillow 13.0.0（`python -m pip install pillow`；包在 `C:\Users\tianhen\AppData\Local\Programs\Python\Python311\Lib\site-packages\PIL`）。Pillow 只是本地拼版工具，不进成品；已登记到 AI 工具台账的「共用工具」表。
- **孤儿小节标题要与其内容同页。** 作者的小节标签有时是普通段落（例如「附汉化步骤；」），既不以 `N.` 开头、也没有 `<strong>` 包裹，默认规则不会把它提升成标题，结果容易被排到页面底部、而内容从下一页才开始。在 `--extra-js` 里把这类段落替换成 `<h2 class="sec">…</h2>`（`print.css` 的 `h2.sec` 自带 `break-after: avoid` / `break-inside: avoid`），标题就会和它后面的步骤落在同一页。只改标签的版式，不改文字。

## Output library（成品库：安装指南库）

- 位置：`C:\Users\tianhen\Documents\软件安装指南\`
- 命名：`<软件名>_<版本>_安装教程.pdf`。不带来源平台、公众号名，也不带“汉化版 / 破解”这类来源性后缀；
  同一软件多版本时用版本号区分（如 `Polar_SI9000_安装教程.pdf`、`Typora1.12.3_安装教程.pdf`）。
- 平铺存放，先不要建子目录；超过约 50 份再按类别（PCB/EDA、办公、系统工具）或年份分。
- 中间产物（页面 HTML、下载的图片、包装页、逐页 PNG）留在任务目录的 `work\<slug>\` 下，不要放进成品库。
- 交付回复里给出完整路径、页数，以及本次为清理版面删掉或改写了什么。
- 索引：该目录下有两份文件，**CSV 是数据源，XLSX 是给人看的视图**，两份都由脚本生成，不要手改、也不要手工加行。
  列结构：`软件名, 版本, 文件名, 页数, 原文链接, 生成日期, 备注`。每交付一篇跑这两条：

  ```powershell
  python "$env:SKILL\scripts\update_index.py" --library "C:\Users\tianhen\Documents\软件安装指南" `
    --entry "<文件名>|<软件名>|<版本>|<原文链接>|<备注>"
  node "$env:SKILL\scripts\build_index_xlsx.mjs" "C:\Users\tianhen\Documents\软件安装指南"
  ```

  `update_index.py` 会重扫目录、从 PDF 回读页数、按文件修改时间填生成日期，并保留已填好的元数据；库里的 PDF 即使没提供元数据也会有一行（软件名按文件名推导）。
  `build_index_xlsx.mjs` 生成带表头筛选（表名 `GuideIndex`、冻结首行）的 `安装教程索引.xlsx`，页数写成数字（文本列排序会出现 10 < 17 < 2 的问题）。
- 成品 PDF 页首默认**不加**「作者/发布时间」与「原文链接」行（即不传 `--meta` 和 `--source-url`），需要落款时由用户明确提出；来源信息记录在索引 CSV 的「原文链接」列。（2026-10-21 用户纠正：Acrobat Pro DC2025 首次生成时默认加了这两行，已移除。）
- CSV 必须写成 UTF-8 **with BOM**，否则 Excel/WPS 打开是乱码。
- **不要用 `=HYPERLINK()` 做可点链接**：表格引擎不实现该函数，写进去单元格会变成字符串 `HYPERLINK is not implemented ...`（实测）。原文链接列保持纯文本。
- 表格工具会在工作簿旁生成 `<文件名>.inspect.ndjson` 诊断文件（即使没显式调用 inspect 也会产生）；`build_index_xlsx.mjs` 会自动把它挪到系统临时目录，成品库里只留索引和 PDF。

## Windows 上处理中文路径与编码（踩过的坑）

- **不要把操作写成 .ps1 再交给 Windows PowerShell 5.1**：它按 GBK 解码脚本，脚本内的中文路径会变乱码。实测因此建出过一个乱码名的空目录。当前会话默认 shell 是 pwsh 7（UTF-8），涉及中文路径的命令直接内联执行即可。
- **Python 的 locale 陷阱**：`subprocess.run(..., text=True)` 用系统默认编码解码子进程输出，`pdfinfo` 的输出里含中文时区字样时会抛 `UnicodeDecodeError`；统一显式写 `encoding='utf-8', errors='replace'`。
- **给用户的 CSV 一律 UTF-8 with BOM**（`encoding='utf-8-sig'`），否则中文在 Excel/WPS 里是乱码。
- **skill 校验脚本用系统默认编码读 `SKILL.md`**（本机 GBK），所以 `SKILL.md` 保持纯 ASCII，中文说明放在 references 与 `agents/openai.yaml`。
- **乱码名目录的清理**：用“目录为空 + 名字含私用区字符（U+E000–U+F8FF）”唯一定位，然后移动到 `C:\.agent_trash\YYYY-MM-DD\`，不要删除。当前环境下 `Remove-Item` 会被策略拦截，移动到回收站既是规范要求也是唯一可行的做法。

## Delivery checklist

- [ ] Page count and paper size read back from `pdfinfo` (A4, expected pages).
- [ ] `inspect_layout.mjs` reports no distorted images.
- [ ] Every page rendered as PNG and looked at: no clipped text, no broken
      image/page breaks, no orphan headings, no site UI left over.
- [ ] Article text matches the source, including version numbers and links the
      author wrote; anything removed is reported to the user.
- [ ] No byline/source-URL lines unless the user asked for them: never pass
      `--meta` / `--source-url` by default. Source links live in the index CSV.
- [ ] Deliverable saved under `outputs/`, intermediates under `work/<slug>/`.

## 实测可用的命令序列（中文参数示例）

在任务目录下执行，`$SKILL` 指本 skill 目录：
`C:\Users\tianhen\.codex\skills\article-to-pdf`。

```powershell
New-Item -ItemType Directory -Force -Path work\regress | Out-Null

# 1. 抓页面
curl.exe -sSL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36" `
  -H "Accept-Language: zh-CN,zh;q=0.9" -o work\regress\page_raw.html "<文章链接>"

# 2. 提取正文（微信 js_content，CSDN content_views）
python "$env:SKILL\scripts\extract_content.py" work\regress\page_raw.html js_content work\regress\content.html

# 3. 图片本地化
python "$env:SKILL\scripts\download_images.py" work\regress\content.html work\regress\images `
  --referer https://mp.weixin.qq.com/ --map work\regress\image_map.txt

# 4. 组装打印页（可加 --extra-js 做文章专属清理）
python "$env:SKILL\scripts\build_page.py" --content work\regress\content.html --out work\regress\article.html `
  --title "Typora1.12.3安装教程" --images work\regress\image_map.txt --css "$env:SKILL\assets\print.css" `

# 5. 打印到成品库（页眉左/右、页脚左；不想要就传空串，页脚右侧固定是页码）
node "$env:SKILL\scripts\print_pdf.mjs" work\regress\article.html `
  "C:\Users\tianhen\Documents\软件安装指南\Typora1.12.3_安装教程.pdf" `
  "Typora1.12.3 安装教程" "" ""

# 6. 版式体检 + 逐页渲染
node "$env:SKILL\scripts\inspect_layout.mjs" work\regress\article.html
& "$poppler\pdftoppm.exe" -png -r 100 "C:\Users\tianhen\Documents\软件安装指南\Typora1.12.3_安装教程.pdf" work\regress\page
```

交付件的命名与存放位置见上面「Output library」一节；报告里要说清完整路径、页数，以及为清理版面删掉了哪些内容。
