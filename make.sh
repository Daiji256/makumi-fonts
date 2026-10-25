#!/usr/bin/env bash
set -euo pipefail

# Directories
SOURCES_DIR="tmp/sources"
mkdir -p "${SOURCES_DIR}"

# Latest commit hashes of Zen font repositories (in alphabetical order)
ZEN_ANTIQUE_REV="3521a97dfa21d4c985725be88e9beb5edef517b9"
ZEN_KAKUGOTHIC_REV="2705757e17e42954f3acbdf921ac0ae24d1270cd"
ZEN_KURENAIDO_REV="cd751ced55d4ebb1fb2fbd90602eb9351dd03fd6"
ZEN_MARUGOTHIC_REV="553c872b216d1290e2902a466edcdc9682f0df6a"
ZEN_OLDMINCHO_REV="490d363e7886839ba1f86971cf874a1d70ad27f0"

download_font() {
  local repo="$1"
  local rev="$2"
  local filename="$3"
  local dest="${SOURCES_DIR}/${filename}"

  if [ -f "${dest}" ]; then
    echo "Already exists: ${dest}"
    return 0
  fi

  local url="https://raw.githubusercontent.com/${repo}/${rev}/fonts/ttf/${filename}"
  echo "Downloading ${filename} from ${repo} (${rev:0:7})..."
  curl -fsSL "${url}" -o "${dest}"
}

echo "=== Downloading Zen Fonts (Japanese font families, alphabetical order) ==="

# 1. Zen Antique & Zen Antique Soft (2 fonts)
download_font "googlefonts/zen-antique" "${ZEN_ANTIQUE_REV}" "ZenAntique-Regular.ttf"
download_font "googlefonts/zen-antique" "${ZEN_ANTIQUE_REV}" "ZenAntiqueSoft-Regular.ttf"

# 2. Zen Kaku Gothic Antique (5 weights)
for w in Light Regular Medium Bold Black; do
  download_font "googlefonts/zen-kakugothic" "${ZEN_KAKUGOTHIC_REV}" "ZenKakuGothicAntique-${w}.ttf"
done

# 3. Zen Kaku Gothic New (5 weights)
for w in Light Regular Medium Bold Black; do
  download_font "googlefonts/zen-kakugothic" "${ZEN_KAKUGOTHIC_REV}" "ZenKakuGothicNew-${w}.ttf"
done

# 4. Zen Kurenaido (1 weight)
download_font "googlefonts/zen-kurenaido" "${ZEN_KURENAIDO_REV}" "ZenKurenaido-Regular.ttf"

# 5. Zen Maru Gothic (5 weights)
for w in Light Regular Medium Bold Black; do
  download_font "googlefonts/zen-marugothic" "${ZEN_MARUGOTHIC_REV}" "ZenMaruGothic-${w}.ttf"
done

# 6. Zen Old Mincho (5 weights)
for w in Regular Medium SemiBold Bold Black; do
  download_font "googlefonts/zen-oldmincho" "${ZEN_OLDMINCHO_REV}" "ZenOldMincho-${w}.ttf"
done

echo "=== All source fonts downloaded successfully ==="

echo "=== Building Makumi Web Fonts ==="
uv run build.py

if [ "${1:-}" = "test" ]; then
  echo "=== Running Makumi Font Tests ==="
  uv run test.py
fi
