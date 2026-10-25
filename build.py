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
from pathlib import Path
import re
import sys

from east_asian_spacing import Builder, Config
from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

# 28 punctuation characters (JIS / east-asian-spacing aligned order)
YAKUMONO_CHARS = "、。，．・：；（）「」『』［］｛｝【】〈〉《》〔〕〝〟　"

SOURCES_DIR = Path("tmp/sources")
OUTPUT_DIR = Path("fonts")
CHWS_CACHE_DIR = Path("tmp/chws")


def to_kebab_case(filename: str) -> str:
    """Convert PascalCase font filename to kebab-case.

    e.g. ZenAntiqueSoft-Regular.ttf -> makumi-antique-soft-regular
    """
    base = filename.replace(".ttf", "")
    base = re.sub(r"^Zen", "Makumi", base)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", base)
    s = s.replace("_", "-").lower()
    return re.sub(r"-+", "-", s)


def rename_zen_to_makumi(text: str) -> str:
    """Replace Zen branding with Makumi in name records."""
    text = text.replace("ZEN!", "MAKUMI").replace("ZEN", "MAKUMI")
    text = text.replace("Zen", "Makumi")
    return text


def update_name_table(font: TTFont) -> None:
    """Update name table records to reflect the Makumi brand."""
    if "name" not in font:
        return
    for record in font["name"].names:
        try:
            val = record.toUnicode()
            new_val = rename_zen_to_makumi(val)
            if new_val != val:
                record.string = new_val
        except Exception:
            pass


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
    font = TTFont(chws_ttf_path)

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

    update_name_table(font)

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
    kebab_name = to_kebab_case(src_path.name)
    chws_cache = CHWS_CACHE_DIR / src_path.name
    output_base = OUTPUT_DIR / kebab_name

    if not chws_cache.exists():
        print(f"[{src_path.name}] Adding chws features...")
        await add_chws_features(src_path, chws_cache)
    else:
        print(f"[{src_path.name}] Using cached chws font.")

    print(f"[{src_path.name}] Subsetting & exporting to {kebab_name}.{{ttf,woff,woff2}}...")
    subset_and_export(chws_cache, output_base)


async def main() -> None:
    if not SOURCES_DIR.exists():
        print(f"Error: {SOURCES_DIR} does not exist. Run source download first.")
        sys.exit(1)

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
