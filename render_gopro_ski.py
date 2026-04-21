#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


INPUT_OFFSET = "00:00:30.000000"
DURATION = "00:00:20.000000"
LAYOUT_XML = "ski-pov-720p.xml"
FFMPEG_PROFILE = "720p"
OVERLAY_SIZE = "1280x720"
DOWNLOAD_DIR = Path("/mnt/downloads/gopro-ski-26")
VENV_BIN = Path("/home/joris/venv/bin")
CACHE_DIR = Path("/tmp/gopro-cache")
PROFILE_FILE = "ffmpeg-profiles.json"


def first_mp4(directory: Path) -> Path:
    mp4s = sorted(
        p for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() == ".mp4"
    )
    if not mp4s:
        raise FileNotFoundError(f"No MP4 files found in {directory}")

    # Prefer a source-like filename without a dash, which matches the camera output
    # in this working folder. Fall back to the first MP4 in lexical order.
    for candidate in mp4s:
        if "-" not in candidate.stem:
            return candidate
    return mp4s[0]


def run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True)


def main() -> int:
    root = Path.cwd()
    source = first_mp4(root)
    cut_file = root / "cut.mp4"

    layout_xml = root / LAYOUT_XML
    config_dir = root
    if not layout_xml.exists():
        raise FileNotFoundError(layout_xml)
    if not config_dir.exists():
        raise FileNotFoundError(config_dir)
    if not (root / PROFILE_FILE).exists():
        raise FileNotFoundError(root / PROFILE_FILE)

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="gopro-ski-") as tmp:
        tmpdir = Path(tmp)

        render_file = tmpdir / f"{source.stem}-ski-pov-4k.mp4"
        timestamp = dt.datetime.now().strftime("%H%M-%d%m%Y")
        final_file = DOWNLOAD_DIR / f"test{timestamp}.mp4"

        if cut_file.exists():
            print(f"reusing cut file: {cut_file}")
        else:
            run(
                [
                    str(VENV_BIN / "gopro-cut.py"),
                    str(source),
                    str(cut_file),
                    "--start",
                    INPUT_OFFSET,
                    "--duration",
                    DURATION,
                ],
                cwd=root,
            )

        run(
            [
                str(VENV_BIN / "gopro-dashboard.py"),
                "--config-dir",
                str(config_dir),
                "--cache-dir",
                str(CACHE_DIR),
                "--layout",
                "xml",
                "--layout-xml",
                str(layout_xml),
                "--profile",
                FFMPEG_PROFILE,
                "--overlay-size",
                OVERLAY_SIZE,
                str(cut_file),
                str(render_file),
            ],
            cwd=root,
        )

        shutil.copy2(render_file, final_file)
        print(f"source: {source}")
        print(f"cut: {cut_file}")
        print(f"render: {render_file}")
        print(f"copied: {final_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
