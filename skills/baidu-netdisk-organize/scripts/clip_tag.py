#!/usr/bin/env python3
"""用本地 CLIP 给一批预览图打零样本标签并做贪心聚类。

用法：
  python clip_tag.py --dir <预览图目录> --out <结果.csv> [--labels <labels.json>]
                     [--threshold 0.92] [--limit N]

输出 CSV 列：file, top1, top1_prob, top2, top2_prob, cluster, cluster_size

注意：相似度必须先乘 model.logit_scale.exp() 再 softmax，否则分布近乎均匀。
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys
import time

DEFAULT_LABELS = {
    "游戏截图": "a screenshot of a video game",
    "抽卡或概率界面": "a screenshot of a gacha pull or loot box result screen",
    "角色属性面板": "a screenshot of a character stat or equipment panel in a game",
    "动漫截图": "a frame from an anime",
    "真人照片": "a photo of a person taken with a camera",
    "风景照": "a landscape photo",
    "文档扫描件": "a scanned document or paper with text",
    "成绩单或表格": "a school report card or a table of grades",
    "证件或银行卡": "a photo of an ID card or bank card",
    "发票或收据": "a photo of a receipt or invoice",
    "聊天截图": "a screenshot of a text chat conversation",
    "网页或应用界面": "a screenshot of a web page or app interface",
    "金融行情界面": "a screenshot of a stock market or finance app",
    "手绘插画": "a hand-drawn illustration",
    "3D建模界面": "a screenshot of 3D modeling software like Blender or Maya",
    "表情包或梗图": "a meme or reaction image with text",
}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--dir", required=True, help="预览图目录")
    p.add_argument("--out", required=True, help="输出 CSV")
    p.add_argument("--labels", help="自定义标签 JSON：{显示名: 英文提示词}")
    p.add_argument("--threshold", type=float, default=0.88,
                   help="聚类余弦阈值，越低簇越少。0.92 会几乎每张一个簇，先小批量试再定")
    p.add_argument("--limit", type=int, default=0, help="只处理前 N 张，0 表示全部")
    p.add_argument("--batch", type=int, default=16)
    return p.parse_args()


def main():
    args = parse_args()
    import torch
    import open_clip
    from PIL import Image

    labels = DEFAULT_LABELS
    if args.labels:
        with open(args.labels, encoding="utf-8") as fh:
            labels = json.load(fh)
    names = list(labels)
    prompts = [labels[n] for n in names]

    files = sorted(
        sum([glob.glob(os.path.join(args.dir, ext))
             for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp", "*.bmp")], [])
    )
    if args.limit:
        files = files[:args.limit]
    if not files:
        sys.exit(f"{args.dir} 下没有图片")
    print(f"待处理 {len(files)} 张，标签 {len(names)} 个", file=sys.stderr)

    t0 = time.time()
    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32", pretrained="laion400m_e32")
    model.eval()
    tokenizer = open_clip.get_tokenizer("ViT-B-32")
    scale = model.logit_scale.exp()
    print(f"模型加载 {time.time() - t0:.1f}s", file=sys.stderr)

    with torch.no_grad():
        text = model.encode_text(tokenizer(prompts))
        text = text / text.norm(dim=-1, keepdim=True)

    # 贪心余弦聚类
    centroids: list = []
    counts: list[int] = []
    rows = []

    done = 0
    step = max(1, args.batch)
    for s in range(0, len(files), step):
        chunk = files[s:s + step]
        tensors, kept = [], []
        for f in chunk:
            try:
                tensors.append(preprocess(Image.open(f).convert("RGB")))
                kept.append(f)
            except Exception as exc:  # noqa: BLE001
                print(f"  跳过 {os.path.basename(f)}: {exc}", file=sys.stderr)
        if not tensors:
            continue
        with torch.no_grad():
            vecs = model.encode_image(torch.stack(tensors))
            vecs = vecs / vecs.norm(dim=-1, keepdim=True)
            probs = ((vecs @ text.T) * scale).softmax(-1)
        for f, vec, prob in zip(kept, vecs, probs):
            top = prob.topk(2)
            best, best_sim = -1, args.threshold
            for idx, cent in enumerate(centroids):
                sim = float(vec @ cent)
                if sim >= best_sim:
                    best, best_sim = idx, sim
            if best < 0:
                centroids.append(vec)
                counts.append(1)
                best = len(centroids) - 1
            else:
                counts[best] += 1
            rows.append({
                "file": os.path.basename(f),
                "top1": names[int(top.indices[0])],
                "top1_prob": round(float(top.values[0]), 3),
                "top2": names[int(top.indices[1])],
                "top2_prob": round(float(top.values[1]), 3),
                "cluster": best,
            })
            done += 1
        if done % 1000 < step:
            print(f"  已处理 {done}/{len(files)}  用时 {time.time() - t0:.0f}s "
                  f"簇数 {len(centroids)}", file=sys.stderr)

    for row in rows:
        row["cluster_size"] = counts[row["cluster"]]

    with open(args.out, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["file", "top1", "top1_prob", "top2", "top2_prob",
                            "cluster", "cluster_size"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"完成：{len(rows)} 张，{len(centroids)} 个簇，用时 {time.time() - t0:.0f}s",
          file=sys.stderr)
    print(f"结果写入 {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
