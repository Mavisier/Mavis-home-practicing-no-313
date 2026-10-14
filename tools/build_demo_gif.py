"""Encode observed synthetic UI screenshots into a labeled step GIF."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / ".local/demo-capture"
OUTPUT = ROOT / "docs/demo"
LABELS = [
    "1. Choose a synthetic scenario",
    "2. Review findings and draft questions",
    "3. Inspect sources before approval",
    "4. Approve a local review task",
    "5. Inspect the persisted audit trail",
]


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    font_path = Path("C:/Windows/Fonts/arialbd.ttf")
    font = (
        ImageFont.truetype(str(font_path), 17) if font_path.exists() else ImageFont.load_default()
    )
    small_path = Path("C:/Windows/Fonts/arial.ttf")
    small = (
        ImageFont.truetype(str(small_path), 12) if small_path.exists() else ImageFont.load_default()
    )
    frames = []
    dimensions = None
    for index, label in enumerate(LABELS, 1):
        with Image.open(INPUT / f"step-{index:02}.png") as source:
            screenshot = source.convert("RGB")
        if dimensions is None:
            dimensions = screenshot.size
        if screenshot.size != dimensions:
            raise ValueError("Capture dimensions changed; recapture instead of stretching the UI.")
        frame = Image.new("RGB", (screenshot.width, screenshot.height + 62), "#183641")
        draw = ImageDraw.Draw(frame)
        draw.text((14, 10), label, fill="white", font=font)
        draw.text(
            (14, 35),
            "Fixture mode | synthetic input | no real messages",
            fill="#BCE2DF",
            font=small,
        )
        frame.paste(screenshot, (0, 62))
        frames.append(frame.quantize(colors=256))
    path = OUTPUT / "workflow.gif"
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=4000,
        loop=0,
        optimize=True,
        disposal=2,
    )
    report = {
        "frames": len(frames),
        "loop_ms": 20000,
        "mode": "fixture",
        "input": "Synthetic ILAN-1001",
        "capture": "Observed browser UI steps, not a real-time screen recording.",
        "real_listing_photos": False,
        "real_listing_identifiers": False,
        "dimensions": frames[0].size,
        "bytes": path.stat().st_size,
    }
    (OUTPUT / "capture.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
