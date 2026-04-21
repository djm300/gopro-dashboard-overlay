#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import shutil
from pathlib import Path

from PIL import Image

from gopro_overlay import timeseries_process
from gopro_overlay.arguments import default_config_location
from gopro_overlay.dimensions import dimension_from, Dimension
from gopro_overlay.ffmpeg import FFMPEG
from gopro_overlay.ffmpeg_gopro import FFMPEGGoPro
from gopro_overlay.font import load_font
from gopro_overlay.framemeta_gpmd import LoadFlag
from gopro_overlay.geo import MapRenderer, MapStyler, api_key_finder
from gopro_overlay.layout import Overlay
from gopro_overlay.layout_xml import Converters, layout_from_xml, load_xml_layout
from gopro_overlay.loading import GoproLoader
from gopro_overlay.point import Point
from gopro_overlay.privacy import NoPrivacyZone
from gopro_overlay.timeunits import timeunits
from gopro_overlay.units import units
from gopro_overlay.widgets.widgets import SimpleFrameSupplier
from gopro_overlay.config import Config


DOWNLOAD_DIR = Path("/mnt/downloads/gopro-ski-26")
DEFAULT_LAYOUT = Path("ski-pov-1080p.xml")
DEFAULT_OUTPUT = Path("preview.jpg")
DEFAULT_CACHE = Path("/tmp/gopro-cache")
DEFAULT_SIZE = "1920x1080"
DEFAULT_FONT = Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf")


def first_mp4(directory: Path) -> Path:
    preferred = directory / "cut.mp4"
    if preferred.exists():
        return preferred

    mp4s = sorted(
        p for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() == ".mp4"
    )
    if not mp4s:
        raise FileNotFoundError(f"No MP4 files found in {directory}")

    for candidate in mp4s:
        if "-" not in candidate.stem:
            return candidate
    return mp4s[0]


def load_frame(ffmpeg_gopro: FFMPEGGoPro, filepath: Path, size: Dimension, at_seconds: float) -> Image.Image:
    at_time = timeunits(seconds=at_seconds)
    raw = ffmpeg_gopro.load_frame(filepath, at_time)
    frame = Image.frombytes(mode="RGBA", size=size.tuple(), data=raw)
    return frame


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a single dashboard preview frame to JPEG.")
    parser.add_argument("--input", type=Path, help="Input GoPro MP4. Defaults to cut.mp4 or first MP4 in cwd.")
    parser.add_argument("--layout-xml", type=Path, default=DEFAULT_LAYOUT, help="Layout XML file.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Local preview JPEG output path.")
    parser.add_argument("--overlay-size", default=DEFAULT_SIZE, help="Overlay frame size, e.g. 1920x1080.")
    parser.add_argument("--at-seconds", type=float, default=10.0, help="Timestamp in seconds for the preview frame.")
    parser.add_argument("--map-style", default="osm", help="Map style.")
    parser.add_argument("--config-dir", type=Path, default=default_config_location, help="Config directory.")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE, help="Cache directory.")
    parser.add_argument("--font", type=Path, default=DEFAULT_FONT, help="Font file.")
    args = parser.parse_args()

    root = Path.cwd()
    source = args.input.resolve() if args.input else first_mp4(root).resolve()
    layout_xml = args.layout_xml.resolve()
    output = args.output.resolve()

    if not layout_xml.exists():
        raise FileNotFoundError(layout_xml)
    if not source.exists():
        raise FileNotFoundError(source)

    args.config_dir.mkdir(parents=True, exist_ok=True)
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    ffmpeg_gopro = FFMPEGGoPro(FFMPEG())
    loader = GoproLoader(
        ffmpeg_gopro=ffmpeg_gopro,
        units=units,
        flags={LoadFlag.ACCL, LoadFlag.CORI, LoadFlag.GRAV},
    )
    gopro = loader.load(source)
    timeseries = gopro.framemeta

    # Match the fields expected by the XML widgets.
    timeseries.process_deltas(timeseries_process.calculate_speeds(), skip=18 * 3)
    timeseries.process(timeseries_process.calculate_odo())
    timeseries.process_accel(timeseries_process.calculate_accel(), skip=18 * 3)
    timeseries.process_deltas(timeseries_process.calculate_gradient(), skip=18 * 3)
    timeseries.process(timeseries_process.process_ses("point", lambda i: i.point, alpha=0.45))

    overlay_size = dimension_from(args.overlay_size)

    frame_time = max(0.0, args.at_seconds)
    source_frame = load_frame(ffmpeg_gopro, source, gopro.recording.video.dimension, frame_time)
    if source_frame.size != overlay_size.tuple():
        source_frame = source_frame.resize(overlay_size.tuple(), resample=Image.Resampling.LANCZOS)

    config_loader = Config(args.config_dir)
    api_finder = api_key_finder(config_loader, argparse.Namespace(map_api_key=None))
    font = load_font(str(args.font)).font_variant(size=16)

    with MapRenderer(
        cache_dir=args.cache_dir,
        styler=MapStyler(api_key_finder=api_finder),
    ).open(args.map_style) as renderer:
        layout = layout_from_xml(
            load_xml_layout(layout_xml),
            renderer,
            timeseries,
            font,
            NoPrivacyZone(),
            converters=Converters(
                speed_unit="kph",
                altitude_unit="metre",
                distance_unit="metre",
                temperature_unit="degC",
            ),
        )
        overlay = Overlay(framemeta=timeseries, create_widgets=layout)
        supplier = SimpleFrameSupplier(overlay_size)
        overlay_frame = overlay.draw(timeunits(seconds=frame_time), supplier.drawing_frame())

    composited = Image.alpha_composite(source_frame, overlay_frame).convert("RGB")
    composited.save(output, format="JPEG", quality=95, optimize=True, progressive=True)

    stamp = dt.datetime.now().strftime("%H%M-%d%m%Y")
    copied = DOWNLOAD_DIR / f"test{stamp}.jpg"
    shutil.copy2(output, copied)

    print(f"source: {source}")
    print(f"layout: {layout_xml}")
    print(f"output: {output}")
    print(f"copied: {copied}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
