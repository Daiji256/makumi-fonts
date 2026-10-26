# /// script
# dependencies = [
#     "chws-tool",
#     "fonttools[woff]",
# ]
# ///

"""Build script for makumi-fonts: OpenType chws injection, subsetting, and export."""

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

YAKUMONO_CHARS = "、。，．・：；（）「」『』［］｛｝【】〈〉《》〔〕〝〟　"

SOURCES_DIR = Path("tmp/sources")
NORMALIZED_CACHE_DIR = Path("tmp/normalized")
OUTPUT_DIR = Path("fonts")
CHWS_CACHE_DIR = Path("tmp/chws")

FONT_VERSION_STRING = "Version 1.000"
FONT_REVISION = 1.0
VENDOR_ID = b"MKMI"
AUTHOR_COPYRIGHT = "Copyright 2026 Daiji256."

BUILD_DATE = "2026-10-25T10:00:00Z"
BUILD_TIMESTAMP = timeTools.timestampSinceEpoch(
    datetime.fromisoformat(BUILD_DATE).timestamp()
)

SOURCE_REPOS: list[tuple[str, str, list[str]]] = [
    (
        "googlefonts/zen-antique",
        "3521a97dfa21d4c985725be88e9beb5edef517b9",
        ["ZenAntique-Regular.ttf", "ZenAntiqueSoft-Regular.ttf"],
    ),
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
    (
        "googlefonts/zen-kurenaido",
        "cd751ced55d4ebb1fb2fbd90602eb9351dd03fd6",
        ["ZenKurenaido-Regular.ttf"],
    ),
    (
        "googlefonts/zen-marugothic",
        "553c872b216d1290e2902a466edcdc9682f0df6a",
        [
            f"ZenMaruGothic-{w}.ttf"
            for w in ["Light", "Regular", "Medium", "Bold", "Black"]
        ],
    ),
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
    """Download source Zen fonts if not already cached."""
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    for repo, rev, filenames in SOURCE_REPOS:
        for filename in filenames:
            dest = SOURCES_DIR / filename
            if not dest.exists():
                print(f"Downloading {filename}...")
                url = f"https://raw.githubusercontent.com/{repo}/{rev}/fonts/ttf/{filename}"
                req = urllib.request.Request(
                    url, headers={"User-Agent": "makumi-fonts-build/1.0"}
                )
                with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:
                    f.write(resp.read())


def to_kebab_case(filename: str) -> str:
    """Convert PascalCase font filename to kebab-case."""
    base = re.sub(r"^Zen", "Makumi", filename.removesuffix(".ttf"))
    return re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", base).lower()


def update_metadata(font: TTFont) -> None:
    """Update font metadata (name, head, OS/2 tables) for Makumi release."""
    if "head" in font:
        font["head"].fontRevision = FONT_REVISION
        font["head"].modified = BUILD_TIMESTAMP
    font.recalcTimestamp = False

    if "OS/2" in font:
        font["OS/2"].achVendID = VENDOR_ID

    if "name" not in font:
        return

    name_table = font["name"]

    def get_name(name_id: int) -> str | None:
        rec = name_table.getName(name_id, 3, 1, 1033)
        return rec.toUnicode() if rec else None

    orig_family = get_name(16) or get_name(1) or "Zen"
    new_family = orig_family.replace("Zen", "Makumi")
    description = (
        f"{new_family} is a subset web font for Japanese punctuation marks based on "
        f"{orig_family}, with OpenType chws features added."
    )

    for record in name_table.names:
        nid = record.nameID
        try:
            val = record.toUnicode()
            if nid == 0 and AUTHOR_COPYRIGHT not in val:
                record.string = f"{val.rstrip('.')}. {AUTHOR_COPYRIGHT}"
            elif nid == 3:
                record.string = re.sub(r"^[^;]+;[^;]+;", "1.000;MKMI;", val).replace(
                    "Zen", "Makumi"
                )
            elif nid == 5:
                record.string = FONT_VERSION_STRING
            elif nid in (1, 4, 6, 16):
                record.string = val.replace("Zen", "Makumi")
        except (UnicodeDecodeError, KeyError):
            pass

    name_table.setName(description, 10, 3, 1, 1033)
    name_table.setName(description, 10, 1, 0, 0)


def normalize_font_metrics(src_path: Path) -> Path:
    """Normalize non-1000 advance widths of fullwidth punctuation (e.g. Zen Kurenaido)."""
    font = TTFont(src_path, recalcTimestamp=False)
    font.recalcTimestamp = False
    hmtx, glyf, cmap = font.get("hmtx"), font.get("glyf"), font.getBestCmap()
    if not hmtx or not glyf or not cmap:
        return src_path

    if not any(hmtx[cmap[ord(c)]][0] != 1000 for c in YAKUMONO_CHARS if ord(c) in cmap):
        return src_path

    dest_path = NORMALIZED_CACHE_DIR / src_path.name
    if dest_path.exists():
        return dest_path

    NORMALIZED_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for chars, shift_fn in [
        ("「『【〈《〔〝", lambda d: d),
        ("」』】〉》〕〟、。", lambda _: 0),
        ("・", lambda d: d // 2),
    ]:
        for c in chars:
            code = ord(c)
            if code in cmap:
                gid = cmap[code]
                adv, lsb = hmtx[gid]
                if adv != 1000:
                    shift = shift_fn(1000 - adv)
                    hmtx[gid] = (1000, lsb + shift)
                    if shift:
                        g = glyf[gid]
                        g.xMin += shift
                        g.xMax += shift
                        g.coordinates.translate((shift, 0))

    font["head"].modified = BUILD_TIMESTAMP
    font.save(dest_path)
    return dest_path


async def add_chws_features(src_path: Path, dest_path: Path) -> None:
    """Inject chws, vchw, halt, vhal features into font."""
    config = Config.default.clone()
    config.fullwidth_advance = 1000
    builder = Builder(str(src_path), config=config)
    await builder.build()
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    builder.save(dest_path)


def subset_and_export(chws_ttf_path: Path, output_base_path: Path) -> None:
    """Subset font to YAKUMONO_CHARS and export TTF, WOFF, and WOFF2 formats."""
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
    for ext, flavor in [(".ttf", None), (".woff", "woff"), (".woff2", "woff2")]:
        font.flavor = flavor
        font.save(output_base_path.with_suffix(ext))


async def process_font(src_path: Path) -> None:
    """Process a single font: normalize metrics, inject chws, subset, and export."""
    kebab_name = to_kebab_case(src_path.name)
    chws_cache = CHWS_CACHE_DIR / src_path.name
    if not chws_cache.exists():
        normalized_src = normalize_font_metrics(src_path)
        print(f"  Injecting chws: {src_path.name}...")
        await add_chws_features(normalized_src, chws_cache)

    print(f"  {src_path.name} -> {kebab_name}")
    subset_and_export(chws_cache, OUTPUT_DIR / kebab_name)


async def main() -> None:
    download_source_fonts()

    source_fonts = sorted(SOURCES_DIR.glob("*.ttf"))
    if not source_fonts:
        print(f"Error: No TTF files found in {SOURCES_DIR}.", file=sys.stderr)
        sys.exit(1)

    print(f"Building {len(source_fonts)} fonts...")
    for src in source_fonts:
        await process_font(src)

    print(f"Build complete: all fonts generated in {OUTPUT_DIR}/")


if __name__ == "__main__":
    asyncio.run(main())
