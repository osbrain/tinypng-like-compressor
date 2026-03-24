#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

try:
    from PIL import Image
except Exception:
    Image = None


SUPPORTED = {".png", ".jpg", ".jpeg", ".webp", ".avif"}
JPEG_QUALITY = 78
JPEG_FALLBACK_QUALITY = 68


@dataclass
class Tools:
    pngquant: str | None
    oxipng: str | None
    cjpeg: str | None
    cwebp: str | None
    avifenc: str | None


@dataclass(frozen=True)
class CompressionJob:
    src: Path
    dest: Path
    display_name: str


def detect_tools() -> Tools:
    return Tools(
        pngquant=shutil.which("pngquant"),
        oxipng=shutil.which("oxipng"),
        cjpeg=shutil.which("cjpeg"),
        cwebp=shutil.which("cwebp"),
        avifenc=shutil.which("avifenc"),
    )


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def format_size(num: int) -> str:
    value = float(num)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{num}B"


def atomic_replace_if_smaller(candidate: Path, original: Path, dest: Path) -> tuple[bool, int, int]:
    before = original.stat().st_size
    after = candidate.stat().st_size
    dest.parent.mkdir(parents=True, exist_ok=True)
    if after >= before:
        shutil.copy2(original, dest)
        return False, before, before
    shutil.move(str(candidate), str(dest))
    return True, before, after


def pillow_required() -> None:
    if Image is None:
        raise RuntimeError("Pillow is not installed. Install it with: pip install -r requirements-local.txt")


def convert_with_sips(src: Path, dest: Path, fmt: str, format_options: int | None = None) -> bool:
    sips = shutil.which("sips")
    if not sips:
        return False
    cmd = [sips, "-s", "format", fmt]
    if format_options is not None:
        cmd.extend(["-s", "formatOptions", str(format_options)])
    cmd.extend([str(src), "--out", str(dest)])
    try:
        run(cmd)
        return True
    except subprocess.CalledProcessError:
        return False


def ensure_rgb_jpeg(src: Path, dest: Path) -> None:
    if convert_with_sips(src, dest, "jpeg"):
        return

    pillow_required()
    with Image.open(src) as img:
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.save(dest, format="JPEG", quality=100)


def reencode_jpeg_with_sips(src: Path, dest: Path, quality: int) -> bool:
    return convert_with_sips(src, dest, "jpeg", format_options=quality)


def sniff_format_from_header(src: Path) -> str | None:
    with src.open("rb") as fh:
        header = fh.read(32)

    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if header.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "WEBP"
    if len(header) >= 12 and header[4:8] == b"ftyp" and b"avif" in header[8:16]:
        return "AVIF"
    return None


def detect_actual_format(src: Path) -> str:
    fmt = sniff_format_from_header(src)
    if fmt is not None:
        return fmt

    ext = src.suffix.lower()
    if ext in {".jpg", ".jpeg"}:
        return "JPEG"
    if ext == ".png":
        return "PNG"
    if ext == ".webp":
        return "WEBP"
    if ext == ".avif":
        return "AVIF"

    if Image is not None:
        with Image.open(src) as img:
            fmt = (img.format or "").upper()
        if fmt in {"JPEG", "PNG", "WEBP", "AVIF"}:
            return fmt

    raise ValueError(f"Unsupported or unreadable file: {src}")


def compress_png(src: Path, dest: Path, tools: Tools) -> tuple[bool, int, int]:
    with tempfile.TemporaryDirectory() as tmpdir:
        work = Path(tmpdir) / "stage.png"
        if tools.pngquant:
            cmd = [
                tools.pngquant,
                "--quality=80-98",
                "--speed",
                "1",
                "--strip",
                "--skip-if-larger",
                "--force",
                "--output",
                str(work),
                str(src),
            ]
            try:
                run(cmd)
            except subprocess.CalledProcessError as exc:
                if exc.returncode == 98:
                    shutil.copy2(src, work)
                else:
                    raise
        else:
            pillow_required()
            with Image.open(src) as img:
                if img.mode in ("RGBA", "LA"):
                    img = img.quantize(colors=256, method=Image.Quantize.FASTOCTREE)
                else:
                    if img.mode not in ("RGB", "L", "P"):
                        img = img.convert("RGB")
                    img = img.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
                img.save(work, format="PNG", optimize=True, compress_level=9)

        if tools.oxipng:
            run([tools.oxipng, "-o", "max", "--strip", "safe", str(work)])

        return atomic_replace_if_smaller(work, src, dest)


def compress_jpeg(src: Path, dest: Path, tools: Tools) -> tuple[bool, int, int]:
    with tempfile.TemporaryDirectory() as tmpdir:
        work = Path(tmpdir) / "stage.jpg"
        if tools.cjpeg and Image is not None:
            ppm = Path(tmpdir) / "stage.ppm"
            with Image.open(src) as img:
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                img.save(ppm, format="PPM")
            run(
                [
                    tools.cjpeg,
                    "-quality",
                    str(JPEG_QUALITY),
                    "-progressive",
                    "-optimize",
                    "-outfile",
                    str(work),
                    str(ppm),
                ]
            )
        elif reencode_jpeg_with_sips(src, work, quality=JPEG_FALLBACK_QUALITY):
            pass
        else:
            pillow_required()
            with Image.open(src) as img:
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                img.save(work, format="JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)

        return atomic_replace_if_smaller(work, src, dest)


def compress_webp(src: Path, dest: Path, tools: Tools) -> tuple[bool, int, int]:
    with tempfile.TemporaryDirectory() as tmpdir:
        work = Path(tmpdir) / "stage.webp"
        if tools.cwebp:
            run([tools.cwebp, "-q", "80", "-m", "6", "-mt", str(src), "-o", str(work)])
        else:
            pillow_required()
            with Image.open(src) as img:
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGBA" if "A" in img.mode else "RGB")
                img.save(work, format="WEBP", quality=80, method=6)

        return atomic_replace_if_smaller(work, src, dest)


def compress_avif(src: Path, dest: Path, tools: Tools) -> tuple[bool, int, int]:
    with tempfile.TemporaryDirectory() as tmpdir:
        work = Path(tmpdir) / "stage.avif"
        if tools.avifenc:
            run([tools.avifenc, "--min", "24", "--max", "34", "-s", "6", str(src), str(work)])
        else:
            pillow_required()
            with Image.open(src) as img:
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGBA" if "A" in img.mode else "RGB")
                img.save(work, format="AVIF", quality=55)

        return atomic_replace_if_smaller(work, src, dest)


def compress_one(src: Path, dest: Path, tools: Tools) -> tuple[bool, int, int]:
    actual = detect_actual_format(src)
    if actual == "PNG":
        return compress_png(src, dest, tools)
    if actual == "JPEG":
        return compress_jpeg(src, dest, tools)
    if actual == "WEBP":
        return compress_webp(src, dest, tools)
    if actual == "AVIF":
        return compress_avif(src, dest, tools)
    raise ValueError(f"Unsupported file: {src}")


def is_supported_image(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED


def iter_images(root: Path, recursive: bool) -> list[Path]:
    walker = root.rglob("*") if recursive else root.glob("*")
    return sorted(path for path in walker if is_supported_image(path))


def sanitize_name(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in name).strip("._") or "images"


def default_output_dir(inputs: list[Path]) -> Path:
    if len(inputs) == 1:
        base = inputs[0]
        if base.is_dir():
            return base.parent / f"{base.name}_compressed"
        return base.parent / f"{base.stem}_compressed"
    return Path.cwd() / "compressed_output"


def ensure_distinct_outputs(jobs: list[CompressionJob]) -> None:
    seen: dict[Path, Path] = {}
    for job in jobs:
        if job.dest in seen and seen[job.dest] != job.src:
            raise ValueError(f"Output path collision: {job.src} and {seen[job.dest]} -> {job.dest}")
        seen[job.dest] = job.src


def collect_jobs(inputs: list[Path], output: Path | None, in_place: bool, recursive: bool) -> list[CompressionJob]:
    jobs: list[CompressionJob] = []
    resolved_inputs = [path.resolve() for path in inputs]
    output_root = None if in_place else (output.resolve() if output else default_output_dir(resolved_inputs).resolve())

    for src_root in resolved_inputs:
        if not src_root.exists():
            raise FileNotFoundError(f"Input not found: {src_root}")

        if src_root.is_file():
            if not is_supported_image(src_root):
                continue
            if in_place:
                dest = src_root
            else:
                assert output_root is not None
                if len(resolved_inputs) == 1 and src_root.is_file():
                    dest = output_root / src_root.name
                else:
                    dest = output_root / sanitize_name(src_root.parent.name) / src_root.name
            jobs.append(CompressionJob(src=src_root, dest=dest, display_name=src_root.name))
            continue

        files = iter_images(src_root, recursive=recursive)
        for file_path in files:
            rel = file_path.relative_to(src_root)
            if in_place:
                dest = file_path
            else:
                assert output_root is not None
                if len(resolved_inputs) == 1:
                    dest = output_root / rel
                else:
                    dest = output_root / src_root.name / rel
            jobs.append(CompressionJob(src=file_path, dest=dest, display_name=str(file_path.relative_to(src_root))))

    ensure_distinct_outputs(jobs)
    return jobs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Batch image compression for files or folders. Supports recursive processing out of the box."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="One or more image files or folders. Folders are scanned recursively by default.",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output folder. Defaults to '<input>_compressed' for single input, or './compressed_output' for multiple inputs.",
    )
    parser.add_argument("--in-place", action="store_true", help="Write results back to the original files.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files.")
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="When input is a folder, only scan the current level and skip subfolders.",
    )
    parser.add_argument("--verbose", action="store_true", help="Print one result line per file.")
    return parser


def print_detected_tools(tools: Tools) -> None:
    print("Detected tools:")
    print(f"  pngquant={tools.pngquant or 'missing'}")
    print(f"  oxipng={tools.oxipng or 'missing'}")
    print(f"  cjpeg={tools.cjpeg or 'missing'}")
    print(f"  cwebp={tools.cwebp or 'missing'}")
    print(f"  avifenc={tools.avifenc or 'missing'}")
    print(f"  pillow={'available' if Image is not None else 'missing'}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.in_place and args.output:
        parser.error("--in-place cannot be used together with --output")

    inputs = [Path(value) for value in args.inputs]
    recursive = not args.no_recursive

    try:
        jobs = collect_jobs(inputs, Path(args.output) if args.output else None, args.in_place, recursive)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if not jobs:
        print("No supported image files found.")
        return 1

    tools = detect_tools()
    print_detected_tools(tools)
    print(f"Discovered {len(jobs)} image(s).")

    ok = skipped = failed = 0
    saved_total = 0

    for idx, job in enumerate(jobs, start=1):
        if job.dest.exists() and not args.overwrite and job.dest != job.src:
            skipped += 1
            if args.verbose:
                print(f"[{idx}/{len(jobs)}] SKIP {job.display_name}: output exists")
            continue

        try:
            improved, before, after = compress_one(job.src, job.dest, tools)
            ok += 1
            saved_total += before - after
            if args.verbose:
                status = "COMPRESSED" if improved else "KEPT"
                print(
                    f"[{idx}/{len(jobs)}] {status} {job.display_name}: "
                    f"{format_size(before)} -> {format_size(after)}"
                )
            elif idx % 100 == 0 or idx == len(jobs):
                print(
                    f"[{idx}/{len(jobs)}] ok={ok} skipped={skipped} failed={failed} "
                    f"saved={format_size(saved_total)}"
                )
        except Exception as exc:
            failed += 1
            print(f"[{idx}/{len(jobs)}] FAIL {job.display_name}: {exc}", file=sys.stderr)

    output_display = "in-place" if args.in_place else str((Path(args.output) if args.output else default_output_dir([p.resolve() for p in inputs])).resolve())
    print(
        f"Summary: ok={ok} skipped={skipped} failed={failed} "
        f"saved={format_size(saved_total)} output={output_display}"
    )
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
