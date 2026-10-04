#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# urduofdani :: build_assets.sh
# Rebuilds the branded raster assets (banner, logo, social preview) from
# assets/banner-bg.jpg (the base artwork) using ImageMagick.
#
#   bash assets/build_assets.sh
#
# Requires: ImageMagick 6+ (convert), DejaVu fonts.
# ---------------------------------------------------------------------------
set -euo pipefail

cd "$(dirname "$0")"

BG="banner-bg.jpg"
TEAL="#14b8a6"
VIOLET="#8b5cf6"
INK="#0b1220"
WHITE="#ffffff"
MUTED="#9fb3c8"
FONT_B="DejaVu-Sans-Bold"
FONT_R="DejaVu-Sans"

# PNG that stays small but keeps smooth gradients
STRIP='-strip -define png:compression-filter=5 -define png:compression-level=9 -define png:compression-strategy=1'

# ---------------------------------------------------------------- 1. BANNER
# 1600x500 crop of the artwork, darkened on the left so the wordmark pops.
convert "$BG" -resize 1600x500^ -gravity center -crop 1600x500+0+0 +repage \
  -strip -define png:compression-level=9 banner-base.png

# soft left scrim: a solid ink layer whose ALPHA comes from a real gradient mask
# (IM6 cannot interpolate alpha in "-size WxH gradient:#rrggbbaa" reliably)
convert -size 1600x500 gradient:white-black -alpha off scrim-mask.png
convert -size 1600x500 xc:"#0b1220" scrim-mask.png -alpha off \
  -compose CopyOpacity -composite banner-dark.png
convert banner-base.png banner-dark.png -compose over -composite banner-dark2.png

# horizontal gradient accent rule (teal -> violet)
convert -size 268x6 gradient:"$TEAL-$VIOLET" rule.png

# chip behind the bottom accent line
convert banner-dark2.png \
  -fill "#0e1729" -stroke "#31486b" -strokewidth 2 \
  -draw "roundrectangle 90,398 782,444 22,22" \
  -stroke none chipped.png

# wordmark (with soft shadow), rule, tagline, stats, accent line
convert chipped.png \
  -font "$FONT_B" -fill "#00000088" -pointsize 108 -kerning 1 -annotate +95+243 "urduofdani" \
  -font "$FONT_B" -fill "$WHITE" -pointsize 108 -kerning 1 -annotate +92+240 "urduofdani" \
  \( rule.png \) -geometry +94+282 -compose over -composite \
  -font "$FONT_B" -fill "$MUTED" -pointsize 22 -kerning 5 -annotate +94+336 "MODERN HIGH-SPEED URDU TEXT ENGINE" \
  -font "$FONT_R" -fill "#8fa6c0" -pointsize 19 -kerning 3 -annotate +94+380 "25,320 WORDS      73.0 KB .GZ      ~2.9 MS LOAD      0 DEPENDENCIES" \
  -font "$FONT_B" -fill "$TEAL" -pointsize 20 -kerning 3 -annotate +112+429 "SINGLE-SPACE TOKENIZATION  x  GZIP LEVEL 9" \
  $STRIP banner.png

# lossless master (banner.png) + fast-loading JPEG used by the README
convert banner.png -sampling-factor 4:4:4 -quality 94 -strip banner.jpg

rm -f banner-base.png banner-dark.png banner-dark2.png chipped.png scrim-mask.png rule.png

# ----------------------------------------------------------------- 2. LOGO
# Dark rounded tile, gradient border ring, gradient alef bar, teal dot.
convert -size 512x512 xc:none -fill "$INK" -draw "roundrectangle 8,8 504,504 112,112" logo-base.png

# horizontal gradient (exact rotation, so the mask never leaks outside the ring)
convert -size 512x512 gradient:"$TEAL-$VIOLET" -rotate 90 logo-grad.png

# ring mask: outer rounded rect minus inner rounded rect
convert -size 512x512 xc:black -fill white -draw "roundrectangle 8,8 504,504 112,112" \
  -fill black -draw "roundrectangle 22,22 490,490 100,100" -alpha off ring-mask.png
convert logo-grad.png ring-mask.png -alpha off -compose CopyOpacity -composite ring.png

# alef bar mask (vertical rounded bar) -> gradient through it
convert -size 512x512 xc:black -fill white -draw "roundrectangle 228,102 284,330 28,28" -alpha off bar-mask.png
convert logo-grad.png bar-mask.png -alpha off -compose CopyOpacity -composite bar.png

# soft glow behind the mark
convert -size 512x512 xc:none -fill "#ffffff2e" -draw "roundrectangle 228,102 284,330 28,28" \
  -blur 0x26 glow.png

convert logo-base.png glow.png -compose over -composite \
  ring.png -compose over -composite \
  bar.png -compose over -composite \
  -fill "#2dd4bf" -stroke none -draw "circle 186,394 186,420" \
  -fill "#ffffff" -draw "circle 186,394 186,406" \
  $STRIP logo.png

rm -f logo-base.png logo-grad.png ring-mask.png ring.png bar-mask.png bar.png glow.png

# ------------------------------------------------------- 3. SOCIAL PREVIEW
# 1280x640 Open Graph card (GitHub repo social preview).
convert "$BG" -resize 1280x640^ -gravity center -crop 1280x640+0+0 +repage \
  -strip social-base.png
convert -size 1280x640 gradient:white-black -alpha off social-mask.png
convert -size 1280x640 xc:"#0b1220" social-mask.png -alpha off \
  -compose CopyOpacity -composite social-scrim.png
convert social-base.png social-scrim.png -compose over -composite \
  -fill "#0e1729" -stroke "#2a3f5f" -strokewidth 2 \
  -draw "roundrectangle 82,438 812,486 20,20" \
  -stroke none \
  -font "$FONT_B" -fill "$WHITE" -pointsize 96 -kerning 1 -annotate +84+300 "urduofdani" \
  -font "$FONT_B" -fill "$MUTED" -pointsize 21 -kerning 5 -annotate +86+368 "MODERN HIGH-SPEED URDU TEXT ENGINE" \
  -font "$FONT_R" -fill "#8fa6c0" -pointsize 21 -kerning 2 -annotate +86+414 "25,320 words  |  73.0 KB .gz  |  ~2.9 ms load  |  stdlib only" \
  -font "$FONT_B" -fill "$TEAL" -pointsize 19 -kerning 3 -annotate +104+468 "SINGLE-SPACE TOKENIZATION  x  GZIP LEVEL 9" \
  $STRIP social-preview.png
rm -f social-base.png social-scrim.png social-mask.png

echo "built:"
identify -format "  %f  %wx%h  %b\n" banner.png banner.jpg logo.png social-preview.png
