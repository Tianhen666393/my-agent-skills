#!/usr/bin/env python3
"""对整批预览图跑本机 OCR，抽文字并匹配作品关键词。

用法：
  python ocr_tag.py --list <图片清单.csv> --dir <预览图目录>
                    --out <结果.csv> --text-out <全文.jsonl>
                    [--keywords <kw.json>] [--limit N] [--workers 4]

清单 CSV 需要含 fs_id 与 path 两列（bdpan.py walk 导出的即可）。
关键词 JSON 形如 {"原神": ["原神","祈愿",...], ...}，不传则用内置表。
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import sys
import time

DEFAULT_KEYWORDS = {
    "原神": ["原神", "祈愿", "摩拉", "神瞳", "璃月", "稻妻", "须弥", "枫丹", "纳塔",
             "冒险等阶", "派蒙", "深渊", "传说任务"],
    "崩坏：星穹铁道": ["星穹铁道", "遗器", "光锥", "星琼", "开拓者", "跃迁", "星轨",
                       "存护", "同谐", "巡猎", "毁灭", "模拟宇宙"],
    "绝区零": ["绝区零", "频段", "音擎", "邦布", "代理人", "绳匠", "空洞"],
    "明日方舟": ["明日方舟", "HYPERGRYPH", "泰拉", "干员", "寻访", "罗德岛", "源石",
                 "集成战略", "作战", "理智"],
    "碧蓝航线": ["碧蓝航线", "塞壬", "舰船", "指挥喵", "建造"],
    "鸣潮": ["鸣潮", "声骸", "共鸣", "漂泊者", "今州"],
    "崩坏3": ["崩坏3", "舰长", "女武神", "无限", "深渊"],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", required=True)
    ap.add_argument("--dir", required=True, help="预览图目录，文件名为 <fs_id>.jpg")
    ap.add_argument("--out", required=True)
    ap.add_argument("--text-out", required=True)
    ap.add_argument("--keywords")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    import winocr
    from PIL import Image

    keywords = DEFAULT_KEYWORDS
    if args.keywords:
        with open(args.keywords, encoding="utf-8") as fh:
            keywords = json.load(fh)

    with open(args.list, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if args.limit:
        rows = rows[:args.limit]

    sem = asyncio.Semaphore(args.workers)
    done = [0]
    t0 = time.time()

    async def one(row):
        path = os.path.join(args.dir, row["fs_id"] + ".jpg")
        async with sem:
            if not os.path.exists(path):
                return {"fs_id": row["fs_id"], "path": row["path"], "text": "",
                        "hits": "", "chars": 0}
            try:
                res = await winocr.recognize_pil(Image.open(path), "zh-Hans")
                text = "".join(line.text for line in res.lines).replace(" ", "")
            except Exception:  # noqa: BLE001
                text = ""
        hits = [g for g, kws in keywords.items() if any(k in text for k in kws)]
        done[0] += 1
        if done[0] % 250 == 0:
            print(f"  {done[0]}/{len(rows)}  {time.time() - t0:.0f}s", file=sys.stderr)
        return {"fs_id": row["fs_id"], "path": row["path"], "text": text,
                "hits": "|".join(hits), "chars": len(text)}

    async def run():
        return await asyncio.gather(*[one(r) for r in rows])

    results = asyncio.run(run())

    with open(args.text_out, "w", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(args.out, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=["fs_id", "path", "hits", "chars"])
        w.writeheader()
        for r in results:
            w.writerow({"fs_id": r["fs_id"], "path": r["path"],
                        "hits": r["hits"], "chars": r["chars"]})

    n_hit = sum(1 for r in results if r["hits"])
    n_text = sum(1 for r in results if r["chars"] >= 4)
    print(f"完成 {len(results)} 张，用时 {time.time() - t0:.0f}s；"
          f"有文字 {n_text} 张，命中关键词 {n_hit} 张", file=sys.stderr)
    print(f"结果 {args.out}，全文 {args.text_out}", file=sys.stderr)


if __name__ == "__main__":
    main()
