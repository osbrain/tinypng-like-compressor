# tinypng-like-compressor

[English README](./README_EN.md)

一个面向本地工作流的批量图片压缩工具，适合处理 UI 截图、流程图、运营素材、插画首图等常见资源。在 PNG 为主的场景下，压缩风格和体积表现通常可以接近 TinyPNG 的常见输出。

> 本项目与 TinyPNG 无关联、无官方背书，也不是其官方实现。

## 目录

- [项目简介](#项目简介)
- [核心能力](#核心能力)
- [适用场景](#适用场景)
- [示例效果](#示例效果)
- [工作原理](#工作原理)
- [环境要求](#环境要求)
- [安装](#安装)
- [快速开始](#快速开始)
- [命令行用法](#命令行用法)
- [输出规则](#输出规则)
- [压缩策略](#压缩策略)
- [工具探测与回退机制](#工具探测与回退机制)
- [项目结构](#项目结构)
- [限制说明](#限制说明)

## 项目简介

`tinypng-like-compressor` 提供一个纯本地、可批量执行的图片压缩方案，目标不是“统一强压所有格式”，而是在真实设计与内容生产流程中，用更低的接入成本拿到稳定、可接受的体积收益。

项目默认支持：

- 单文件压缩
- 多文件批量压缩
- 单目录递归扫描
- 多目录批量处理
- 压缩结果自动择优保留

## 核心能力

- 支持 `png`、`jpg`、`jpeg`、`webp`、`avif`
- 文件夹默认递归扫描，可关闭递归
- 支持输出到新目录，也支持原地覆盖
- 当压缩后体积不降反升时，自动保留原文件
- 自动探测本地编码器，按可用能力选择最佳压缩链路
- 缺失外部工具时，可回退到 Pillow，macOS 下 JPEG 还可回退到 `sips`

## 适用场景

- 设计稿导出的 PNG 截图
- UI 图标、弹窗、流程图、信息图
- 文章封面图、活动运营图
- 需要在本地离线批量处理的素材目录

如果你的主要素材是已经高度压缩过的 JPEG，收益通常会低于 PNG 场景，这属于编码特性差异，不是脚本异常。

## 示例效果

原图 `example/panda.png`，约 `858KB`：

![Original example](./example/panda.png)

压缩后 `example/panda_compressed.png`，约 `234KB`：

![Compressed example](./example/panda_compressed.png)

## 工作原理

脚本会先识别输入类型，再根据本地可用工具选择对应压缩策略：

1. 扫描输入文件或目录，构建待处理任务列表。
2. 识别图片真实格式，而不是只看扩展名。
3. 优先调用外部编码器执行压缩。
4. 若编码器缺失，则按格式回退到 Pillow 或系统工具。
5. 比较压缩前后体积，仅在结果更小时写入目标路径。

这个设计的核心目标是稳定，而不是在单一格式上追求极限参数。

## 环境要求

- Python 3.9+
- macOS、Linux 常见本地环境
- 可选依赖：`pngquant`、`oxipng`、`mozjpeg`、`webp`、`libavif`

推荐尽量安装完整编码器集合，以获得更接近预期的压缩结果。

## 安装

### 1. 创建虚拟环境

```bash
python3 -m venv .venv
```

### 2. 安装 Python 依赖

```bash
./.venv/bin/pip install -r requirements-local.txt
```

### 3. 安装可选编码器

推荐安装以下工具：

- `pngquant`
- `oxipng`
- `mozjpeg` 提供的 `cjpeg`
- `webp` 提供的 `cwebp`
- `libavif` 提供的 `avifenc`

在 macOS 上通常可以通过 Homebrew 安装；在 Linux 上可通过系统包管理器安装。编码器不是全部强制依赖，但安装越完整，实际效果通常越好。

## 快速开始

压缩一个文件夹：

```bash
python3 compress_images.py ./images
```

输出到指定目录：

```bash
python3 compress_images.py ./images -o ./dist_images
```

原地覆盖源文件：

```bash
python3 compress_images.py ./images --in-place
```

查看完整帮助：

```bash
python3 compress_images.py --help
```

## 命令行用法

```bash
python3 compress_images.py INPUT [INPUT ...] [--output OUTPUT_DIR] [--in-place] [--overwrite] [--no-recursive] [--verbose]
```

参数说明：

- `INPUT [INPUT ...]`：一个或多个图片文件、目录
- `-o, --output`：输出目录
- `--in-place`：直接覆盖原文件
- `--overwrite`：目标文件已存在时允许覆盖
- `--no-recursive`：目录输入时只扫描当前层级
- `--verbose`：输出逐文件处理日志

常见示例：

压缩整个目录：

```bash
python3 compress_images.py ./images
```

同时处理多个目录：

```bash
python3 compress_images.py ./design ./screenshots -o ./compressed_output
```

同时处理多个文件和目录：

```bash
python3 compress_images.py ./a.png ./b.jpg ./assets
```

关闭递归扫描：

```bash
python3 compress_images.py ./images --no-recursive
```

显示逐文件结果：

```bash
python3 compress_images.py ./images --verbose
```

## 输出规则

默认输出目录按输入数量和类型自动推断：

- 单个目录输入：输出到同级 `目录名_compressed`
- 单个文件输入：输出到同级 `文件名_compressed`
- 多输入混合场景：输出到当前目录下 `./compressed_output`
- 多目录同时处理时：保留各自源目录名，避免重名冲突

额外规则：

- 如果目标文件已存在，默认跳过
- 配合 `--overwrite` 可覆盖已有输出
- `--in-place` 与 `--output` 不能同时使用

## 压缩策略

- PNG：优先 `pngquant -> oxipng`
- JPEG：优先 `mozjpeg/cjpeg`
- WebP：优先 `cwebp`
- AVIF：优先 `avifenc`

回退逻辑：

- PNG / WebP / AVIF：外部工具不可用时回退到 Pillow
- JPEG：优先 `cjpeg`，其次在 macOS 下尝试 `sips`，再回退到 Pillow

## 工具探测与回退机制

执行时脚本会打印当前探测到的工具状态，例如：

- `pngquant`
- `oxipng`
- `cjpeg`
- `cwebp`
- `avifenc`
- `pillow`

这有两个作用：

- 帮助确认当前机器实际使用的是哪条压缩链路
- 在压缩结果与预期不一致时，快速定位是否缺少本地编码器

## 项目结构

```text
.
|-- compress_images.py
|-- requirements-local.txt
|-- README.md
|-- README_EN.md
`-- example/
    |-- panda.png
    `-- panda_compressed.png
```

## 限制说明

- 本项目是本地 CLI 工具，不提供 Web 服务或 GUI
- 不同格式的收益差异明显，PNG 通常最稳定
- 对已经高度压缩的 JPEG、WebP、AVIF，二次压缩收益可能有限
- 压缩结果受本地已安装编码器影响较大

如果你希望结果尽量稳定且接近 TinyPNG 风格，优先保证 `pngquant + oxipng + mozjpeg` 可用。
