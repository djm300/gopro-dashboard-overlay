#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import shutil
import subprocess
import tempfile
from pathlib import Path

INPUT_OFFSET = "00:00:30.000000"
DURATION = "00:00:20.000000"
DOWNLOAD_DIR = Path("/mnt/downloads/gopro-ski-26")
VENV_BIN = Path("/home/joris/venv/bin")


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
    layout_xml = root / "ski-pov-1080p.xml"
    profile_file = root / "ffmpeg-profiles.json"
    font_file = Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf")
    cache_dir = Path("/tmp/gopro-cache")

    if not layout_xml.exists():
        raise FileNotFoundError(layout_xml)
    if not profile_file.exists():
        raise FileNotFoundError(profile_file)

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="gopro-ski-") as tmp:
        tmpdir = Path(tmp)

        render_file = tmpdir / f"{source.stem}-ski-pov-1080p.mp4"
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
                "--font",
                str(font_file),
                "--config-dir",
                str(root),
                "--cache-dir",
                str(cache_dir),
                "--layout",
                "xml",
                "--layout-xml",
                str(layout_xml),
                "--profile",
                "1080p",
                "--overlay-size",
                "1920x1080",
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
