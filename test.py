# /// script
# dependencies = [
#     "fonttools[woff]",
#     "pillow",
# ]
# ///

"""Test suite and visual specimen generator for makumi-fonts.

Tests:
1. File completeness & sizes: Verify all 23 fonts exist in TTF, WOFF, and WOFF2 within valid size ranges.
2. Character coverage & glyphs: Verify exactly 28 punctuation characters in cmap, with no extra or missing glyphs.
3. Metadata completeness: Verify name, head, OS/2, GPOS/GSUB table records across all fonts.
4. chws feature compaction: Verify that chws properly compacts text across all 23 fonts and weights.
5. Visual specimens & regression:
   Generate specimen images in specimens/ (combining Makumi punctuation and Zen body text, chws OFF vs ON).
   Compare against existing specimen files:
   - If identical: do not touch the existing file (preventing binary Git diffs).
   - If visual diff detected: update specimens/ and output Before/After/Diff comparison images to
     tmp/specimens_diff/ (untracked).
"""

from __future__ import annotations

from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageChops, ImageDraw, ImageFont

# 28 punctuation characters (same as in build.py)
YAKUMONO_CHARS = "、。，．・：；（）「」『』［］｛｝【】〈〉《》〔〕〝〟　"
YAKUMONO_SET = set(YAKUMONO_CHARS)
EXPECTED_CHAR_CODES = {ord(c) for c in YAKUMONO_CHARS}

FONTS_DIR = Path("fonts")
SOURCES_DIR = Path("tmp/sources")
SPECIMENS_DIR = Path("specimens")
SPECIMENS_DIFF_DIR = Path("tmp/specimens_diff")

# All 23 font families in alphabetical order with Zen source mapping and display names
FONTS_INFO: list[tuple[str, str, str]] = [
    # 1. Zen Antique (2 fonts)
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
    # 2. Zen Kaku Gothic Antique (5 fonts)
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
    # 3. Zen Kaku Gothic New (5 fonts)
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
    # 4. Zen Kurenaido (1 font)
    (
        "makumi-kurenaido-regular",
        "ZenKurenaido-Regular.ttf",
        "Makumi Kurenaido Regular",
    ),
    # 5. Zen Maru Gothic (5 fonts)
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
    # 6. Zen Old Mincho (5 fonts)
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

EXPECTED_FAMILIES = [info[0] for info in FONTS_INFO]

# Representative sample texts showcasing punctuation combinations, double minutes, and fullwidth space
SAMPLE_LINE1 = "「『吾輩は猫である』、名前はまだ無い。」"
SAMPLE_LINE2 = "【夏目漱石】　これは〝美しい〟文字組み。（注：テスト）"


def test_file_completeness_and_sizes():
    """Verify that all 23 font families exist in TTF, WOFF, and WOFF2 formats."""
    print("\n--- Test 1: File Completeness & Size Range ---")
    assert FONTS_DIR.exists(), f"{FONTS_DIR} directory does not exist"

    total_files = 0
    for prefix in EXPECTED_FAMILIES:
        for ext in [".ttf", ".woff", ".woff2"]:
            p = FONTS_DIR / f"{prefix}{ext}"
            assert p.exists(), f"Missing font file: {p}"
            sz = p.stat().st_size
            total_files += 1

            if ext == ".ttf":
                assert 5000 <= sz <= 15000, (
                    f"{p} size {sz} is out of expected TTF range (5KB-15KB)"
                )
            elif ext == ".woff":
                assert 3500 <= sz <= 8000, (
                    f"{p} size {sz} is out of expected WOFF range (3.5KB-8KB)"
                )
            elif ext == ".woff2":
                assert 2000 <= sz <= 6000, (
                    f"{p} size {sz} is out of expected WOFF2 range (2KB-6KB)"
                )

    assert total_files == 69, f"Expected 69 font files, found {total_files}"
    print("  All 69 font files verified within expected size ranges.")


def test_character_coverage_and_glyphs():
    """Verify that every font contains exactly the 28 required punctuation characters."""
    print("\n--- Test 2: Character & Glyph Coverage ---")
    for prefix in EXPECTED_FAMILIES:
        ttf_path = FONTS_DIR / f"{prefix}.ttf"
        font = TTFont(ttf_path)
        cmap = font.getBestCmap()

        # Check character set equality
        actual_codes = set(cmap.keys())
        missing = EXPECTED_CHAR_CODES - actual_codes
        extra = actual_codes - EXPECTED_CHAR_CODES

        assert not missing, (
            f"[{prefix}] Missing characters: {[chr(c) for c in missing]}"
        )
        assert not extra, (
            f"[{prefix}] Unexpected extra characters: {[chr(c) for c in extra]}"
        )
        assert len(actual_codes) == 28, (
            f"[{prefix}] Expected 28 characters, found {len(actual_codes)}"
        )

        # Check glyph data (all characters except fullwidth space should have non-empty outlines)
        glyf_table = font.get("glyf")
        if glyf_table:
            for code in EXPECTED_CHAR_CODES:
                ch = chr(code)
                glyph_name = cmap[code]
                glyph = glyf_table[glyph_name]
                if ch == "　":
                    assert glyph.numberOfContours == 0, (
                        f"[{prefix}] Fullwidth space should have 0 contours"
                    )
                else:
                    assert glyph.numberOfContours != 0, (
                        f"[{prefix}] Character '{ch}' has empty glyph"
                    )

    print(
        "  Character coverage verified: Exactly 28 punctuation characters in all fonts."
    )


def test_metadata_validity():
    """Verify that all metadata fields are complete, correct, and free of leftover Zen branding."""
    print("\n--- Test 3: Metadata & OpenType Tables ---")
    for prefix in EXPECTED_FAMILIES:
        ttf_path = FONTS_DIR / f"{prefix}.ttf"
        font = TTFont(ttf_path)

        # 1. head table
        head = font["head"]
        assert head.fontRevision == 1.0, (
            f"[{prefix}] head.fontRevision is {head.fontRevision}, expected 1.0"
        )
        assert head.modified > 0, f"[{prefix}] head.modified timestamp is invalid"

        # 2. OS/2 table
        os2 = font["OS/2"]
        assert os2.achVendID in ("MKMI", b"MKMI"), (
            f"[{prefix}] OS/2.achVendID is {os2.achVendID}, expected 'MKMI'"
        )

        # 3. GPOS features
        gpos = font["GPOS"].table
        gpos_features = {r.FeatureTag for r in gpos.FeatureList.FeatureRecord}
        required_gpos = {"chws", "vchw", "halt", "vhal"}
        assert required_gpos.issubset(gpos_features), (
            f"[{prefix}] Missing GPOS features: {required_gpos - gpos_features}"
        )

        # 4. GSUB features
        gsub = font["GSUB"].table
        gsub_features = {r.FeatureTag for r in gsub.FeatureList.FeatureRecord}
        required_gsub = {"vert", "vrt2"}
        assert required_gsub.issubset(gsub_features), (
            f"[{prefix}] Missing GSUB features: {required_gsub - gsub_features}"
        )

        # 5. name table
        names = {
            r.nameID: r.toUnicode()
            for r in font["name"].names
            if r.platformID == 3 and r.langID == 1033
        }

        # Copyright
        assert "Copyright 2026 Daiji256." in names[0], (
            f"[{prefix}] Copyright missing Daiji256"
        )
        assert "The Zen" in names[0], (
            f"[{prefix}] Copyright should preserve original Zen authors credit"
        )

        # Family & Full Name
        assert names[1].startswith("Makumi"), (
            f"[{prefix}] Family name does not start with Makumi: {names[1]}"
        )
        assert "Zen" not in names[1], (
            f"[{prefix}] Family name still contains Zen: {names[1]}"
        )
        assert names[4].startswith("Makumi"), (
            f"[{prefix}] Full name does not start with Makumi: {names[4]}"
        )
        assert "Zen" not in names[4], (
            f"[{prefix}] Full name still contains Zen: {names[4]}"
        )

        # Version & PostScript
        assert names[5] == "Version 1.000", (
            f"[{prefix}] Version string is {names[5]}, expected Version 1.000"
        )
        assert names[6].startswith("Makumi"), (
            f"[{prefix}] PostScript name does not start with Makumi: {names[6]}"
        )
        assert " " not in names[6], (
            f"[{prefix}] PostScript name contains spaces: {names[6]}"
        )

        # Vendor & Designer credits
        assert names[8] == "Positype", f"[{prefix}] Manufacturer should be Positype"
        assert names[9] == "Yoshimichi Ohira", (
            f"[{prefix}] Designer should be Yoshimichi Ohira"
        )
        assert names[11] == "https://positype.com"
        assert names[12] == "https://www.zenfont.jp"

        # Description (NameID 10)
        assert 10 in names, f"[{prefix}] Missing Description (NameID 10)"
        assert (
            "subset web font for Japanese punctuation marks based on Zen" in names[10]
        )

    print(
        "  Metadata verified: Version 1.000, Vendor MKMI, proper copyright, and complete credits."
    )


def segment_text(text: str) -> list[tuple[str, bool]]:
    """Segment a string into alternating chunks of punctuation (Makumi) and general chars (Zen)."""
    if not text:
        return []
    segments: list[tuple[str, bool]] = []
    curr_is_y = text[0] in YAKUMONO_SET
    curr_chars = [text[0]]
    for ch in text[1:]:
        is_y = ch in YAKUMONO_SET
        if is_y == curr_is_y:
            curr_chars.append(ch)
        else:
            segments.append(("".join(curr_chars), curr_is_y))
            curr_chars = [ch]
            curr_is_y = is_y
    segments.append(("".join(curr_chars), curr_is_y))
    return segments


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
    segments = segment_text(text)
    for seg, is_y in segments:
        f = makumi_font if is_y else zen_font
        draw.text((x, y), seg, font=f, fill=fill, features=features)
        x += f.getlength(seg, features=features)
    return x - pos[0]


def test_chws_feature_compaction():
    """Verify that chws feature reduces advance width across all 23 fonts and weights."""
    print("\n--- Test 4: chws Feature Compaction Across All 23 Fonts & Weights ---")
    for makumi_prefix, zen_filename, display_name in FONTS_INFO:
        makumi_path = FONTS_DIR / f"{makumi_prefix}.ttf"
        zen_path = SOURCES_DIR / zen_filename

        m_font = ImageFont.truetype(
            str(makumi_path), 32, layout_engine=ImageFont.Layout.RAQM
        )
        z_font = ImageFont.truetype(
            str(zen_path), 32, layout_engine=ImageFont.Layout.RAQM
        )

        # Measure text advance width with chws OFF and ON
        dummy_img = Image.new("RGB", (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_img)

        w_off = draw_text_run(
            dummy_draw, (0, 0), SAMPLE_LINE1, m_font, z_font, False, (0, 0, 0)
        )
        w_on = draw_text_run(
            dummy_draw, (0, 0), SAMPLE_LINE1, m_font, z_font, True, (0, 0, 0)
        )

        reduction_px = w_off - w_on
        reduction_pct = (reduction_px / w_off) * 100

        # Assert that chws properly compacts punctuation spacing
        assert reduction_px >= 40.0, (
            f"[{makumi_prefix}] Insufficient compaction: reduction={reduction_px:.1f}px (w_off={w_off:.1f}, w_on={w_on:.1f})"
        )
        print(
            f"  [{makumi_prefix:35}] -{reduction_px:.1f}px (-{reduction_pct:.1f}%) | OFF: {w_off:.1f}px -> ON: {w_on:.1f}px"
        )

    print(
        "  chws feature compaction verified: All 23 fonts tighten punctuation pairs reliably."
    )


def generate_specimen_card(
    makumi_prefix: str,
    zen_filename: str,
    display_name: str,
) -> Image.Image:
    """Generate a clean, compact visual specimen card with minimal styling."""
    makumi_path = FONTS_DIR / f"{makumi_prefix}.ttf"
    zen_path = SOURCES_DIR / zen_filename

    body_size = 24
    title_size = 18
    label_size = 13

    f_m_body = ImageFont.truetype(
        str(makumi_path), body_size, layout_engine=ImageFont.Layout.RAQM
    )
    f_z_body = ImageFont.truetype(
        str(zen_path), body_size, layout_engine=ImageFont.Layout.RAQM
    )
    f_z_title = ImageFont.truetype(
        str(zen_path), title_size, layout_engine=ImageFont.Layout.RAQM
    )
    f_z_label = ImageFont.truetype(
        str(zen_path), label_size, layout_engine=ImageFont.Layout.RAQM
    )

    w, h = 720, 280
    img = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    c_text = (17, 24, 39)  # #111827 Dark neutral text
    c_label = (107, 114, 128)  # #6B7280 Muted gray label
    c_line = (229, 231, 235)  # #E5E7EB Subtle divider line
    pad_x = 32

    # Title: font family name
    y = 20
    draw.text((pad_x, y), display_name, font=f_z_title, fill=c_text)

    # Title bottom divider line
    draw.line([(pad_x, 48), (w - pad_x, 48)], fill=c_line, width=1)

    # Section 1: chws OFF
    draw.text((pad_x, 64), "chws OFF", font=f_z_label, fill=c_label)
    draw_text_run(draw, (pad_x, 86), SAMPLE_LINE1, f_m_body, f_z_body, False, c_text)
    draw_text_run(draw, (pad_x, 118), SAMPLE_LINE2, f_m_body, f_z_body, False, c_text)

    # Mid section divider line
    draw.line([(pad_x, 156), (w - pad_x, 156)], fill=c_line, width=1)

    # Section 2: chws ON
    draw.text((pad_x, 172), "chws ON", font=f_z_label, fill=c_label)
    draw_text_run(draw, (pad_x, 194), SAMPLE_LINE1, f_m_body, f_z_body, True, c_text)
    draw_text_run(draw, (pad_x, 226), SAMPLE_LINE2, f_m_body, f_z_body, True, c_text)

    return img


def test_visual_specimens_and_regression():
    """Generate visual specimens in specimens/ and run visual regression testing.

    If a specimen file exists and has identical pixels, it is NOT overwritten (preserving binary reproducibility).
    If a visual diff is detected, the specimen is updated and a Before/After/Diff comparison is saved
    to tmp/specimens_diff/ for inspection.
    """
    print("\n--- Test 5: Visual Specimens (specimens/) & Regression Testing ---")
    SPECIMENS_DIR.mkdir(parents=True, exist_ok=True)
    SPECIMENS_DIFF_DIR.mkdir(parents=True, exist_ok=True)

    matches_count = 0
    created_count = 0
    updated_count = 0

    for makumi_prefix, zen_filename, display_name in FONTS_INFO:
        specimen_file = SPECIMENS_DIR / f"{makumi_prefix}.png"
        new_img = generate_specimen_card(makumi_prefix, zen_filename, display_name)

        if not specimen_file.exists():
            # First-time creation
            new_img.save(specimen_file)
            created_count += 1
            print(f"  [CREATED]  {specimen_file.name}")
        else:
            # Visual regression comparison against existing specimen
            old_img = Image.open(specimen_file).convert("RGB")
            diff = ImageChops.difference(old_img, new_img)
            diff_bbox = diff.getbbox()

            if diff_bbox is None:
                # 100% pixel identical: DO NOT overwrite (preserves exact binary and timestamp)
                matches_count += 1
                print(
                    f"  [MATCH]    {specimen_file.name} (100% pixel match, no binary diff)"
                )
            else:
                # Visual difference detected: Update specimen and output regression diff
                updated_count += 1
                diff_colored = Image.new("RGB", new_img.size, (255, 255, 255))
                w, h = new_img.size
                for y in range(h):
                    for x in range(w):
                        r, g, b = diff.getpixel((x, y))
                        if r > 10 or g > 10 or b > 10:
                            diff_colored.putpixel((x, y), (220, 20, 60))

                # Composite 3-tier regression report (Before, After, Diff Highlight)
                rep_h = h * 3 + 80
                rep_img = Image.new("RGB", (w, rep_h), (245, 245, 248))
                rep_draw = ImageDraw.Draw(rep_img)

                rep_draw.text(
                    (24, 8),
                    f"Visual Regression Report — {display_name}",
                    fill=(180, 0, 0),
                )
                rep_draw.text(
                    (24, 28), "[1] Existing Version (Before)", fill=(100, 100, 100)
                )
                rep_img.paste(old_img, (0, 48))

                rep_draw.text(
                    (24, h + 58), "[2] Newly Built Version (After)", fill=(0, 120, 0)
                )
                rep_img.paste(new_img, (0, h + 78))

                rep_draw.text(
                    (24, h * 2 + 88),
                    "[3] Pixel Difference Highlight (Crimson Red = Changed Pixels)",
                    fill=(220, 20, 60),
                )
                rep_img.paste(diff_colored, (0, h * 2 + 108))

                diff_report_file = SPECIMENS_DIFF_DIR / f"{makumi_prefix}_diff.png"
                rep_img.save(diff_report_file)

                # Overwrite specimen file so Git notices the update
                new_img.save(specimen_file)
                print(
                    f"  [UPDATED]  {specimen_file.name} (Visual diff detected! Saved diff report to tmp/specimens_diff/{diff_report_file.name})"
                )

    print(
        f"\n  Visual Specimen Summary: {created_count} created, {matches_count} matched (untouched), {updated_count} updated."
    )


def main():
    print("==================================================")
    print("      MAKUMI FONTS COMPREHENSIVE TEST SUITE       ")
    print("==================================================")
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
