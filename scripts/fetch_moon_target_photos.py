#!/usr/bin/env python3
"""Download only the explicitly verified Moon photos; never update catalogs."""

from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
    from PIL import Image, ImageOps
except ImportError as error:
    raise SystemExit("Pillow and requests must already be installed; no packages were installed.") from error

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "dashboard" / "assets" / "targets"
MAX_EDGE = 1200
QUALITY = 80
MAX_BYTES = 400_000
USER_AGENT = "PTAE verified Moon reference photo downloader/1.0"
PHOTOS = (
    {
        "source_url": "https://lroc.im-ldi.com/images/1276",
        "image_url": "https://lroc.im-ldi.com/ckeditor_assets/pictures/1229/content_M1407524099_LRmos.warp.No_Arrow.1100pixelCrop.png",
        "filename": "moon-shackleton-crater-rim-oblique.webp",
        "credit": "NASA/GSFC/Arizona State University",
    },
    {
        "source_url": "https://lroc.im-ldi.com/images/1294",
        "image_url": "https://lroc.im-ldi.com/ckeditor_assets/pictures/1273/content_M1432398306_LRmos.warp.str01.MALAPERT.1100x1100.png",
        "filename": "moon-malapert-massif-oblique.webp",
        "credit": "NASA/GSFC/Arizona State University",
    },
    {
        "source_url": "https://science.nasa.gov/photojournal/marius-hills-constellation-region-of-interest/",
        "image_url": "https://assets.science.nasa.gov/content/dam/science/psd/photojournal/pia/pia13/pia13179/PIA13179.jpg",
        "filename": "moon-marius-hills-rille.webp",
        "credit": "NASA/GSFC/Arizona State University",
    },
    {
        "source_url": "https://science.nasa.gov/photojournal/aristarchus-plateau-2-pyroclastic-deposit/",
        "image_url": "https://assets.science.nasa.gov/content/dam/science/psd/photojournal/pia/pia12/pia12944/PIA12944.jpg",
        "filename": "moon-aristarchus-plateau-pyroclastic-deposit.webp",
        "credit": "NASA/GSFC/Arizona State University",
    },
    {
        "source_url": "https://science.nasa.gov/photojournal/aristarchus-plateau-1-amazing-geologic-diversity/",
        "image_url": "https://assets.science.nasa.gov/content/dam/science/psd/photojournal/pia/pia12/pia12942/PIA12942.jpg",
        "filename": "moon-aristarchus-plateau-cobra-head.webp",
        "credit": "NASA/GSFC/Arizona State University",
    },
    {
        "source_url": "https://lroc.im-ldi.com/images/524",
        "image_url": "https://lroc.im-ldi.com/news/uploads/LROCiotw/M187340587LR_thumb.png",
        "filename": "moon-schrodinger-basin-peak-ring-boulders.webp",
        "credit": "NASA/GSFC/Arizona State University",
    },
    {
        "source_url": "https://lroc.im-ldi.com/images/391",
        "image_url": "https://lroc.im-ldi.com/news/uploads/LROCiotw/M159099396RE_thumb.png",
        "filename": "moon-schrodinger-basin-scarp.webp",
        "credit": "NASA/GSFC/Arizona State University",
    },
)


def main():
    if not OUTPUT_DIR.is_dir():
        raise SystemExit(f"Existing asset directory required: {OUTPUT_DIR}")
    destinations = [OUTPUT_DIR / photo["filename"] for photo in PHOTOS]
    if len(set(destinations)) != len(destinations):
        raise SystemExit("Duplicate destination filenames; no files written.")
    for destination in destinations:
        if destination.parent != OUTPUT_DIR or destination.suffix != ".webp":
            raise SystemExit("Destination must be a WebP directly inside dashboard/assets/targets/.")
        if destination.exists():
            raise SystemExit(f"Refusing to overwrite existing asset: {destination.name}")

    encoded_photos = []
    with requests.Session() as session:
        session.headers.update({"User-Agent": USER_AGENT})
        for photo, destination in zip(PHOTOS, destinations):
            if urlparse(photo["image_url"]).hostname not in {"lroc.im-ldi.com", "assets.science.nasa.gov"}:
                raise SystemExit("Unapproved image host; no files written.")
            response = session.get(photo["image_url"], timeout=60)
            response.raise_for_status()
            if urlparse(response.url).hostname not in {"lroc.im-ldi.com", "assets.science.nasa.gov"}:
                raise SystemExit("Unexpected redirect host; no files written.")
            with Image.open(BytesIO(response.content)) as source:
                if source.format not in {"JPEG", "PNG"}:
                    raise SystemExit(f"Unexpected source image format for {destination.name}.")
                image = ImageOps.exif_transpose(source).convert("RGB")
                image.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)
                buffer = BytesIO()
                image.save(buffer, format="WEBP", quality=QUALITY, method=6)
                data = buffer.getvalue()
                if len(data) > MAX_BYTES:
                    raise SystemExit(f"{destination.name} exceeds {MAX_BYTES} bytes; no files written.")
                encoded_photos.append((destination, data, image.size, photo))

    for destination, data, size, photo in encoded_photos:
        with destination.open("xb") as output:
            output.write(data)
        print(f"{destination.name}: {size[0]}x{size[1]}, {len(data)} bytes; {photo['credit']}; {photo['source_url']}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, requests.RequestException) as error:
        raise SystemExit(f"Moon photo download stopped: {error}") from error