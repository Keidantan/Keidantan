#!/usr/bin/env python3
"""One-off helper: subset the two pixel fonts and write their text metrics.

Needs fonttools and brotli (pip install fonttools brotli). build.py does not:
it reads the committed results in scripts/fonts/.

Usage: python3 scripts/subset_fonts.py <jersey-10-latin-400.woff2> <vt323-latin-400.woff2>
(the files ship in the npm packages @fontsource/jersey-10 and @fontsource/vt323)
"""
import json
import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

OUT = Path(__file__).parent / "fonts"
# printable ASCII plus the middle dot
CHARS = [chr(c) for c in range(0x20, 0x7F)] + ["·"]


def main(jersey: str, vt323: str) -> None:
    metrics = {}
    for name, src in (("jersey10", jersey), ("vt323", vt323)):
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.layout_features = ["kern"]
        opts.name_IDs = [0, 1, 2, 3, 4, 6, 13, 14]
        opts.notdef_outline = True
        font = TTFont(src)
        sub = subset.Subsetter(opts)
        sub.populate(text="".join(CHARS))
        sub.subset(font)
        font.flavor = "woff2"
        font.save(OUT / f"{name}.woff2")
        f2 = TTFont(OUT / f"{name}.woff2")
        cmap = f2.getBestCmap()
        hmtx = f2["hmtx"]
        metrics[name] = {
            "upem": f2["head"].unitsPerEm,
            "adv": {c: hmtx[cmap[ord(c)]][0] for c in CHARS if ord(c) in cmap},
        }
    (OUT / "metrics.json").write_text(json.dumps(metrics, sort_keys=True, indent=1) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:3])
