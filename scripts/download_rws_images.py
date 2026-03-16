#!/usr/bin/env python3
"""
Download public-domain Rider-Waite-Smith tarot card images from Wikimedia Commons.

All images are in the public domain in the United States (published before 1928).
Source: https://commons.wikimedia.org/wiki/Rider-Waite_tarot_deck

Usage:
    python scripts/download_rws_images.py
    python scripts/download_rws_images.py --output assets/rws --delay 0.5
"""
import argparse
import time
import json
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Wikimedia Commons base URL for direct file access via the API
WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"
WIKIMEDIA_FILE_BASE = "https://upload.wikimedia.org/wikipedia/commons"

# Mapping: cards.json image_file → Wikimedia Commons file name
# Source: https://commons.wikimedia.org/wiki/Category:Rider-Waite_tarot_deck_cards
WIKIMEDIA_FILES = {
    # Major Arcana
    "00_fool.jpg": "RWS_Tarot_00_Fool.jpg",
    "01_magician.jpg": "RWS_Tarot_01_Magician.jpg",
    "02_high_priestess.jpg": "RWS_Tarot_02_High_Priestess.jpg",
    "03_empress.jpg": "RWS_Tarot_03_Empress.jpg",
    "04_emperor.jpg": "RWS_Tarot_04_Emperor.jpg",
    "05_hierophant.jpg": "RWS_Tarot_05_Hierophant.jpg",
    "06_lovers.jpg": "RWS_Tarot_06_Lovers.jpg",
    "07_chariot.jpg": "RWS_Tarot_07_Chariot.jpg",
    "08_strength.jpg": "RWS_Tarot_08_Strength.jpg",
    "09_hermit.jpg": "RWS_Tarot_09_Hermit.jpg",
    "10_wheel_of_fortune.jpg": "RWS_Tarot_10_Wheel_of_Fortune.jpg",
    "11_justice.jpg": "RWS_Tarot_11_Justice.jpg",
    "12_hanged_man.jpg": "RWS_Tarot_12_Hanged_Man.jpg",
    "13_death.jpg": "RWS_Tarot_13_Death.jpg",
    "14_temperance.jpg": "RWS_Tarot_14_Temperance.jpg",
    "15_devil.jpg": "RWS_Tarot_15_Devil.jpg",
    "16_tower.jpg": "RWS_Tarot_16_Tower.jpg",
    "17_star.jpg": "RWS_Tarot_17_Star.jpg",
    "18_moon.jpg": "RWS_Tarot_18_Moon.jpg",
    "19_sun.jpg": "RWS_Tarot_19_Sun.jpg",
    "20_judgement.jpg": "RWS_Tarot_20_Judgement.jpg",
    "21_world.jpg": "RWS_Tarot_21_World.jpg",
    # Minor Arcana – Wands
    "wands_01.jpg": "RWS_Tarot_Wands_Ace.jpg",
    "wands_02.jpg": "RWS_Tarot_Wands_02.jpg",
    "wands_03.jpg": "RWS_Tarot_Wands_03.jpg",
    "wands_04.jpg": "RWS_Tarot_Wands_04.jpg",
    "wands_05.jpg": "RWS_Tarot_Wands_05.jpg",
    "wands_06.jpg": "RWS_Tarot_Wands_06.jpg",
    "wands_07.jpg": "RWS_Tarot_Wands_07.jpg",
    "wands_08.jpg": "RWS_Tarot_Wands_08.jpg",
    "wands_09.jpg": "RWS_Tarot_Wands_09.jpg",
    "wands_10.jpg": "RWS_Tarot_Wands_10.jpg",
    "wands_11.jpg": "RWS_Tarot_Wands_Page.jpg",
    "wands_12.jpg": "RWS_Tarot_Wands_Knight.jpg",
    "wands_13.jpg": "RWS_Tarot_Wands_Queen.jpg",
    "wands_14.jpg": "RWS_Tarot_Wands_King.jpg",
    # Minor Arcana – Cups
    "cups_01.jpg": "RWS_Tarot_Cups_Ace.jpg",
    "cups_02.jpg": "RWS_Tarot_Cups_02.jpg",
    "cups_03.jpg": "RWS_Tarot_Cups_03.jpg",
    "cups_04.jpg": "RWS_Tarot_Cups_04.jpg",
    "cups_05.jpg": "RWS_Tarot_Cups_05.jpg",
    "cups_06.jpg": "RWS_Tarot_Cups_06.jpg",
    "cups_07.jpg": "RWS_Tarot_Cups_07.jpg",
    "cups_08.jpg": "RWS_Tarot_Cups_08.jpg",
    "cups_09.jpg": "RWS_Tarot_Cups_09.jpg",
    "cups_10.jpg": "RWS_Tarot_Cups_10.jpg",
    "cups_11.jpg": "RWS_Tarot_Cups_Page.jpg",
    "cups_12.jpg": "RWS_Tarot_Cups_Knight.jpg",
    "cups_13.jpg": "RWS_Tarot_Cups_Queen.jpg",
    "cups_14.jpg": "RWS_Tarot_Cups_King.jpg",
    # Minor Arcana – Swords
    "swords_01.jpg": "RWS_Tarot_Swords_Ace.jpg",
    "swords_02.jpg": "RWS_Tarot_Swords_02.jpg",
    "swords_03.jpg": "RWS_Tarot_Swords_03.jpg",
    "swords_04.jpg": "RWS_Tarot_Swords_04.jpg",
    "swords_05.jpg": "RWS_Tarot_Swords_05.jpg",
    "swords_06.jpg": "RWS_Tarot_Swords_06.jpg",
    "swords_07.jpg": "RWS_Tarot_Swords_07.jpg",
    "swords_08.jpg": "RWS_Tarot_Swords_08.jpg",
    "swords_09.jpg": "RWS_Tarot_Swords_09.jpg",
    "swords_10.jpg": "RWS_Tarot_Swords_10.jpg",
    "swords_11.jpg": "RWS_Tarot_Swords_Page.jpg",
    "swords_12.jpg": "RWS_Tarot_Swords_Knight.jpg",
    "swords_13.jpg": "RWS_Tarot_Swords_Queen.jpg",
    "swords_14.jpg": "RWS_Tarot_Swords_King.jpg",
    # Minor Arcana – Pentacles
    "pentacles_01.jpg": "RWS_Tarot_Pentacles_Ace.jpg",
    "pentacles_02.jpg": "RWS_Tarot_Pentacles_02.jpg",
    "pentacles_03.jpg": "RWS_Tarot_Pentacles_03.jpg",
    "pentacles_04.jpg": "RWS_Tarot_Pentacles_04.jpg",
    "pentacles_05.jpg": "RWS_Tarot_Pentacles_05.jpg",
    "pentacles_06.jpg": "RWS_Tarot_Pentacles_06.jpg",
    "pentacles_07.jpg": "RWS_Tarot_Pentacles_07.jpg",
    "pentacles_08.jpg": "RWS_Tarot_Pentacles_08.jpg",
    "pentacles_09.jpg": "RWS_Tarot_Pentacles_09.jpg",
    "pentacles_10.jpg": "RWS_Tarot_Pentacles_10.jpg",
    "pentacles_11.jpg": "RWS_Tarot_Pentacles_Page.jpg",
    "pentacles_12.jpg": "RWS_Tarot_Pentacles_Knight.jpg",
    "pentacles_13.jpg": "RWS_Tarot_Pentacles_Queen.jpg",
    "pentacles_14.jpg": "RWS_Tarot_Pentacles_King.jpg",
}


def get_wikimedia_url(filename: str) -> str:
    """Resolve a Wikimedia Commons filename to a direct download URL using the API."""
    import hashlib
    # Wikimedia uses MD5-based path: first 2 chars of MD5(filename)
    name = filename.replace(" ", "_")
    md5 = hashlib.md5(name.encode("utf-8")).hexdigest()
    return f"{WIKIMEDIA_FILE_BASE}/{md5[0]}/{md5[:2]}/{name}"


def download_file(url: str, dest: Path, delay: float = 1.0) -> bool:
    """Download a file from url to dest. Returns True on success."""
    headers = {
        "User-Agent": (
            "TarotAppImageDownloader/1.0 "
            "(https://github.com/eunicell78-arch/taro; tarot card reading app)"
        )
    }
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=30) as resp:
            data = resp.read()
        dest.write_bytes(data)
        time.sleep(delay)
        return True
    except (HTTPError, URLError) as exc:
        print(f"  WARN: {exc} → {url}", file=sys.stderr)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Download RWS tarot images.")
    parser.add_argument(
        "--output",
        default="assets/rws",
        help="Output directory (default: assets/rws)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay in seconds between requests (default: 1.0)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Overwrite files that already exist (default: skip existing)",
    )
    args = parser.parse_args()

    # Resolve output dir relative to the repo root (script is in scripts/)
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    output_dir = (repo_root / args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {len(WIKIMEDIA_FILES)} RWS images → {output_dir}")
    print(f"Delay between requests: {args.delay}s")
    print()

    success = 0
    skipped = 0
    failed = []

    for local_name, wiki_name in WIKIMEDIA_FILES.items():
        dest = output_dir / local_name
        if not args.overwrite and dest.exists():
            print(f"  SKIP  {local_name} (already exists)")
            skipped += 1
            continue

        url = get_wikimedia_url(wiki_name)
        print(f"  GET   {local_name} …", end=" ", flush=True)
        ok = download_file(url, dest, delay=args.delay)
        if ok:
            size_kb = dest.stat().st_size // 1024
            print(f"OK ({size_kb} KB)")
            success += 1
        else:
            print("FAILED")
            failed.append(local_name)

    print()
    print(f"Done: {success} downloaded, {skipped} skipped, {len(failed)} failed.")
    if failed:
        print("Failed files:")
        for f in failed:
            print(f"  {f}")
        sys.exit(1)


if __name__ == "__main__":
    main()
