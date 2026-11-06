#!/usr/bin/env bash
# Rerun notebook 06, check it, and copy its outputs into the website repo's working tree.
# Commits nothing. Stops before touching the website if a check fails.
#
#   conda activate spirometry
#   bash scripts/site_publish.sh [website repo]      # default below
#   RUN_NOTEBOOK=0 bash scripts/site_publish.sh ...  # reuse figures/site/ as it stands
set -euo pipefail
cd "$(dirname "$0")/.."
SITE="${1:-$HOME/Dropbox/github_website/pmacias.github.io}"
NB=notebooks/06_site_figures.ipynb
[ -f "$SITE/index.html" ] || { echo "no index.html in $SITE" >&2; exit 1; }

if [ "${RUN_NOTEBOOK:-1}" = 1 ]; then
    jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 "$NB"
    n=$(grep -c "/Users/" "$NB" || true)
    [ "$n" = 0 ] || { echo "$NB: $n lines hold /Users/" >&2; exit 1; }
    echo "/Users/ lines in $NB: 0"
fi

python - "$SITE" <<'PY'
import json, re, sys, pathlib
from spirometry.site_figures import PLACEBO_FACTORS_H3 as F
ps = json.load(open("figures/site/spirometry_cards.json"))["patch_summary"]
got = {k: (v["n_clear"], v["n"]) for k, v in ps.items()}
assert got == {"first": (13, 26), "second": (2, 17)}, got
html = pathlib.Path(sys.argv[1], "index.html").read_text(encoding="utf-8")
m = re.search(r"const CAL = \{ first: ([\d.]+), second: ([\d.]+) \}", html)
assert m, "CAL not found in index.html"
assert (float(m[1]), float(m[2])) == (F["first"], F["second"]), (m.groups(), F)
print("patch_summary:", got, "| CAL matches", F)
PY

cp figures/site/spirometry_parry.png "$SITE/figures/spirometry_parry.png"
cp figures/site/spirometry_patch1.png "$SITE/figures/spirometry_patch1.png"
cp figures/site/spirometry_cards.json "$SITE/figures/spirometry_cards.json"
js="$SITE/figures/spirometry_cards.js"
header=$(head -n 2 "$js")
printf '%s\nwindow.SPIROMETRY_CARDS = %s;\n' "$header" "$(cat figures/site/spirometry_cards.json)" > "$js"
echo "copied into $SITE/figures: spirometry_parry.png, spirometry_patch1.png, spirometry_cards.json, spirometry_cards.js"
