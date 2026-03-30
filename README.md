# tinypng-like-compressor

[中文说明](./README_ZH.md)

A local-first batch image compression tool for UI screenshots, diagrams, marketing assets, and cover illustrations. In PNG-heavy workflows, its compression style and size reduction can often get reasonably close to typical TinyPNG output.

> This project is not affiliated with, endorsed by, or connected to TinyPNG.

## Table of Contents

- [Overview](#overview)
- [Capabilities](#capabilities)
- [Use Cases](#use-cases)
- [Example Result](#example-result)
- [How It Works](#how-it-works)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Usage](#cli-usage)
- [Output Rules](#output-rules)
- [Compression Strategy](#compression-strategy)
- [Tool Detection and Fallbacks](#tool-detection-and-fallbacks)
- [Project Structure](#project-structure)
- [Limitations](#limitations)
- [Links](#links)

## Overview

`tinypng-like-compressor` is a pure local batch compression workflow. The goal is not to aggressively squeeze every format with one fixed setting, but to provide a practical, low-friction compression path that works well in real design and content pipelines.

Supported workflows include:

- single file compression
- multiple file compression
- recursive folder processing
- multi-folder batch processing
- automatic keep-the-smaller-result behavior

## Capabilities

- Supports `png`, `jpg`, `jpeg`, `webp`, `avif`
- Recursively scans folders by default, with an option to disable recursion
- Writes output to a new directory or overwrites files in place
- Keeps the original file when recompression is larger
- Detects available local encoders and chooses the best path automatically
- Falls back to Pillow when external tools are missing, with extra JPEG fallback via `sips` on macOS

## Use Cases

- exported PNG screenshots from design tools
- UI icons, dialog screenshots, flowcharts, and diagrams
- article covers and campaign assets
- local offline batch processing for asset folders

If your inputs are mostly already heavily compressed JPEGs, the savings will usually be lower than PNG-heavy cases. That is expected codec behavior.

## Example Result

Original image `example/panda.png`, about `858KB`:

![Original example](./example/panda.png)

Compressed image `example/panda_compressed.png`, about `234KB`:

![Compressed example](./example/panda_compressed.png)

## How It Works

The script detects the input format and then selects the best available compression path from local tools:

1. Scan input files or folders and build a job list.
2. Detect the actual image format instead of trusting only the filename extension.
3. Prefer external encoders when available.
4. Fall back to Pillow or system tools when required.
5. Compare original and compressed sizes, and only write the new file when it is smaller.

The design goal is predictable, practical output rather than format-specific parameter tuning.

## Requirements

- Python 3.9+
- Common local macOS or Linux environment
- Optional encoders: `pngquant`, `oxipng`, `mozjpeg`, `webp`, `libavif`

Installing the full encoder set is recommended for better results.

## Installation

### 1. Create a virtual environment

```bash
python3 -m venv .venv
```

### 2. Install Python dependencies

```bash
./.venv/bin/pip install -r requirements-local.txt
```

### 3. Install optional encoders

Recommended tools:

- `pngquant`
- `oxipng`
- `mozjpeg` (`cjpeg`)
- `webp` (`cwebp`)
- `libavif` (`avifenc`)

On macOS these are commonly installed with Homebrew. On Linux, use your system package manager. They are not all mandatory, but the more complete your toolchain is, the better the compression results tend to be.

## Quick Start

Compress a folder:

```bash
python3 compress_images.py ./images
```

Write output to a dedicated folder:

```bash
python3 compress_images.py ./images -o ./dist_images
```

Overwrite originals in place:

```bash
python3 compress_images.py ./images --in-place
```

Show full help:

```bash
python3 compress_images.py --help
```

## CLI Usage

```bash
python3 compress_images.py INPUT [INPUT ...] [--output OUTPUT_DIR] [--in-place] [--overwrite] [--no-recursive] [--verbose]
```

Arguments:

- `INPUT [INPUT ...]`: one or more image files or folders
- `-o, --output`: output directory
- `--in-place`: write results back to the source files
- `--overwrite`: overwrite existing output files
- `--no-recursive`: only scan the current folder level
- `--verbose`: print one line per processed file

Examples:

Compress a directory:

```bash
python3 compress_images.py ./images
```

Compress multiple directories:

```bash
python3 compress_images.py ./design ./screenshots -o ./compressed_output
```

Compress mixed files and folders:

```bash
python3 compress_images.py ./a.png ./b.jpg ./assets
```

Disable recursive scan:

```bash
python3 compress_images.py ./images --no-recursive
```

Print per-file output:

```bash
python3 compress_images.py ./images --verbose
```

## Output Rules

The default output directory is inferred from the input shape:

- single folder input: sibling directory named `foldername_compressed`
- single file input: sibling directory named `filename_compressed`
- multiple inputs: `./compressed_output`
- multiple folders keep their source folder names inside the output root to avoid collisions

Additional rules:

- existing targets are skipped by default
- use `--overwrite` to replace existing outputs
- `--in-place` and `--output` cannot be used together

## Compression Strategy

- PNG: prefer `pngquant -> oxipng`
- JPEG: prefer `mozjpeg/cjpeg`
- WebP: prefer `cwebp`
- AVIF: prefer `avifenc`

Fallback behavior:

- PNG / WebP / AVIF: fall back to Pillow when external tools are missing
- JPEG: prefer `cjpeg`, then try `sips` on macOS, then fall back to Pillow

## Tool Detection and Fallbacks

At runtime, the script prints the detected status of:

- `pngquant`
- `oxipng`
- `cjpeg`
- `cwebp`
- `avifenc`
- `pillow`

This helps with two things:

- verifying which compression path is actually being used on the current machine
- diagnosing result differences caused by missing local encoders

## Project Structure

```text
.
|-- compress_images.py
|-- requirements-local.txt
|-- README.md
|-- README_EN.md
|-- README_ZH.md
`-- example/
    |-- panda.png
    `-- panda_compressed.png
```

## Limitations

- This is a local CLI tool, not a web service or GUI app
- Compression gains vary a lot by format, with PNG usually being the most stable case
- Already heavily compressed JPEG, WebP, and AVIF inputs may see limited improvement
- Final results depend heavily on which local encoders are installed

If you want the most consistent TinyPNG-like behavior, make sure `pngquant + oxipng + mozjpeg` are available.

## Links

- linuxdo: https://linux.do/
