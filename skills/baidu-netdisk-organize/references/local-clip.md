# 本地图像识别环境（CLIP）

用于：隐私筛查、把纯 CG 与截图分开、按画面聚类减少人工判断量。

**它不认识"原神"这类作品名**，只知道画面长什么样。判断具体作品仍要靠 OCR 读界面文字，或聚类后请用户标注。

## 环境位置

| 项目 | 位置 |
| --- | --- |
| 虚拟环境 | `C:\Users\tianhen\Documents\Codex\_cache\netdisk-organize\venv` |
| Python | 3.11.9（用系统 Python 创建 venv） |
| 模型缓存 | `C:\Users\tianhen\.cache\huggingface`（由 huggingface_hub 管理） |

已装：`torch 2.14.1+cpu`、`torchvision 0.29.1`、`open_clip_torch 3.3.0`、`timm 1.0.30`、`pillow 12.3.0`、`numpy 2.4.6`、`ftfy`、`regex`、`huggingface_hub`。

## 安装命令（重建时用）

```powershell
python -m venv "C:\Users\tianhen\Documents\Codex\_cache\netdisk-organize\venv"
$p = "C:\Users\tianhen\Documents\Codex\_cache\netdisk-organize\venv\Scripts\python.exe"
& $p -m pip install --progress-bar off torch torchvision pillow numpy
& $p -m pip install --progress-bar off open_clip_torch timm ftfy regex huggingface_hub
```

约 150 MB 下载、1.5 GB 磁盘。

## 加载模型

```python
model, _, preprocess = open_clip.create_model_and_transforms(
    "ViT-B-32", pretrained="laion400m_e32")
model.eval()
tokenizer = open_clip.get_tokenizer("ViT-B-32")
```

## 坑（都实际踩过）

1. **必须乘 logit scale 再 softmax**。`(image @ text.T).softmax(-1)` 会得到几乎均匀的分布，看起来像模型坏了。正确写法：

   ```python
   scale = model.logit_scale.exp()          # 实测 100.0
   probs = ((image @ text.T) * scale).softmax(-1)
   ```

2. **别用 `("ViT-B-32-quickgelu", pretrained="openai")`**。在新版 open_clip + torch 上会报 QuickGELU 不匹配，输出退化。改用 `("ViT-B-32", "laion400m_e32")`，实测正常。

3. **不要用清华 PyPI 镜像**。本机系统代理 `127.0.0.1:7890` 会把 `pypi.tuna.tsinghua.edu.cn` 拦掉并报 `ProxyError`；官方 `pypi.org` 走代理正常。

4. HuggingFace 权重下载需设 `HF_ENDPOINT=https://hf-mirror.com` 或保证代理可达；首次下载约 350 MB，耗时约 1 分钟。

5. Windows 上 huggingface_hub 会警告不能建符号链接（未开开发者模式），只是多用点磁盘，不影响使用。可设 `HF_HUB_DISABLE_SYMLINKS_WARNING=1` 静音。

## 性能与用法

- 图像嵌入：CPU 上约 20～30 ms / 张，6743 张约 5～10 分钟。
- 零样本分类：一次编码全部提示词，之后每张图只做一次点积，成本可忽略。
- 聚类用贪心余弦聚类即可（对每个向量，找已有簇心余弦 ≥ 阈值就并入，否则新建簇），不需要 sklearn。
- 建议先跑 200 张小批量看效果，再上全量。

  阈值经验：默认 0.88。实测 0.92 时 24 张出 23 个簇（等于没聚起来）；同一款游戏的界面截图余弦大约落在 0.85～0.95，跨游戏一般低于 0.85。先小批量对比 0.85 / 0.88 / 0.90 三档再定。

  零样本标签实测很好用：游戏截图 0.95～1.00、真人照片 1.00、证件或银行卡 0.96、动漫截图 0.99。少数两类都像的（如"文档扫描件 0.41 / 聊天截图 0.32"）按低置信度处理，送 `不确定`。
