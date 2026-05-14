"""Aggregate results/*.jsonl into REPORT.html (and REPORT.md)."""
from __future__ import annotations

import json
import math
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results"
HTML_OUT = RESULTS_DIR / "REPORT.html"
MD_OUT = RESULTS_DIR / "REPORT.md"


def _load_runs() -> list[dict]:
    runs = []
    for path in sorted(RESULTS_DIR.glob("*.jsonl")):
        with open(path) as fh:
            first = fh.readline().strip()
            if not first:
                continue
            summary = json.loads(first)
            if not summary.get("_summary"):
                continue
            rows = [json.loads(l) for l in fh if l.strip()]
            runs.append({"summary": summary, "rows": rows, "path": path.name})
    return runs


def _fmt(v, kind="num"):
    if v is None:
        return "—"
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return "—"
    if kind == "pct":
        return f"{v * 100:.2f}%"
    if kind == "rtf":
        return f"{v:.3f}"
    if kind == "ms":
        return f"{v * 1000:.0f} ms"
    if kind == "mb":
        return f"{v:.0f}"
    if kind == "s":
        return f"{v:.2f} s"
    return f"{v}"


def _verdict(rtf_median: float) -> tuple[str, str]:
    if rtf_median != rtf_median:
        return ("error", "no data")
    if rtf_median < 0.3:
        return ("ok", "realtime + headroom")
    if rtf_median < 0.7:
        return ("warn", "realtime, low headroom")
    if rtf_median < 1.0:
        return ("warn", "borderline")
    return ("bad", "slower than realtime")


def _render_html(runs: list[dict]) -> str:
    rows_main = []
    for run in runs:
        s = run["summary"]
        if s.get("failed"):
            rows_main.append(
                f"<tr class='failed'><td>{s['engine']}</td><td>{s['model']}</td>"
                f"<td colspan='8'><b>FAILED</b> ({s.get('phase','?')}): "
                f"<code>{s.get('error','')[:200]}</code></td></tr>"
            )
            continue
        cls, label = _verdict(s["rtf_median"])
        pct = s.get("rtf_percentiles") or {}
        rows_main.append(
            "<tr class='{cls}'>"
            "<td>{engine}</td><td>{model}</td>"
            "<td class='num'>{wer}</td>"
            "<td class='num'>{rtf_med}</td>"
            "<td class='num'>{rtf_p95}</td>"
            "<td class='num'>{rtf_p99}</td>"
            "<td class='num'>{cold}</td>"
            "<td class='num'>{rss}</td>"
            "<td class='num'>{n}</td>"
            "<td class='label'>{label}</td>"
            "</tr>".format(
                cls=cls,
                engine=s["engine"],
                model=s["model"],
                wer=_fmt(s["wer"], "pct"),
                rtf_med=_fmt(s["rtf_median"], "rtf"),
                rtf_p95=_fmt(pct.get("p95"), "rtf"),
                rtf_p99=_fmt(pct.get("p99"), "rtf"),
                cold=_fmt(s["cold_start_s"], "s"),
                rss=_fmt(s["peak_rss_mb"], "mb"),
                n=s.get("n_utterances", "—"),
                label=label,
            )
        )

    host_block = ""
    if runs:
        first_ok = next((r["summary"] for r in runs if not r["summary"].get("failed")), None)
        if first_ok:
            h = first_ok["host"]
            host_block = (
                f"<p class='host'>VM: <b>{h['hostname']}</b> · {h['platform']} · "
                f"{h['cpu_count_physical']} cores ({h['cpu_count']} logical) · "
                f"{h['ram_gb']} GB RAM · python {h['python']}</p>"
            )
            host_block += (
                f"<p class='host'>Corpus: {first_ok.get('n_utterances','?')} utterances "
                f"({first_ok.get('total_audio_s', 0):.1f}s total) · "
                f"repeats per utterance: {first_ok.get('repeats_per_utterance', 1)} · "
                f"timestamp: {first_ok.get('timestamp','?')}</p>"
            )

    per_utt_blocks = []
    for run in runs:
        s = run["summary"]
        if s.get("failed"):
            continue
        body = "\n".join(
            "<tr><td>{id}</td><td class='num'>{dur}</td>"
            "<td class='num'>{ct}</td><td class='num'>{rtf}</td>"
            "<td><span class='ref'>{ref}</span><br><span class='hyp'>{hyp}</span></td></tr>".format(
                id=row["id"],
                dur=_fmt(row["duration_s"], "s"),
                ct=_fmt(row["compute_time_s"], "s"),
                rtf=_fmt(row["rtf"], "rtf"),
                ref=_html_escape(row["reference"]),
                hyp=_html_escape(row["hypothesis"]),
            )
            for row in run["rows"]
        )
        per_utt_blocks.append(
            f"<details><summary>{s['engine']} / {s['model']} — {len(run['rows'])} utterances</summary>"
            f"<table class='per-utt'><thead><tr><th>id</th><th>dur</th><th>compute</th><th>RTF</th>"
            f"<th>reference / hypothesis</th></tr></thead><tbody>{body}</tbody></table></details>"
        )

    return f"""<!doctype html>
<html lang=en>
<head>
<meta charset=utf-8>
<title>STT bake-off on exe.dev</title>
<style>
body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 1100px; margin: 2em auto; padding: 0 1em; color: #222; }}
h1 {{ margin-bottom: 0.2em; }}
h2 {{ margin-top: 2em; border-bottom: 1px solid #ddd; padding-bottom: 0.3em; }}
.host {{ color: #555; font-size: 0.9em; margin: 0.2em 0; }}
table {{ border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 0.93em; }}
th, td {{ padding: 0.45em 0.7em; border-bottom: 1px solid #eee; text-align: left; vertical-align: top; }}
th {{ background: #f5f5f5; }}
td.num {{ font-variant-numeric: tabular-nums; text-align: right; }}
td.label {{ font-size: 0.85em; }}
tr.ok {{ background: #eaf7ea; }}
tr.warn {{ background: #fff7e0; }}
tr.bad {{ background: #fde0e0; }}
tr.failed {{ background: #f0f0f0; color: #777; }}
code {{ background: #f0f0f0; padding: 0.1em 0.3em; border-radius: 3px; }}
details {{ margin: 0.5em 0; }}
summary {{ cursor: pointer; padding: 0.4em 0; font-weight: 500; }}
.ref {{ color: #444; }}
.hyp {{ color: #06c; }}
.legend {{ font-size: 0.85em; color: #555; margin-top: 0.5em; }}
.legend span {{ display: inline-block; padding: 0.1em 0.5em; margin-right: 0.5em; border-radius: 3px; }}
.legend .ok {{ background: #eaf7ea; }}
.legend .warn {{ background: #fff7e0; }}
.legend .bad {{ background: #fde0e0; }}
</style>
</head>
<body>
<h1>STT bake-off on exe.dev</h1>
<p class='host'>CPU-only STT engines on a single VM, offline mode (whole-file transcription).</p>
{host_block}

<h2>Summary</h2>
<table>
<thead><tr>
<th>Engine</th><th>Model</th><th>WER</th>
<th>RTF (med)</th><th>RTF P95</th><th>RTF P99</th>
<th>Cold start</th><th>Peak RSS (MB)</th><th>N</th><th>Verdict</th>
</tr></thead>
<tbody>
{''.join(rows_main)}
</tbody>
</table>
<p class='legend'>
<span class='ok'>RTF &lt; 0.3</span> realtime + headroom
<span class='warn'>RTF 0.3–1.0</span> borderline
<span class='bad'>RTF ≥ 1.0</span> slower than realtime
</p>

<h2>Per-utterance detail</h2>
{''.join(per_utt_blocks) or '<p>No successful runs.</p>'}

</body>
</html>
"""


def _html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _render_markdown(runs: list[dict]) -> str:
    lines = ["# STT bake-off on exe.dev", ""]
    first_ok = next((r["summary"] for r in runs if not r["summary"].get("failed")), None)
    if first_ok:
        h = first_ok["host"]
        lines.append(
            f"- VM `{h['hostname']}` · {h['cpu_count_physical']} cores ({h['cpu_count']} logical) · {h['ram_gb']} GB RAM"
        )
        lines.append(
            f"- Corpus: {first_ok.get('n_utterances','?')} utterances ({first_ok.get('total_audio_s',0):.1f}s total)"
        )
        lines.append(f"- Repeats per utterance: {first_ok.get('repeats_per_utterance', 1)}")
        lines.append(f"- Timestamp: {first_ok.get('timestamp','?')}")
        lines.append("")
    lines.append("| Engine | Model | WER | RTF med | RTF P95 | Cold start | Peak RSS | Verdict |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---|")
    for run in runs:
        s = run["summary"]
        if s.get("failed"):
            lines.append(f"| {s['engine']} | {s['model']} | — | — | — | — | — | FAILED ({s.get('phase','?')}) |")
            continue
        _, label = _verdict(s["rtf_median"])
        pct = s.get("rtf_percentiles") or {}
        lines.append(
            f"| {s['engine']} | {s['model']} | "
            f"{_fmt(s['wer'],'pct')} | {_fmt(s['rtf_median'],'rtf')} | "
            f"{_fmt(pct.get('p95'),'rtf')} | {_fmt(s['cold_start_s'],'s')} | "
            f"{_fmt(s['peak_rss_mb'],'mb')} MB | {label} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    runs = _load_runs()
    if not runs:
        raise SystemExit(f"no results in {RESULTS_DIR} — run benchmark.harness first")
    HTML_OUT.write_text(_render_html(runs))
    MD_OUT.write_text(_render_markdown(runs))
    print(f"wrote {HTML_OUT}")
    print(f"wrote {MD_OUT}")


if __name__ == "__main__":
    main()
