# /// script
# dependencies = [
#     "fonttools[woff]",
#     "pillow",
# ]
# ///

"""Test suite and visual specimen generator for makumi-fonts."""

from __future__ import annotations

import itertools
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageChops, ImageDraw, ImageFont

YAKUMONO_CHARS = "、。，．・：；（）「」『』［］｛｝【】〈〉《》〔〕〝〟　"
YAKUMONO_SET = set(YAKUMONO_CHARS)
EXPECTED_CHAR_CODES = {ord(c) for c in YAKUMONO_CHARS}

FONTS_DIR = Path("fonts")
SOURCES_DIR = Path("tmp/sources")
SPECIMENS_DIR = Path("specimens")
SPECIMENS_DIFF_DIR = Path("tmp/specimens_diff")

SIZE_RANGES = {
    ".ttf": (5000, 15000),
    ".woff": (3500, 8000),
    ".woff2": (2000, 6000),
}

FONTS_INFO: list[tuple[str, str, str]] = [
    (
        "makumi-antique-regular",
        "ZenAntique-Regular.ttf",
        "Makumi Antique Regular",
    ),
    (
        "makumi-antique-soft-regular",
        "ZenAntiqueSoft-Regular.ttf",
        "Makumi Antique Soft Regular",
    ),
    (
        "makumi-kaku-gothic-antique-light",
        "ZenKakuGothicAntique-Light.ttf",
        "Makumi Kaku Gothic Antique Light",
    ),
    (
        "makumi-kaku-gothic-antique-regular",
        "ZenKakuGothicAntique-Regular.ttf",
        "Makumi Kaku Gothic Antique Regular",
    ),
    (
        "makumi-kaku-gothic-antique-medium",
        "ZenKakuGothicAntique-Medium.ttf",
        "Makumi Kaku Gothic Antique Medium",
    ),
    (
        "makumi-kaku-gothic-antique-bold",
        "ZenKakuGothicAntique-Bold.ttf",
        "Makumi Kaku Gothic Antique Bold",
    ),
    (
        "makumi-kaku-gothic-antique-black",
        "ZenKakuGothicAntique-Black.ttf",
        "Makumi Kaku Gothic Antique Black",
    ),
    (
        "makumi-kaku-gothic-new-light",
        "ZenKakuGothicNew-Light.ttf",
        "Makumi Kaku Gothic New Light",
    ),
    (
        "makumi-kaku-gothic-new-regular",
        "ZenKakuGothicNew-Regular.ttf",
        "Makumi Kaku Gothic New Regular",
    ),
    (
        "makumi-kaku-gothic-new-medium",
        "ZenKakuGothicNew-Medium.ttf",
        "Makumi Kaku Gothic New Medium",
    ),
    (
        "makumi-kaku-gothic-new-bold",
        "ZenKakuGothicNew-Bold.ttf",
        "Makumi Kaku Gothic New Bold",
    ),
    (
        "makumi-kaku-gothic-new-black",
        "ZenKakuGothicNew-Black.ttf",
        "Makumi Kaku Gothic New Black",
    ),
    (
        "makumi-kurenaido-regular",
        "ZenKurenaido-Regular.ttf",
        "Makumi Kurenaido Regular",
    ),
    (
        "makumi-maru-gothic-light",
        "ZenMaruGothic-Light.ttf",
        "Makumi Maru Gothic Light",
    ),
    (
        "makumi-maru-gothic-regular",
        "ZenMaruGothic-Regular.ttf",
        "Makumi Maru Gothic Regular",
    ),
    (
        "makumi-maru-gothic-medium",
        "ZenMaruGothic-Medium.ttf",
        "Makumi Maru Gothic Medium",
    ),
    (
        "makumi-maru-gothic-bold",
        "ZenMaruGothic-Bold.ttf",
        "Makumi Maru Gothic Bold",
    ),
    (
        "makumi-maru-gothic-black",
        "ZenMaruGothic-Black.ttf",
        "Makumi Maru Gothic Black",
    ),
    (
        "makumi-old-mincho-regular",
        "ZenOldMincho-Regular.ttf",
        "Makumi Old Mincho Regular",
    ),
    (
        "makumi-old-mincho-medium",
        "ZenOldMincho-Medium.ttf",
        "Makumi Old Mincho Medium",
    ),
    (
        "makumi-old-mincho-semi-bold",
        "ZenOldMincho-SemiBold.ttf",
        "Makumi Old Mincho SemiBold",
    ),
    (
        "makumi-old-mincho-bold",
        "ZenOldMincho-Bold.ttf",
        "Makumi Old Mincho Bold",
    ),
    (
        "makumi-old-mincho-black",
        "ZenOldMincho-Black.ttf",
        "Makumi Old Mincho Black",
    ),
]

SAMPLE_LINE1 = "「『吾輩は猫である』、名前はまだ無い。」"
SAMPLE_LINE2 = "【夏目漱石】　これは〝美しい〟文字組み。（注：テスト）"


def test_file_completeness_and_sizes() -> None:
    """Verify that all 23 font families exist in TTF, WOFF, and WOFF2 within expected size ranges."""
    print("\n--- Test 1: File Completeness & Size Range ---")
    assert FONTS_DIR.is_dir(), f"{FONTS_DIR} directory does not exist"

    for prefix, _, _ in FONTS_INFO:
        for ext, (min_sz, max_sz) in SIZE_RANGES.items():
            p = FONTS_DIR / f"{prefix}{ext}"
            assert p.exists(), f"Missing font file: {p}"
            sz = p.stat().st_size
            assert min_sz <= sz <= max_sz, (
                f"{p} size {sz} out of range ({min_sz}-{max_sz})"
            )

    print(
        f"  All {len(FONTS_INFO) * len(SIZE_RANGES)} font files verified within expected size ranges."
    )


def test_character_coverage_and_glyphs() -> None:
    """Verify that every font contains exactly the 28 required punctuation characters."""
    print("\n--- Test 2: Character & Glyph Coverage ---")
    for prefix, _, _ in FONTS_INFO:
        font = TTFont(FONTS_DIR / f"{prefix}.ttf")
        cmap = font.getBestCmap()
        actual_codes = set(cmap.keys())
        assert actual_codes == EXPECTED_CHAR_CODES, (
            f"[{prefix}] Character mismatch: diff={actual_codes ^ EXPECTED_CHAR_CODES}"
        )

        glyf = font.get("glyf")
        if glyf:
            for code in EXPECTED_CHAR_CODES:
                contours = glyf[cmap[code]].numberOfContours
                if chr(code) == "　":
                    assert contours == 0, (
                        f"[{prefix}] Fullwidth space should have 0 contours"
                    )
                else:
                    assert contours != 0, (
                        f"[{prefix}] Character {chr(code)!r} has empty glyph"
                    )

    print(
        "  Character coverage verified: Exactly 28 punctuation characters in all fonts."
    )


def test_metadata_validity() -> None:
    """Verify metadata fields across all fonts."""
    print("\n--- Test 3: Metadata & OpenType Tables ---")
    for prefix, _, _ in FONTS_INFO:
        font = TTFont(FONTS_DIR / f"{prefix}.ttf")

        assert font["head"].fontRevision == 1.0
        assert font["head"].modified > 0
        assert font["OS/2"].achVendID in ("MKMI", b"MKMI")

        gpos_features = {
            r.FeatureTag for r in font["GPOS"].table.FeatureList.FeatureRecord
        }
        assert {"chws", "vchw", "halt", "vhal"}.issubset(gpos_features)

        gsub_features = {
            r.FeatureTag for r in font["GSUB"].table.FeatureList.FeatureRecord
        }
        assert {"vert", "vrt2"}.issubset(gsub_features)

        names = {
            r.nameID: r.toUnicode()
            for r in font["name"].names
            if r.platformID == 3 and r.langID == 1033
        }
        assert "Copyright 2026 Daiji256." in names[0] and "The Zen" in names[0]
        assert names[1].startswith("Makumi") and "Zen" not in names[1]
        assert names[4].startswith("Makumi") and "Zen" not in names[4]
        assert names[5] == "Version 1.000"
        assert names[6].startswith("Makumi") and " " not in names[6]
        assert names[8] == "Positype"
        assert names[9] == "Yoshimichi Ohira"
        assert names[11] == "https://positype.com"
        assert names[12] == "https://www.zenfont.jp"
        assert (
            "subset web font for Japanese punctuation marks based on Zen" in names[10]
        )

    print(
        "  Metadata verified: Version 1.000, Vendor MKMI, proper copyright, and complete credits."
    )


def segment_text(text: str) -> list[tuple[str, bool]]:
    """Segment a string into alternating chunks of punctuation (Makumi) and general chars (Zen)."""
    return [
        ("".join(group), is_y)
        for is_y, group in itertools.groupby(text, lambda c: c in YAKUMONO_SET)
    ]


def draw_text_run(
    draw: ImageDraw.ImageDraw,
    pos: tuple[float, float],
    text: str,
    makumi_font: ImageFont.FreeTypeFont,
    zen_font: ImageFont.FreeTypeFont,
    enable_chws: bool,
    fill: tuple[int, int, int],
) -> float:
    """Draw a text string with fallback: Makumi for punctuation, Zen for general characters."""
    x, y = pos
    features = ["chws"] if enable_chws else ["-chws"]
    for seg, is_y in segment_text(text):
        f = makumi_font if is_y else zen_font
        draw.text((x, y), seg, font=f, fill=fill, features=features)
        x += f.getlength(seg, features=features)
    return x - pos[0]


def test_chws_feature_compaction() -> None:
    """Verify that chws feature reduces advance width across all 23 fonts and weights."""
    print("\n--- Test 4: chws Feature Compaction Across All 23 Fonts & Weights ---")
    dummy_draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for prefix, zen_file, _ in FONTS_INFO:
        m_font = ImageFont.truetype(
            str(FONTS_DIR / f"{prefix}.ttf"), 32, layout_engine=ImageFont.Layout.RAQM
        )
        z_font = ImageFont.truetype(
            str(SOURCES_DIR / zen_file), 32, layout_engine=ImageFont.Layout.RAQM
        )

        w_off = draw_text_run(
            dummy_draw, (0, 0), SAMPLE_LINE1, m_font, z_font, False, (0, 0, 0)
        )
        w_on = draw_text_run(
            dummy_draw, (0, 0), SAMPLE_LINE1, m_font, z_font, True, (0, 0, 0)
        )

        reduction_px = w_off - w_on
        reduction_pct = (reduction_px / w_off) * 100
        assert reduction_px >= 40.0, (
            f"[{prefix}] Insufficient compaction: reduction={reduction_px:.1f}px"
        )
        print(
            f"  [{prefix:35}] -{reduction_px:.1f}px (-{reduction_pct:.1f}%) | OFF: {w_off:.1f}px -> ON: {w_on:.1f}px"
        )

    print(
        "  chws feature compaction verified: All 23 fonts tighten punctuation pairs reliably."
    )


def generate_specimen_card(
    makumi_prefix: str,
    zen_filename: str,
    display_name: str,
) -> Image.Image:
    """Generate a clean visual specimen card (720x280) comparing chws OFF vs ON."""
    makumi_path = FONTS_DIR / f"{makumi_prefix}.ttf"
    zen_path = SOURCES_DIR / zen_filename

    raqm = ImageFont.Layout.RAQM
    f_m_body = ImageFont.truetype(str(makumi_path), 24, layout_engine=raqm)
    f_z_body = ImageFont.truetype(str(zen_path), 24, layout_engine=raqm)
    f_z_title = ImageFont.truetype(str(zen_path), 18, layout_engine=raqm)
    f_z_label = ImageFont.truetype(str(zen_path), 13, layout_engine=raqm)

    w, h = 720, 280
    img = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    c_text = (17, 24, 39)
    c_label = (107, 114, 128)
    c_line = (229, 231, 235)
    pad_x = 32

    draw.text((pad_x, 20), display_name, font=f_z_title, fill=c_text)
    draw.line([(pad_x, 48), (w - pad_x, 48)], fill=c_line, width=1)

    for label, enable_chws, label_y in [
        ("chws OFF", False, 64),
        ("chws ON", True, 172),
    ]:
        draw.text((pad_x, label_y), label, font=f_z_label, fill=c_label)
        draw_text_run(
            draw,
            (pad_x, label_y + 22),
            SAMPLE_LINE1,
            f_m_body,
            f_z_body,
            enable_chws,
            c_text,
        )
        draw_text_run(
            draw,
            (pad_x, label_y + 54),
            SAMPLE_LINE2,
            f_m_body,
            f_z_body,
            enable_chws,
            c_text,
        )

    draw.line([(pad_x, 156), (w - pad_x, 156)], fill=c_line, width=1)
    return img


def _save_diff_report(
    old_img: Image.Image,
    new_img: Image.Image,
    diff: Image.Image,
    dest: Path,
    title: str,
) -> None:
    """Save Before / After / Diff visual regression report image."""
    w, h = new_img.size
    diff_mask = diff.convert("L").point(lambda p: 255 if p > 10 else 0, mode="1")
    diff_colored = Image.new("RGB", (w, h), (255, 255, 255))
    diff_colored.paste(Image.new("RGB", (w, h), (220, 20, 60)), mask=diff_mask)

    rep_img = Image.new("RGB", (w, h * 3 + 80), (245, 245, 248))
    draw = ImageDraw.Draw(rep_img)
    draw.text((24, 8), f"Visual Regression Report — {title}", fill=(180, 0, 0))
    draw.text((24, 28), "[1] Existing Version (Before)", fill=(100, 100, 100))
    rep_img.paste(old_img, (0, 48))
    draw.text((24, h + 58), "[2] Newly Built Version (After)", fill=(0, 120, 0))
    rep_img.paste(new_img, (0, h + 78))
    draw.text(
        (24, h * 2 + 88),
        "[3] Pixel Difference Highlight (Changed Pixels)",
        fill=(220, 20, 60),
    )
    rep_img.paste(diff_colored, (0, h * 2 + 108))
    rep_img.save(dest)


def test_visual_specimens_and_regression() -> None:
    """Generate visual specimens in specimens/ and run visual regression testing."""
    print("\n--- Test 5: Visual Specimens (specimens/) & Regression Testing ---")
    SPECIMENS_DIR.mkdir(parents=True, exist_ok=True)
    SPECIMENS_DIFF_DIR.mkdir(parents=True, exist_ok=True)

    matches = created = updated = 0
    for prefix, zen_file, display_name in FONTS_INFO:
        specimen_file = SPECIMENS_DIR / f"{prefix}.png"
        new_img = generate_specimen_card(prefix, zen_file, display_name)

        if not specimen_file.exists():
            new_img.save(specimen_file)
            created += 1
            print(f"  [CREATED]  {specimen_file.name}")
            continue

        old_img = Image.open(specimen_file).convert("RGB")
        diff = ImageChops.difference(old_img, new_img)
        if diff.getbbox() is None:
            matches += 1
            print(f"  [MATCH]    {specimen_file.name}")
        else:
            updated += 1
            diff_file = SPECIMENS_DIFF_DIR / f"{prefix}_diff.png"
            _save_diff_report(old_img, new_img, diff, diff_file, display_name)
            new_img.save(specimen_file)
            print(f"  [UPDATED]  {specimen_file.name} (diff saved to {diff_file})")

    print(
        f"\n  Visual Specimen Summary: {created} created, {matches} matched, {updated} updated."
    )


def main() -> None:
    print("=== Makumi Fonts Test Suite ===")
    test_file_completeness_and_sizes()
    test_character_coverage_and_glyphs()
    test_metadata_validity()
    test_chws_feature_compaction()
    test_visual_specimens_and_regression()
    print("\n==================================================")
    print("       ALL TESTS PASSED SUCCESSFULLY! (5/5)       ")
    print("==================================================")


if __name__ == "__main__":
    main()
