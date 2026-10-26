#!/usr/bin/env python3
"""百度网盘开放平台最小客户端，供 baidu-netdisk-organize skill 使用。

只用标准库（Python 3.8+）。token 来自 --token 或环境变量
BAIDU_NETDISK_ACCESS_TOKEN。

子命令：
  whoami        查看账号与容量
  ls            列单层目录
  walk          递归列目录（可按 category 过滤，可导出 CSV）
  metas         取文件信息与缩略图链接
  fetch         批量下载缩略图预览
  mkdir         新建文件夹
  move          按 CSV 计划批量移动（服务端操作）
  agent-check   检查 /Agent整理 是否存在、是否有未清理的图片视频
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

API = "https://pan.baidu.com/rest/2.0"
RETRY_ERRNOS = {31034}  # hit frequency limit
UA = "pan.baidu.com"

CAT_VIDEO, CAT_AUDIO, CAT_IMAGE, CAT_DOC, CAT_APP, CAT_OTHER, CAT_BT = range(1, 8)
CATEGORY_NAMES = {
    1: "视频", 2: "音频", 3: "图片", 4: "文档",
    5: "应用", 6: "其他", 7: "种子",
}
AGENT_ROOT = "/Agent整理"
TOKEN_FILE = Path.home() / ".codex" / "baidu_netdisk_token.txt"
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".wmv", ".flv", ".m4v", ".3gp", ".ts", ".rmvb"}


def get_token(args) -> str:
    """token 优先级：--token 参数 > 环境变量 > ~/.codex/baidu_netdisk_token.txt。"""
    tok = getattr(args, "token", None) or os.environ.get("BAIDU_NETDISK_ACCESS_TOKEN")
    if not tok and TOKEN_FILE.exists():
        tok = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not tok:
        sys.exit("缺少 token：按 references/接入与续期.md 重新授权，把 token 写进 "
                 f"{TOKEN_FILE} 或用环境变量 BAIDU_NETDISK_ACCESS_TOKEN")
    return tok


def call(method_path: str, params: dict, data: dict | None = None,
         retries: int = 4, wait: float = 30.0) -> dict:
    """发一次请求，限流和网络异常自动重试。返回解析后的 JSON。

    method_path 以 http 开头时当作完整地址，否则拼在 API 基址后面。
    data 不为空时用 POST 表单提交（create、filemanager 这类接口必须 POST）。
    """
    base = method_path if method_path.startswith("http") else f"{API}/{method_path}"
    query = urllib.parse.urlencode(params, safe="")
    url = f"{base}?{query}"
    body = urllib.parse.urlencode(data, safe="").encode("utf-8") if data else None
    last = None
    for attempt in range(1, retries + 1):
        headers = {"User-Agent": UA}
        if body is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        req = urllib.request.Request(url, data=body, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - 网络层异常统一重试
            last = exc
            print(f"  请求异常({attempt}/{retries}): {exc}", file=sys.stderr)
            time.sleep(wait)
            continue
        if data.get("errno") in RETRY_ERRNOS:
            print(f"  触发限流 errno={data.get('errno')}，{wait:.0f}s 后重试({attempt}/{retries})", file=sys.stderr)
            time.sleep(wait)
            last = data
            continue
        return data
    raise SystemExit(f"重试 {retries} 次仍失败：{last}")


def list_dir(tok: str, path: str, limit: int = 1000) -> tuple[int, list]:
    entries, start = [], 0
    while True:
        data = call("xpan/file", {
            "method": "list", "access_token": tok, "dir": path,
            "order": "name", "limit": limit, "start": start, "web": 1,
        })
        errno = data.get("errno", 0)
        if errno:
            return errno, []
        batch = data.get("list") or []
        entries.extend(batch)
        if len(batch) < limit:
            return 0, entries
        start += limit
        time.sleep(1)


def exists(tok: str, path: str) -> bool:
    errno, _ = list_dir(tok, path, limit=1)
    return errno == 0


def walk(tok: str, path: str, limit: int = 10000, sleep: float = 9.0,
         max_pages: int = 200, quiet: bool = False) -> tuple[list, bool]:
    """递归列出目录下所有条目。返回 (entries, complete)。"""
    entries, start, page = [], 0, 0
    while page < max_pages:
        data = call("xpan/multimedia", {
            "method": "listall", "access_token": tok, "path": path,
            "recursion": 1, "limit": limit, "start": start,
        })
        errno = data.get("errno", 0)
        if errno:
            raise SystemExit(f"listall 失败 errno={errno} errmsg={data.get('errmsg')}")
        batch = data.get("list") or []
        entries.extend(batch)
        page += 1
        if not quiet:
            print(f"  page={page} start={start} 本页={len(batch)} 累计={len(entries)} "
                  f"has_more={data.get('has_more')}", file=sys.stderr)
        if data.get("has_more") != 1:
            return entries, True
        start += limit
        time.sleep(sleep)
    return entries, False


def metas(tok: str, fsids, thumb: bool = True) -> list:
    out = []
    ids = [str(x) for x in fsids]
    # 一批最多 50 个 fsid：100 个拼出来的 URL 会超过服务器长度限制，报 HTTP 400
    for i in range(0, len(ids), 50):
        batch = ids[i:i + 50]
        # fsids 必须是纯数字数组。写成 ["123","456"] 会返回 HTTP 400 fsids error
        fsids_json = "[" + ",".join(str(int(x)) for x in batch) + "]"
        data = call("xpan/multimedia", {
            "method": "filemetas", "access_token": tok,
            "fsids": fsids_json, "thumb": 1 if thumb else 0, "dlink": 0,
        })
        errno = data.get("errno", 0)
        if errno:
            raise SystemExit(f"filemetas 失败 errno={errno} errmsg={data.get('errmsg')}")
        out.extend(data.get("list") or [])
        if i + 50 < len(ids):
            time.sleep(3)
    return out


def thumb_url(item: dict, size: int = 1600) -> str | None:
    """取缩略图链接。filemetas 返回的 thumbs 是字典 {icon,url1..url4}，也兼容数组形式。"""
    thumbs = item.get("thumbs") or {}
    if isinstance(thumbs, list):
        thumbs = thumbs[0] if thumbs else {}
    if not thumbs:
        return None
    url = thumbs.get("url3") or thumbs.get("url2") or thumbs.get("url1")
    if not url:
        return None
    return re.sub(r"size=c\d+_u\d+", f"size=c{size}_u{size}", url)


def download(url: str, dest: Path) -> bool:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            dest.write_bytes(resp.read())
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  下载失败 {dest.name}: {exc}", file=sys.stderr)
        return False


def read_rows(path: str) -> list:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def write_rows(path: str, rows: list, fields: list) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def is_video(item: dict) -> bool:
    return item.get("category") == CAT_VIDEO or \
        Path(item.get("server_filename", "")).suffix.lower() in VIDEO_EXT


# ---------------------------------------------------------------- commands

def cmd_whoami(args):
    tok = get_token(args)
    info = call("xpan/nas", {"method": "uinfo", "access_token": tok})
    quota = call("https://pan.baidu.com/api/quota",
                 {"access_token": tok, "checkfree": 1, "checkexpire": 1})
    summary = {
        "账号": info.get("baidu_name"),
        "会员类型": info.get("vip_type"),
    }
    if quota.get("errno") == 0:
        summary["已用GB"] = round((quota.get("used") or 0) / 2**30, 2)
        summary["总容量GB"] = round((quota.get("total") or 0) / 2**30, 2)
    else:
        summary["容量查询"] = f"失败 errno={quota.get('errno')}"
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def cmd_ls(args):
    tok = get_token(args)
    errno, entries = list_dir(tok, args.dir)
    if errno:
        sys.exit(f"列目录失败 errno={errno}（目录可能不存在）")
    for item in entries:
        kind = "DIR " if item.get("isdir") else f"cat{item.get('category')}"
        print(f"{kind}\t{item.get('server_filename')}\t{item.get('size')}")
    print(f"共 {len(entries)} 项", file=sys.stderr)


def cmd_walk(args):
    tok = get_token(args)
    entries, complete = walk(tok, args.dir)
    rows = entries
    if args.category:
        wanted = {int(x) for x in str(args.category).split(",")}
        rows = [e for e in entries if e.get("category") in wanted]
    if args.out:
        write_rows(args.out, rows,
                   ["fs_id", "path", "server_filename", "size", "md5",
                    "server_mtime", "category"])
        print(f"已写出 {args.out}（{len(rows)} 条）")
    else:
        for item in rows[:args.limit]:
            print(f"{item.get('category')}\t{item.get('path')}\t{item.get('size')}")
    if not complete:
        print("警告：未扫完（达到页数上限），结果可能不完整", file=sys.stderr)


def cmd_metas(args):
    tok = get_token(args)
    ids = args.fsids.split(",")
    for item in metas(tok, ids, thumb=True):
        print(f"{item.get('fs_id')}\t{item.get('path')}\t{thumb_url(item, args.size) or '(无缩略图)'}")


def cmd_fetch(args):
    tok = get_token(args)
    rows = read_rows(args.from_csv)
    if args.limit:
        rows = rows[:args.limit]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ids = [str(r["fs_id"]) for r in rows]
    todo = []
    for i in range(0, len(ids), 50):
        batch = ids[i:i + 50]
        for item in metas(tok, batch):
            url = thumb_url(item, args.size)
            if url:
                todo.append((url, out_dir / f"{item['fs_id']}.jpg"))
        print(f"  取链接 {min(i + 50, len(ids))}/{len(ids)}", file=sys.stderr)

    ok = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(lambda pair: download(*pair), todo):
            ok += 1 if result else 0
    print(f"下载完成：{ok}/{len(todo)} -> {out_dir}")


def cmd_mkdir(args):
    tok = get_token(args)
    data = call("xpan/file", {
        "method": "create", "access_token": tok,
    }, data={"path": args.path, "size": 0, "isdir": 1, "rtype": args.rtype})
    errno = data.get("errno", 0)
    if errno == 0:
        print(f"已创建 {args.path}")
    elif errno in (-8, -9, 31066):  # 已存在
        print(f"已存在 {args.path}")
    else:
        sys.exit(f"创建失败 errno={errno} errmsg={data.get('errmsg')}")


def cmd_move(args):
    tok = get_token(args)
    rows = read_rows(args.from_csv)
    log, batch_size = [], 100
    def do_move(entries):
        """返回 (顶部errno, 未成功的条目)。filemanager 的逐文件结果在 info 里。"""
        filelist = [{"path": e["path"], "dest": e["dest"], "newname": e["newname"]}
                    for e in entries]
        resp = call("xpan/file", {
            "method": "filemanager", "access_token": tok, "opera": "move",
        }, data={"async": 0, "ondup": args.ondup, "filelist": json.dumps(filelist)})
        info = resp.get("info") or []
        bad = []
        for idx, e in enumerate(entries):
            per = info[idx].get("errno") if idx < len(info) else None
            if per != 0:
                bad.append(e)
        return resp.get("errno", 0), bad

    for i in range(0, len(rows), batch_size):
        chunk = rows[i:i + batch_size]
        if args.per_file:
            for e in chunk:
                bad = [e]
                for _try in range(3):          # 单次移动不稳定，失败就重试
                    _, bad = do_move([e])
                    if not bad:
                        break
                    time.sleep(1.0)
                log.append({"path": e["path"], "dest": e["dest"], "newname": e["newname"],
                            "errno": 0 if not bad else -1})
                if len(log) % 50 == 0:
                    print(f"  逐个移动 {len(log)}/{len(rows)}", file=sys.stderr)
                time.sleep(args.sleep)
            continue
        errno, bad = do_move(chunk)
        fixed = 0
        for e in bad:
            time.sleep(1.5)
            _, still = do_move([e])
            if not still:
                fixed += 1
        print(f"  移动 {min(i + batch_size, len(rows))}/{len(rows)} errno={errno} "
              f"批量未成功 {len(bad)}，逐个重试成功 {fixed}", file=sys.stderr)
        bad_paths = {e["path"] for e in bad}
        for r in chunk:
            log.append({"path": r["path"], "dest": r["dest"], "newname": r["newname"],
                        "errno": (errno if r["path"] not in bad_paths else -1)})
        time.sleep(args.sleep)
    if args.log:
        write_rows(args.log, log, ["path", "dest", "newname", "errno"])
        print(f"已写出移动日志 {args.log}")


def cmd_agent_check(args):
    tok = get_token(args)
    root = args.root
    if not exists(tok, root):
        print(f"RESULT=missing\n{root} 不存在，需要创建。")
        return
    print(f"RESULT=exists\n{root} 已存在，正在统计残留……")
    entries, complete = walk(tok, root, quiet=True)
    files = [e for e in entries if not e.get("isdir")]
    images = [e for e in files if e.get("category") == CAT_IMAGE]
    videos = [e for e in files if is_video(e)]
    others = [e for e in files if e not in images and e not in videos]
    print(f"图片={len(images)} 视频={len(videos)} 其他={len(others)}"
          f"{'' if complete else '（未扫完）'}")
    groups: dict[str, list] = {}
    for item in images + videos:
        parts = item.get("path", "").split("/")
        key = parts[2] if len(parts) > 2 else "(根)"
        groups.setdefault(key, []).append(item)
    for key, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        n_img = sum(1 for x in items if x.get("category") == CAT_IMAGE)
        n_vid = len(items) - n_img
        print(f"  {key}: 图片 {n_img} / 视频 {n_vid}")
    if images or videos:
        print("RESULT=blocked\n存在未清理的图片或视频：提醒用户先清理，等他确认后再动手。")
    else:
        print("RESULT=clean\n可以开始整理。")


SPECIAL_EXT = {
    ".psd", ".ai", ".cdr", ".prproj", ".aep", ".sch", ".pcb", ".brd", ".step", ".stp",
    ".zip", ".rar", ".7z", ".tar", ".gz", ".iso", ".exe", ".msi", ".apk", ".dmg",
    ".db", ".sqlite", ".sql", ".mdb", ".bak", ".ttf", ".otf", ".woff",
    ".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".cs", ".ipynb", ".json", ".xml",
    ".vhd", ".vhdx", ".qcow2", ".torrent", ".key", ".pem",
}


def cmd_survey(args):
    """勘察目标文件夹：类型分布、目录结构、体量、默认桶覆盖不到的特殊类型。"""
    tok = get_token(args)
    entries, complete = walk(tok, args.dir, quiet=True)
    # listall 会把同一条目重复列出 2~4 次，统计前必须按 path 去重
    raw_n = len(entries)
    uniq = {}
    for e in entries:
        uniq.setdefault(e.get("path"), e)
    entries = list(uniq.values())
    files = [e for e in entries if e.get("md5")]
    dirs = [e for e in entries if not e.get("md5")]
    total = sum(int(e.get("size") or 0) for e in files)
    print(f"目录：{args.dir}")
    if raw_n != len(entries):
        print(f"接口返回 {raw_n} 条，按路径去重后 {len(entries)} 条（已剔除 {raw_n - len(entries)} 条重复列表）")
    print(f"文件 {len(files)} 个，子目录 {len(dirs)} 个，合计 {total / 2**30:.2f} GB")
    print(f"扫完：{'是' if complete else '否（结果可能不全）'}")

    print("\n按 category：")
    for code, n in collections.Counter(e.get("category") for e in files).most_common():
        print(f"  {CATEGORY_NAMES.get(code, code)} ({code}): {n}")

    print("\n按扩展名 Top 15：")
    ext_counter = collections.Counter(
        Path(e.get("server_filename", "")).suffix.lower() or "(无)" for e in files)
    for ext, n in ext_counter.most_common(15):
        print(f"  {ext}: {n}")

    print("\n一级子目录文件数 Top 15：")
    root = args.dir.rstrip("/")
    tops = collections.Counter()
    for e in files:
        rel = e.get("path", "")[len(root):].strip("/")
        tops[rel.split("/")[0] if "/" in rel else "(根目录)"] += 1
    for name, n in tops.most_common(15):
        print(f"  {name}: {n}")

    print("\n最大的 5 个文件：")
    for e in sorted(files, key=lambda x: -int(x.get("size") or 0))[:5]:
        print(f"  {int(e.get('size') or 0) / 2**20:.1f} MB  {e.get('path')}")

    special = [e for e in files
               if Path(e.get("server_filename", "")).suffix.lower() in SPECIAL_EXT]
    print()
    if special:
        print(f"!! 发现 {len(special)} 个特殊类型文件，默认桶覆盖不到，需要跟用户单独定分类：")
        sc = collections.Counter(Path(e.get("server_filename", "")).suffix.lower()
                                 for e in special)
        for ext, n in sc.most_common(20):
            print(f"  {ext}: {n}")
    else:
        print("未发现默认桶覆盖不到的特殊类型。")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="百度网盘整理辅助工具")
    parser.add_argument("--token", help="access_token（默认读 BAIDU_NETDISK_ACCESS_TOKEN）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("whoami", help="账号与容量").set_defaults(func=cmd_whoami)

    p = sub.add_parser("ls", help="列单层目录")
    p.add_argument("--dir", required=True)
    p.set_defaults(func=cmd_ls)

    p = sub.add_parser("walk", help="递归列目录")
    p.add_argument("--dir", required=True)
    p.add_argument("--category", help="按 category 过滤，逗号分隔，如 1,3")
    p.add_argument("--out", help="导出 CSV")
    p.add_argument("--limit", type=int, default=50, help="不导出时打印的条数")
    p.set_defaults(func=cmd_walk)

    p = sub.add_parser("metas", help="取文件信息与缩略图链接")
    p.add_argument("--fsids", required=True, help="逗号分隔的 fs_id")
    p.add_argument("--size", type=int, default=1600)
    p.set_defaults(func=cmd_metas)

    p = sub.add_parser("fetch", help="批量下载缩略图预览")
    p.add_argument("--from-csv", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--size", type=int, default=1600)
    p.add_argument("--limit", type=int)
    p.add_argument("--workers", type=int, default=8)
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("mkdir", help="新建文件夹")
    p.add_argument("--path", required=True)
    p.add_argument("--rtype", type=int, default=0,
                   help="0=重名直接返回冲突（幂等，默认）；1=重名自动改名，会导致多出 <名字>_日期时间 的目录")
    p.set_defaults(func=cmd_mkdir)

    p = sub.add_parser("move", help="按 CSV 批量移动（列：path,dest,newname）")
    p.add_argument("--from-csv", required=True)
    p.add_argument("--log", help="写出移动日志 CSV")
    p.add_argument("--ondup", default="fail",
                   choices=["fail", "newcopy", "overwrite", "skip"])
    p.add_argument("--sleep", type=float, default=8.0)
    p.add_argument("--per-file", action="store_true",
                   help="逐个移动。批量在多文件且目标不同时不可靠（会把文件塞进某个目标并保留原目录结构），"
                        "出过事故后一律用这个模式")
    p.set_defaults(func=cmd_move)

    p = sub.add_parser("agent-check", help="检查 Agent整理 目录")
    p.add_argument("--root", default=AGENT_ROOT)
    p.set_defaults(func=cmd_agent_check)

    p = sub.add_parser("survey", help="勘察目标文件夹：类型分布/结构/体量/特殊类型")
    p.add_argument("--dir", required=True)
    p.set_defaults(func=cmd_survey)
    return parser


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
