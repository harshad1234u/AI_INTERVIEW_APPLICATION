"""Fake webcam feeds for the browser tests (Pillow needed), written to e2e/out/:
face.mjpeg (one smiling face) and faces.mjpeg (three faces). Made from the face-api package's
own demo photo at test time, so no photo of a person is kept in this repository.

    python e2e/camera_feeds.py
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "frontend" / "node_modules" / "@vladmandic" / "face-api" / "demo" / "sample1.jpg"
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)

photo = Image.open(SOURCE).convert("RGB")
frames = {
    "face": photo.crop((1180, 120, 1900, 660)).resize((640, 480)),  # the face on the right
    "faces": photo.resize((640, 480)),  # all three faces
}
for name, frame in frames.items():
    jpeg = OUT / f"{name}.jpg"
    frame.save(jpeg, quality=85)
    # Chromium's fake camera reads MJPEG: JPEG frames back to back.
    (OUT / f"{name}.mjpeg").write_bytes(jpeg.read_bytes() * 30)
print(f"camera feeds written to {OUT}")
