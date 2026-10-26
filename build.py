# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "chws-tool==1.4.5",
#     "fonttools==4.67.0",
# ]
# ///

"""Build script for makumi-fonts: OpenType chws injection, subsetting, and export."""

from __future__ import annotations

import asyncio
import re
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path

from east_asian_spacing import Builder, Config
from fontTools.misc import timeTools
from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

YAKUMONO_CHARS = "、。，．・：；（）「」『』［］｛｝【】〈〉《》〔〕〝〟　"

SOURCES_DIR = Path("tmp/sources")
OUTPUT_DIR = Path("fonts")
CSS_DIR = Path("css")

FONT_VERSION = "1.000"
FONT_REVISION = float(FONT_VERSION)
VENDOR_ID = "MKMI"
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
    for repo, rev, filenames in SOURCE_REPOS:
        rev_dir = SOURCES_DIR / rev[:7]
        rev_dir.mkdir(parents=True, exist_ok=True)
        for filename in filenames:
            dest = rev_dir / filename
            if not dest.exists():
                print(f"Downloading {filename}...")
                url = f"https://raw.githubusercontent.com/{repo}/{rev}/fonts/ttf/{filename}"
                tmp = dest.with_suffix(".tmp")
                req = urllib.request.Request(
                    url, headers={"User-Agent": "makumi-fonts-build/1.0"}
                )
                with (
                    urllib.request.urlopen(req, timeout=30) as resp,
                    open(tmp, "wb") as f,
                ):
                    f.write(resp.read())
                tmp.replace(dest)


def output_stem(filename: str) -> str:
    """Convert PascalCase Zen font filename to kebab-case Makumi name."""
    base = filename.removesuffix(".ttf").removeprefix("Zen")
    return "makumi-" + re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", base).lower()


def update_metadata(font: TTFont) -> None:
    """Update font metadata (name, head, OS/2 tables) for Makumi release."""
    font["head"].fontRevision = FONT_REVISION
    font["head"].modified = BUILD_TIMESTAMP
    font["OS/2"].achVendID = VENDOR_ID

    name_table = font["name"]

    def get_name(name_id: int) -> str:
        rec = name_table.getName(name_id, 3, 1, 1033)
        return rec.toUnicode() if rec else ""

    orig_family = get_name(16) or get_name(1)
    new_family = orig_family.replace("Zen", "Makumi")
    description = (
        f"{new_family} is a subset web font for Japanese punctuation marks based on "
        f"{orig_family}, with OpenType chws features added."
    )

    for record in name_table.names:
        nid = record.nameID
        val = record.toUnicode()
        if nid == 0 and AUTHOR_COPYRIGHT not in val:
            record.string = f"{val.rstrip('.')}. {AUTHOR_COPYRIGHT}"
        elif nid == 3:
            record.string = re.sub(
                r"^[^;]+;[^;]+;", f"{FONT_VERSION};{VENDOR_ID};", val
            ).replace("Zen", "Makumi")
        elif nid == 5:
            record.string = f"Version {FONT_VERSION}"
        elif nid in (1, 4, 6, 16):
            record.string = val.replace("Zen", "Makumi")

    name_table.setName(description, 10, 3, 1, 1033)


def normalize_font_metrics(src_path: Path, dest_path: Path) -> Path:
    """Normalize non-1000 advance widths of fullwidth punctuation (e.g. Zen Kurenaido)."""
    font = TTFont(src_path, recalcTimestamp=False)
    hmtx, glyf, cmap = font["hmtx"], font["glyf"], font.getBestCmap()

    if not any(hmtx[cmap[ord(c)]][0] != 1000 for c in YAKUMONO_CHARS if ord(c) in cmap):
        return src_path

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
    res = await builder.build_and_save(dest_path)
    if not res:
        raise RuntimeError(f"Failed to inject chws features into {src_path.name}")


def subset_and_export(chws_ttf_path: Path, output_base_path: Path) -> None:
    """Subset font to YAKUMONO_CHARS and export TTF, WOFF, and WOFF2 formats."""
    font = TTFont(chws_ttf_path, recalcTimestamp=False)

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


async def process_font(src_path: Path, work_dir: Path) -> None:
    """Process a single font: normalize metrics, inject chws, subset, and export."""
    stem = output_stem(src_path.name)
    norm_dest = work_dir / f"norm_{src_path.name}"
    chws_dest = work_dir / f"chws_{src_path.name}"

    norm_src = normalize_font_metrics(src_path, norm_dest)
    await add_chws_features(norm_src, chws_dest)
    print(f"  {src_path.name} -> {stem}")
    subset_and_export(chws_dest, OUTPUT_DIR / stem)


def generate_css() -> None:
    """Generate family and all-in-one CSS files for jsDelivr distribution."""
    CSS_DIR.mkdir(parents=True, exist_ok=True)
    families: dict[str, list[tuple[str, int, str]]] = {}

    for p in sorted(OUTPUT_DIR.glob("*.ttf")):
        font = TTFont(p)
        names = {
            r.nameID: r.toUnicode()
            for r in font["name"].names
            if r.platformID == 3 and r.langID == 1033
        }
        fam = names.get(16) or names[1]
        weight = font["OS/2"].usWeightClass
        slug = fam.lower().replace(" ", "-")
        families.setdefault(slug, []).append((fam, weight, p.stem))

    all_css_blocks: list[str] = []

    for slug, entries in sorted(families.items()):
        entries.sort(key=lambda e: e[1])
        blocks = [
            f"@font-face {{\n"
            f'  font-family: "{fam}";\n'
            f"  font-style: normal;\n"
            f"  font-weight: {weight};\n"
            f"  font-display: swap;\n"
            f"  src:\n"
            f'    url("../fonts/{stem}.woff2") format("woff2"),\n'
            f'    url("../fonts/{stem}.woff") format("woff"),\n'
            f'    url("../fonts/{stem}.ttf") format("truetype");\n'
            f"}}"
            for fam, weight, stem in entries
        ]
        family_css = "\n\n".join(blocks) + "\n"
        (CSS_DIR / f"{slug}.css").write_text(family_css, encoding="utf-8")
        minified = (
            re.sub(r"\s+", " ", re.sub(r"\s*([{:;,])\s*", r"\1", family_css)).strip()
            + "\n"
        )
        (CSS_DIR / f"{slug}.min.css").write_text(minified, encoding="utf-8")
        all_css_blocks.extend(blocks)

    combined_css = "\n\n".join(all_css_blocks) + "\n"
    (CSS_DIR / "makumi.css").write_text(combined_css, encoding="utf-8")
    minified_combined = (
        re.sub(r"\s+", " ", re.sub(r"\s*([{:;,])\s*", r"\1", combined_css)).strip()
        + "\n"
    )
    (CSS_DIR / "makumi.min.css").write_text(minified_combined, encoding="utf-8")


async def main() -> None:
    download_source_fonts()

    source_files = [
        SOURCES_DIR / rev[:7] / filename
        for _, rev, filenames in SOURCE_REPOS
        for filename in filenames
    ]

    print(f"Building {len(source_files)} fonts...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        work_dir = Path(tmp_dir)
        for src in source_files:
            await process_font(src, work_dir)

    generate_css()
    print(f"Build complete: fonts in {OUTPUT_DIR}/, CSS in {CSS_DIR}/")


if __name__ == "__main__":
    asyncio.run(main())
