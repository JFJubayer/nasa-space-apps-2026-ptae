#!/usr/bin/env python3
"""Fetch freely licensed site photos from Wikimedia Commons for new PTAE sites."""

import argparse
import html
import json
import re
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = PROJECT_ROOT / "data" / "sites.json"
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"
OUTPUT_DIR = DASHBOARD_DIR / "assets" / "sites"
MANIFEST_PATH = DASHBOARD_DIR / "site_photos.json"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "PTAE site photo fetcher/1.0 (https://github.com/nasa-space-apps-2026-ptae-main)"
PUBLIC_DOMAIN_TAG_URL = "https://commons.wikimedia.org/wiki/Template:PD"
IMAGE_WIDTH_MIN = 800
THUMBNAIL_WIDTH = 1200
MAX_PHOTOS_PER_SITE = 3
REQUEST_DELAY_SECONDS = 0.5
GENERIC_SITE_TERMS = {
    "area", "crater", "craters", "depression", "desert", "district", "field", "mining", "mount",
    "mountain", "protected", "region", "volcanic", "volcano", "valley", "site"
}
SITE_SEARCH_ALIASES = {
    "svalbard_longyearbyen": ("Svalbard landscape", "Longyearbyen Svalbard terrain"),
    "danakil_depression": ("Danakil Depression Ethiopia landscape", "Danakil Ethiopia terrain"),
    "rio_tinto": ("Rio Tinto Spain mine landscape", "Rio Tinto Huelva Spain"),
    "kilauea_hawaii": ("Kilauea volcano Hawaii", "Kilauea crater lava field"),
    "etna_sicily": ("Mount Etna Sicily landscape",),
    "teide_tenerife": ("Mount Teide Tenerife landscape", "Teide volcano Tenerife"),
    "lonar_crater": ("Lonar Crater Maharashtra India", "Lonar crater India aerial"),
    "suswa_volcano_kenya": ("Mount Suswa Kenya volcano", "Suswa volcano Kenya landscape"),
}

# These five galleries already exist in dashboard/assets and must remain untouched.
EXISTING_GALLERIES = {
    "iceland_askja": 3,
    "atacama_puna": 3,
    "mcmurdo_dry_valleys": 3,
    "haughton_crater": 3,
    "hawaii_mauna_kea": 3,
}

NON_PHOTO_TERMS = re.compile(
    r"\b(map|locator|diagram|logo|flag|chart|schematic|icon|coat of arms|"
    r"infographic|illustration|graphic|model|rendering|3d|plan view|location map|topographic map)\b",
    re.IGNORECASE,
)


def _visible_text(value):
    class TextExtractor(__import__("html.parser", fromlist=["HTMLParser"]).HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts = []

        def handle_data(self, data):
            self.parts.append(data)

    extractor = TextExtractor()
    extractor.feed(html.unescape(value or ""))
    return " ".join(" ".join(extractor.parts).split())


def _normalized_words(value):
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    return re.findall(r"[a-z0-9]+", normalized)


def _read_json(path, fallback):
    try:
        with Path(path).open(encoding="utf-8") as source:
            return json.load(source)
    except FileNotFoundError:
        return fallback


def _write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output:
        json.dump(payload, output, indent=2, ensure_ascii=False)
        output.write("\n")


def _request_json(parameters):
    request = urllib.request.Request(
        f"{COMMONS_API}?{urllib.parse.urlencode(parameters)}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _license_info(metadata):
    name = _visible_text(metadata.get("LicenseShortName", {}).get("value", ""))
    license_url = html.unescape(metadata.get("LicenseUrl", {}).get("value", "")).strip()
    normalized = name.lower().replace("creative commons", "cc").strip()
    if "nc" in normalized or "nd" in normalized or "fair use" in normalized:
        return None
    if normalized == "cc0" or normalized.startswith("cc0 "):
        return name or "CC0", license_url
    if normalized.startswith("public domain") or normalized in {"pd", "public-domain"}:
        return name or "Public domain", license_url or PUBLIC_DOMAIN_TAG_URL
    if re.match(r"^cc by-sa(?:\s|$)", normalized):
        return name, license_url
    if re.match(r"^cc by(?:\s|$)", normalized):
        return name, license_url
    return None


def _photo_candidate(page, site_name):
    image_info = (page.get("imageinfo") or [{}])[0]
    width = image_info.get("width", 0)
    mime = image_info.get("mime", "").lower()
    if isinstance(width, bool) or not isinstance(width, int) or width < IMAGE_WIDTH_MIN:
        return None
    if mime not in {"image/jpeg", "image/png"}:
        return None

    metadata = image_info.get("extmetadata", {})
    title = page.get("title", "")
    description = _visible_text(metadata.get("ImageDescription", {}).get("value", ""))
    object_name = _visible_text(metadata.get("ObjectName", {}).get("value", ""))
    candidate_text = f"{title} {object_name} {description}"
    if NON_PHOTO_TERMS.search(candidate_text):
        return None

    accepted_license = _license_info(metadata)
    if not accepted_license:
        return None
    author = _visible_text(metadata.get("Artist", {}).get("value", ""))
    thumb_url = image_info.get("thumburl")
    if not thumb_url:
        return None

    matching_terms = _matching_site_terms(title, site_name)
    match_count = len(matching_terms)
    if match_count == 0:
        return None
    return {
        "title": title,
        "thumb_url": thumb_url,
        "author": author or "Author not credited",
        "license_name": accepted_license[0],
        "license_url": accepted_license[1],
        "source_page_url": f"https://commons.wikimedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
        "source_width": width,
        "relevance": match_count,
    }


def _matching_site_terms(title, site_name):
    if NON_PHOTO_TERMS.search(title):
        return set()
    site_terms = [word for word in _normalized_words(site_name) if len(word) > 2 and word not in GENERIC_SITE_TERMS]
    return set(site_terms).intersection(_normalized_words(title))


def search_site_photos(site, manifest):
    candidates = []
    seen_titles = set()
    existing = manifest.get(site["site_id"], [])
    for entry in existing:
        if entry.get("commons_title"):
            seen_titles.add(entry["commons_title"])
    queries = list(dict.fromkeys((
        *(f"{site['name']} {term}" for term in ("landscape", "terrain", "geology")),
        *SITE_SEARCH_ALIASES.get(site["site_id"], ()),
    )))
    for query in queries:
        payload = _request_json({
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,
            "gsrlimit": 50,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|size|mime",
            "iiurlwidth": THUMBNAIL_WIDTH,
        })
        pages = list((payload.get("query", {}).get("pages") or {}).values())
        for page in pages:
            candidate = _photo_candidate(page, site["name"])
            if candidate and candidate["title"] not in seen_titles:
                seen_titles.add(candidate["title"])
                candidates.append(candidate)
        time.sleep(REQUEST_DELAY_SECONDS)
    candidates.sort(key=lambda candidate: (candidate["relevance"], candidate["source_width"]), reverse=True)
    return candidates


def _download_webp(candidate, output_path):
    request = urllib.request.Request(
        candidate["thumb_url"],
        headers={"User-Agent": USER_AGENT, "Accept": "image/jpeg,image/png"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        image_data = response.read()
    with Image.open(BytesIO(image_data)) as source_image:
        if source_image.format not in {"JPEG", "PNG"}:
            raise ValueError(f"Thumbnail is not JPEG or PNG ({source_image.format}).")
        if source_image.width < IMAGE_WIDTH_MIN:
            raise ValueError(f"Thumbnail is narrower than {IMAGE_WIDTH_MIN}px.")
        converted = source_image.convert("RGB")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(suffix=".webp", dir=output_path.parent, delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        try:
            converted.save(temp_path, format="WEBP", quality=80, method=6)
            temp_path.replace(output_path)
        finally:
            temp_path.unlink(missing_ok=True)


def fetch_site(site, manifest):
    site_id = site["site_id"]
    output_dir = OUTPUT_DIR / site_id
    manifest_entries = manifest.get(site_id, [])
    if output_dir.is_dir() and any(output_dir.iterdir()) and not manifest_entries:
        return len(list(output_dir.glob("*.webp"))), 0, "existing gallery"
    valid_entries = [
        entry for entry in manifest_entries
        if (DASHBOARD_DIR / entry.get("file_path", "")).is_file()
        and entry.get("commons_title")
        and _matching_site_terms(entry["commons_title"], site["name"])
    ]
    if len(valid_entries) != len(manifest_entries):
        valid_entries = []
    if len(valid_entries) >= MAX_PHOTOS_PER_SITE:
        return len(valid_entries), 0, "skipped"

    candidates = search_site_photos(site, manifest)
    entries = list(valid_entries)
    failures = 0
    for candidate in candidates:
        if len(entries) >= MAX_PHOTOS_PER_SITE:
            break
        output_index = len(entries) + 1
        relative_path = f"assets/sites/{site_id}/{output_index}.webp"
        output_path = DASHBOARD_DIR / relative_path
        try:
            _download_webp(candidate, output_path)
            entries.append({
                "file_path": relative_path,
                "commons_title": candidate["title"],
                "author": candidate["author"],
                "license_name": candidate["license_name"],
                "license_url": candidate["license_url"],
                "source_page_url": candidate["source_page_url"],
            })
            manifest[site_id] = entries
            _write_json(MANIFEST_PATH, manifest)
        except (OSError, urllib.error.URLError, ValueError) as error:
            failures += 1
            print(f"  {site_id}: skipped {candidate['title']}: {error}", file=sys.stderr)
        time.sleep(REQUEST_DELAY_SECONDS)
    manifest[site_id] = entries
    _write_json(MANIFEST_PATH, manifest)
    status = "success" if entries else "no licensed photos"
    return len(entries), failures, status


def run(catalog_path=CATALOG_PATH, site_id=None):
    catalog = _read_json(catalog_path, {})
    sites = catalog.get("sites") if isinstance(catalog, dict) else None
    if not isinstance(sites, list):
        raise ValueError("data/sites.json must contain a sites list.")
    if site_id:
        sites = [site for site in sites if site.get("site_id") == site_id]
        if not sites:
            raise ValueError(f"Site not found in catalog: {site_id}")
    manifest = _read_json(MANIFEST_PATH, {})
    if not isinstance(manifest, dict):
        manifest = {}
    for site in sites:
        manifest.setdefault(site.get("site_id", "unknown"), [])
    for entries in manifest.values():
        for entry in entries if isinstance(entries, list) else []:
            if entry.get("license_name") == "Public domain" and not entry.get("license_url"):
                entry["license_url"] = PUBLIC_DOMAIN_TAG_URL
    _write_json(MANIFEST_PATH, manifest)
    results = []
    for site in sites:
        site_id = site.get("site_id", "unknown")
        if site_id in EXISTING_GALLERIES:
            existing_count = EXISTING_GALLERIES[site_id]
            results.append((site_id, existing_count, 0, "existing gallery"))
            continue
        try:
            count, failures, status = fetch_site(site, manifest)
        except (OSError, RuntimeError, TimeoutError, urllib.error.URLError, ValueError, json.JSONDecodeError) as error:
            count, failures, status = len(manifest.get(site_id, [])), 1, "failed"
            print(f"{site_id}: {error}", file=sys.stderr)
        results.append((site_id, count, failures, status))
        time.sleep(REQUEST_DELAY_SECONDS)

    print(f"{'SITE ID':<32} {'PHOTOS':>6} {'FAILURES':>9}  STATUS")
    print("-" * 72)
    for site_id, count, failures, status in results:
        print(f"{site_id:<32} {count:>6} {failures:>9}  {status}")
    print("-" * 72)
    print(f"Sites: {len(results)} | photos: {sum(result[1] for result in results)} | failures: {sum(result[2] for result in results)}")
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH, help="Site catalog JSON (default: data/sites.json)")
    parser.add_argument("--site-id", help="Fetch only this site ID")
    args = parser.parse_args(argv)
    try:
        results = run(args.catalog, args.site_id)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    return 1 if any(status == "failed" for _, _, _, status in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
