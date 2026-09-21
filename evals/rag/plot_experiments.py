"""Charts for comparing RAGAS experiments, built from results_<name>.json
snapshots (snapshot results.json under an experiment's name after each run).

Writes two files next to the snapshots:
  experiments.html  interactive: metric trends, per-case before/after
                    scatter (hover for the question), per-category bars
  experiments.svg   static trend chart, embedded in the README

Usage:
    python -m evals.rag.plot_experiments                 # every results_*.json, oldest first
    python -m evals.rag.plot_experiments a.json b.json   # explicit order
"""

import json
import sys
from pathlib import Path

_DIR = Path(__file__).parent
_METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
_COLORS = ["#4e79a7", "#f28e2b", "#59a14f", "#e15759"]


def _load(paths: list[Path]) -> list[dict]:
    return [
        {"name": path.stem.removeprefix("results_"), **json.loads(path.read_text(encoding="utf-8"))}
        for path in paths
    ]


def _write_svg(experiments: list[dict], out: Path) -> None:
    width, height, left, right, top, bottom = 660, 340, 60, 190, 20, 50
    lo, hi = 0.6, 1.0
    plot_w, plot_h = width - left - right, height - top - bottom
    xs = [left + plot_w * i / max(len(experiments) - 1, 1) for i in range(len(experiments))]

    def y_of(value: float) -> float:
        return top + plot_h * (1 - (value - lo) / (hi - lo))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        'font-family="sans-serif" font-size="12">',
        f'<rect width="{width}" height="{height}" fill="white"/>',
    ]
    for tick in (0.6, 0.7, 0.8, 0.9, 1.0):
        y = y_of(tick)
        parts.append(f'<line x1="{left}" x2="{left + plot_w}" y1="{y}" y2="{y}" stroke="#ddd"/>')
        parts.append(f'<text x="{left - 8}" y="{y + 4}" text-anchor="end">{tick:.1f}</text>')
    for x, exp in zip(xs, experiments):
        parts.append(f'<text x="{x}" y="{height - 22}" text-anchor="middle">{exp["name"]}</text>')
    for i, (metric, color) in enumerate(zip(_METRICS, _COLORS)):
        points = [(x, exp["aggregate"].get(metric)) for x, exp in zip(xs, experiments)]
        points = [(x, y_of(v), v) for x, v in points if v is not None]
        path = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in points)
        parts.append(f'<polyline points="{path}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        for x, y, v in points:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}"/>')
        ly = top + 20 + i * 22
        parts.append(f'<rect x="{left + plot_w + 24}" y="{ly - 10}" width="12" height="12" fill="{color}"/>')
        latest = points[-1][2] if points else 0.0
        parts.append(f'<text x="{left + plot_w + 44}" y="{ly}">{metric} {latest:.2f}</text>')
    parts.append("</svg>")
    out.write_text("\n".join(parts), encoding="utf-8")


_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>RAGAS experiments</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
body{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem}
.card{margin:2rem 0}canvas{max-height:420px}select{margin-right:1rem}
</style></head><body>
<h1>RAGAS experiments</h1>
<div class="card"><h2>Metric trends</h2><canvas id="trend"></canvas></div>
<div class="card"><h2>Per-case before / after</h2>
<p>Above the diagonal = improved. Hover a point for the question.</p>
<select id="metric"></select> before <select id="before"></select> after <select id="after"></select>
<canvas id="scatter"></canvas></div>
<div class="card"><h2>By category</h2><select id="catmetric"></select><canvas id="cat"></canvas></div>
<script>
const DATA = __DATA__;
const METRICS = __METRICS__, COLORS = __COLORS__;
const names = DATA.map(e => e.name);
const mean = a => a.reduce((s, v) => s + v, 0) / a.length;

new Chart("trend", {type: "line", data: {labels: names, datasets: METRICS.map((m, i) => ({
  label: m, data: DATA.map(e => e.aggregate[m] ?? null), borderColor: COLORS[i], backgroundColor: COLORS[i], tension: 0}))},
  options: {scales: {y: {min: 0.6, max: 1}}}});

function fill(id, items, selected) {
  const el = document.getElementById(id);
  items.forEach(v => el.add(new Option(v, v)));
  el.value = selected;
}
fill("metric", METRICS, "context_recall");
fill("before", names, names[Math.max(names.length - 2, 0)]);
fill("after", names, names[names.length - 1]);
fill("catmetric", METRICS, "context_recall");

const scatter = new Chart("scatter", {type: "scatter", data: {datasets: []}, options: {
  scales: {x: {min: 0, max: 1, title: {display: true, text: "before"}}, y: {min: 0, max: 1, title: {display: true, text: "after"}}},
  plugins: {tooltip: {callbacks: {label: c => c.raw.id + ": " + c.raw.x.toFixed(2) + " -> " + c.raw.y.toFixed(2) + " " + c.raw.q}}}}});
function drawScatter() {
  const metric = document.getElementById("metric").value;
  const before = DATA.find(e => e.name === document.getElementById("before").value);
  const after = DATA.find(e => e.name === document.getElementById("after").value);
  const prior = Object.fromEntries(before.rows.map(r => [r.custom_id, r]));
  const pts = after.rows.filter(r => prior[r.custom_id] && r[metric] != null && prior[r.custom_id][metric] != null)
    .map(r => ({x: prior[r.custom_id][metric], y: r[metric], id: r.custom_id, q: r.user_input}));
  const color = p => p.y > p.x + 0.05 ? "#59a14f" : p.y < p.x - 0.05 ? "#e15759" : "#999";
  scatter.data.datasets = [
    {label: "cases", data: pts, pointBackgroundColor: pts.map(color), pointRadius: 5},
    {label: "no change", data: [{x: 0, y: 0}, {x: 1, y: 1}], type: "line", borderColor: "#bbb", borderDash: [4, 4], pointRadius: 0}];
  scatter.update();
}
["metric", "before", "after"].forEach(id => document.getElementById(id).onchange = drawScatter);
drawScatter();

const cats = [...new Set(DATA.flatMap(e => e.rows.map(r => r.category)))].sort();
const catChart = new Chart("cat", {type: "bar", data: {labels: cats, datasets: []}, options: {scales: {y: {min: 0, max: 1}}}});
function drawCat() {
  const metric = document.getElementById("catmetric").value;
  catChart.data.datasets = DATA.map((e, i) => ({label: e.name, backgroundColor: COLORS[i % COLORS.length],
    data: cats.map(c => { const v = e.rows.filter(r => r.category === c && r[metric] != null).map(r => r[metric]); return v.length ? mean(v) : null; })}));
  catChart.update();
}
document.getElementById("catmetric").onchange = drawCat;
drawCat();
</script></body></html>
"""


def _write_html(experiments: list[dict], out: Path) -> None:
    keep = ["custom_id", "category", "user_input", *_METRICS]
    data = [
        {
            "name": exp["name"],
            "aggregate": exp["aggregate"],
            "rows": [{k: row.get(k) for k in keep} for row in exp["rows"]],
        }
        for exp in experiments
    ]
    html = (
        _HTML.replace("__DATA__", json.dumps(data).replace("</", "<\\/"))
        .replace("__METRICS__", json.dumps(_METRICS))
        .replace("__COLORS__", json.dumps(_COLORS))
    )
    out.write_text(html, encoding="utf-8")


def main() -> None:
    if len(sys.argv) > 1:
        paths = [Path(arg) for arg in sys.argv[1:]]
    else:
        paths = sorted(_DIR.glob("results_*.json"), key=lambda p: p.stat().st_mtime)
    experiments = _load(paths)
    _write_svg(experiments, _DIR / "experiments.svg")
    _write_html(experiments, _DIR / "experiments.html")
    print(f"Charted {len(experiments)} experiments: {[e['name'] for e in experiments]}")


if __name__ == "__main__":
    main()
