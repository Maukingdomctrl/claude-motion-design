"""Write one placeholder shots/Gx.js per build group (G1-G4, the files index.html loads) and shots/groups.json.
usage: remake_stub.py [b1 b2 b3]  -> groups [0,b1) [b1,b2) [b2,b3) [b3,n), boundaries taken from SPEC.md.
Without boundaries the film is split into 4 equal parts, each boundary snapped to the nearest cut in ref/cuts.json."""
import json, sys
from remake_common import H, meta

m = meta(); n = m["n"]
if not n: sys.exit("run remake_analyze.py first (ref/cuts.json has no frame count)")
if len(sys.argv) > 1:
    inner = [int(x) for x in sys.argv[1:]]
    if len(inner) != 3: sys.exit("give exactly 3 boundaries (4 groups, matching index.html)")
else:
    inner = [min(m["cuts"], key=lambda c: abs(c - n * k / 4)) if m["cuts"] else round(n * k / 4) for k in (1, 2, 3)]
edges = [0, *inner, n]
if edges != sorted(set(edges)): sys.exit(f"boundaries must be increasing and inside 0-{n}: {edges}")
groups = {f"G{i + 1}": [edges[i], edges[i + 1]] for i in range(4)}
(H / "shots").mkdir(exist_ok=True)
(H / "shots/groups.json").write_text(json.dumps(groups) + "\n")
print("groups", groups)
for g, (a, b) in groups.items():
    p = H / f"shots/{g}.js"
    if not p.exists():
        p.write_text(f"""(function () {{
  const C = CORE;
  // {g}: frames {a}-{b}. Replace this placeholder with real shots (SHOT per shot id).
  SHOT({{ id: '{g}_placeholder', f0: {a}, f1: {b}, render: (lf, F) =>
    `<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font:48px Geist;color:#94a3b8">{g} · F${{F}}</div>` }});
}})();
""")
        print("stub", g)
