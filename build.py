# /// script
# dependencies = [
#     "chws-tool",
#     "fonttools[woff]",
# ]
# ///

"""Build script for makumi-fonts.

This script:
1. Injects OpenType spacing features (chws, vchw, halt, vhal) into source Zen fonts
   using east-asian-spacing with forced fullwidth_advance=1000.
2. Subsets the fonts to 28 Japanese punctuation characters.
3. Updates font metadata (name table: Zen -> Makumi).
4. Exports TTF, WOFF, and WOFF2 files to fonts/.
"""

from __future__ import annotations

import asyncio
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

from east_asian_spacing import Builder, Config
from fontTools.misc import timeTools
from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

# 28 punctuation characters (JIS / east-asian-spacing aligned order)
YAKUMONO_CHARS = "、。，．・：；（）「」『』［］｛｝【】〈〉《》〔〕〝〟　"

SOURCES_DIR = Path("tmp/sources")
NORMALIZED_CACHE_DIR = Path("tmp/normalized")
OUTPUT_DIR = Path("fonts")
CHWS_CACHE_DIR = Path("tmp/chws")

# Opening brackets that sit on the right half of fullwidth: shift right
OPENING_CHARS = "「『【〈《〔〝"
# Closing brackets and punctuation that sit on the left half of fullwidth: advance=1000
CLOSING_CHARS = "」』】〉》〕〟、。"
# Middle punctuation: centered
MIDDLE_CHARS = "・"

FONT_VERSION_STRING = "Version 1.000"
FONT_REVISION = 1.0
VENDOR_ID = b"MKMI"
AUTHOR_COPYRIGHT = "Copyright 2026 Daiji256."

# Fixed build timestamp for deterministic (reproducible) builds.
# Update this timestamp (ISO 8601 UTC) when releasing a new version.
BUILD_DATE = "2026-10-25T10:00:00Z"
BUILD_TIMESTAMP = timeTools.timestampSinceEpoch(
    datetime.fromisoformat(BUILD_DATE).timestamp()
)


# Source Zen font repositories and pinned commit revisions (alphabetical order)
SOURCE_REPOS: list[tuple[str, str, list[str]]] = [
    # 1. Zen Antique & Zen Antique Soft (2 fonts)
    (
        "googlefonts/zen-antique",
        "3521a97dfa21d4c985725be88e9beb5edef517b9",
        ["ZenAntique-Regular.ttf", "ZenAntiqueSoft-Regular.ttf"],
    ),
    # 2. Zen Kaku Gothic Antique (5 fonts) & Zen Kaku Gothic New (5 fonts)
    (
        "googlefonts/zen-kakugothic",
        "2705757e17e42954f3acbdf921ac0ae24d1270cd",
        [
            f"ZenKakuGothicAntique-{w}.ttf"
            for w in ["Light", "Regular", "Medium", "Bold", "Black"]
        ]
        + [
            f"ZenKakuGothicNew-{w}.ttf"
            for w in ["Light", "Regular", "Medium", "Bold", "Black"]
        ],
    ),
    # 3. Zen Kurenaido (1 font)
    (
        "googlefonts/zen-kurenaido",
        "cd751ced55d4ebb1fb2fbd90602eb9351dd03fd6",
        ["ZenKurenaido-Regular.ttf"],
    ),
    # 4. Zen Maru Gothic (5 fonts)
    (
        "googlefonts/zen-marugothic",
        "553c872b216d1290e2902a466edcdc9682f0df6a",
        [
            f"ZenMaruGothic-{w}.ttf"
            for w in ["Light", "Regular", "Medium", "Bold", "Black"]
        ],
    ),
    # 5. Zen Old Mincho (5 fonts)
    (
        "googlefonts/zen-oldmincho",
        "490d363e7886839ba1f86971cf874a1d70ad27f0",
        [
            f"ZenOldMincho-{w}.ttf"
            for w in ["Regular", "Medium", "SemiBold", "Bold", "Black"]
        ],
    ),
]


def download_source_fonts() -> None:
    """Download source Zen fonts from GitHub repositories if not already present."""
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    print("=== Checking source Zen fonts (alphabetical order) ===")
    for repo, rev, filenames in SOURCE_REPOS:
        for filename in filenames:
            dest = SOURCES_DIR / filename
            if dest.exists():
                continue
            url = f"https://raw.githubusercontent.com/{repo}/{rev}/fonts/ttf/{filename}"
            print(f"Downloading {filename} from {repo} ({rev[:7]})...")
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "makumi-fonts-build/1.0"},
            )
            with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:
                f.write(resp.read())


def to_kebab_case(filename: str) -> str:
    """Convert PascalCase font filename to kebab-case.

    e.g. ZenAntiqueSoft-Regular.ttf -> makumi-antique-soft-regular
    """
    base = filename.replace(".ttf", "")
    base = re.sub(r"^Zen", "Makumi", base)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", base)
    s = s.replace("_", "-").lower()
    return re.sub(r"-+", "-", s)


def update_metadata(font: TTFont) -> None:
    """Update font metadata (name, head, OS/2 tables) for Makumi release."""
    # 1. head table: fontRevision and fixed modified timestamp
    if "head" in font:
        font["head"].fontRevision = FONT_REVISION
        font["head"].modified = BUILD_TIMESTAMP
    font.recalcTimestamp = False

    # 2. OS/2 table: achVendID
    if "OS/2" in font:
        font["OS/2"].achVendID = VENDOR_ID

    # 3. name table
    if "name" not in font:
        return

    name_table = font["name"]

    # Extract base names from Windows records (plat 3, enc 1, lang 1033)
    def get_name(name_id: int) -> str | None:
        rec = name_table.getName(name_id, 3, 1, 1033)
        return rec.toUnicode() if rec else None

    orig_family = get_name(16) or get_name(1) or "Zen"
    new_family = orig_family.replace("Zen", "Makumi")

    # Construct description
    description = (
        f"{new_family} is a subset web font for Japanese punctuation marks based on "
        f"{orig_family}, with OpenType chws features added."
    )

    # Update records across all platforms
    for record in name_table.names:
        nid = record.nameID
        try:
            val = record.toUnicode()
            if nid == 0:  # Copyright
                if AUTHOR_COPYRIGHT not in val:
                    record.string = f"{val.rstrip('.')}. {AUTHOR_COPYRIGHT}"
            elif nid == 3:  # Unique Identifier
                # e.g. 1.002;ZEN!;ZenMaruGothic-Regular -> 1.000;MKMI;MakumiMaruGothic-Regular
                new_val = re.sub(r"^[^;]+;[^;]+;", "1.000;MKMI;", val)
                record.string = new_val.replace("Zen", "Makumi")
            elif nid == 5:  # Version
                record.string = FONT_VERSION_STRING
            elif nid in (1, 4, 6, 16):
                record.string = val.replace("Zen", "Makumi")
            elif nid in (2, 17):  # Subfamily, Typographic Subfamily
                pass  # Keep as is (Regular, Bold, etc.)
        except (UnicodeDecodeError, KeyError):
            pass

    # Ensure Description (NameID 10) is set for Windows and Mac platforms
    name_table.setName(description, 10, 3, 1, 1033)
    name_table.setName(description, 10, 1, 0, 0)


def normalize_font_metrics(src_path: Path) -> Path:
    """Normalize non-1000 advance widths of fullwidth punctuation (e.g. Zen Kurenaido).

    Zen Kurenaido sets punctuation advance to 943 to match kana metrics, which causes
    east-asian-spacing (chws) to skip them. This function adjusts 943-advance punctuation
    to fullwidth 1000 (shifting opening brackets right, centering middle dot) so chws
    features apply correctly.
    """
    font = TTFont(src_path, recalcTimestamp=False)
    font.recalcTimestamp = False
    hmtx = font.get("hmtx")
    glyf = font.get("glyf")
    cmap = font.getBestCmap()

    if not hmtx or not glyf or not cmap:
        return src_path

    # Check if any yakumono character has non-1000 advance
    needs_normalization = False
    for char in YAKUMONO_CHARS:
        code = ord(char)
        if code in cmap:
            gid = cmap[code]
            adv, _ = hmtx[gid]
            if adv != 1000:
                needs_normalization = True
                break

    if not needs_normalization:
        return src_path

    dest_path = NORMALIZED_CACHE_DIR / src_path.name
    if dest_path.exists():
        return dest_path

    NORMALIZED_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[{src_path.name}] Normalizing punctuation advances to 1000...")

    for char in OPENING_CHARS:
        code = ord(char)
        if code in cmap:
            gid = cmap[code]
            adv, lsb = hmtx[gid]
            if adv != 1000:
                diff = 1000 - adv
                hmtx[gid] = (1000, lsb + diff)
                g = glyf[gid]
                g.xMin += diff
                g.xMax += diff
                coords = g.coordinates
                for i in range(len(coords)):
                    coords[i] = (coords[i][0] + diff, coords[i][1])

    for char in CLOSING_CHARS:
        code = ord(char)
        if code in cmap:
            gid = cmap[code]
            adv, lsb = hmtx[gid]
            if adv != 1000:
                hmtx[gid] = (1000, lsb)

    for char in MIDDLE_CHARS:
        code = ord(char)
        if code in cmap:
            gid = cmap[code]
            adv, lsb = hmtx[gid]
            if adv != 1000:
                half_diff = (1000 - adv) // 2
                hmtx[gid] = (1000, lsb + half_diff)
                g = glyf[gid]
                g.xMin += half_diff
                g.xMax += half_diff
                coords = g.coordinates
                for i in range(len(coords)):
                    coords[i] = (coords[i][0] + half_diff, coords[i][1])

    font["head"].modified = BUILD_TIMESTAMP
    font.save(dest_path)
    return dest_path


async def add_chws_features(src_path: Path, dest_path: Path) -> None:
    """Inject chws, vchw, halt, vhal features into font."""
    config = Config.default.clone()
    # Explicitly set fullwidth_advance to 1000 upem to handle all fonts
    # (prevents Zen Antique and Zen Kurenaido from being skipped as proportional).
    config.fullwidth_advance = 1000

    builder = Builder(str(src_path), config=config)
    await builder.build()
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    builder.save(dest_path)


def subset_and_export(chws_ttf_path: Path, output_base_path: Path) -> None:
    """Subset the font to YAKUMONO_CHARS and export TTF, WOFF, and WOFF2."""
    font = TTFont(chws_ttf_path, recalcTimestamp=False)
    font.recalcTimestamp = False

    options = Options()
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.notdef_outline = True
    options.recalc_bounds = True
    options.recalc_timestamp = False
    options.canonical_order = True

    subsetter = Subsetter(options=options)
    subsetter.populate(text=YAKUMONO_CHARS)
    subsetter.subset(font)

    update_metadata(font)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. TTF
    font.flavor = None
    ttf_out = output_base_path.with_suffix(".ttf")
    font.save(ttf_out)

    # 2. WOFF
    font.flavor = "woff"
    woff_out = output_base_path.with_suffix(".woff")
    font.save(woff_out)

    # 3. WOFF2
    font.flavor = "woff2"
    woff2_out = output_base_path.with_suffix(".woff2")
    font.save(woff2_out)


async def process_font(src_path: Path) -> None:
    """Process a single font file."""
    normalized_src = normalize_font_metrics(src_path)
    kebab_name = to_kebab_case(src_path.name)
    chws_cache = CHWS_CACHE_DIR / src_path.name
    output_base = OUTPUT_DIR / kebab_name

    if not chws_cache.exists():
        print(f"[{src_path.name}] Adding chws features...")
        await add_chws_features(normalized_src, chws_cache)
    else:
        print(f"[{src_path.name}] Using cached chws font.")

    print(
        f"[{src_path.name}] Subsetting & exporting to {kebab_name}.{{ttf,woff,woff2}}..."
    )
    subset_and_export(chws_cache, output_base)


async def main() -> None:
    download_source_fonts()

    source_fonts = sorted(SOURCES_DIR.glob("*.ttf"))
    if not source_fonts:
        print(f"Error: No TTF files found in {SOURCES_DIR}.")
        sys.exit(1)

    print(f"Found {len(source_fonts)} source fonts in {SOURCES_DIR}.")

    for src in source_fonts:
        await process_font(src)

    print(f"\nBuild complete! All fonts generated in {OUTPUT_DIR}/")


if __name__ == "__main__":
    asyncio.run(main())
