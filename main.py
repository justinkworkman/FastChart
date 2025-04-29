from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional, Literal, Dict, Any
import math
import statistics
import os
import uvicorn

app = FastAPI()

# ─── Models ────────────────────────────────────────────────────────────────

class ChartDefinition(BaseModel):
    title: Optional[str] = ""
    type: Literal["pie", "bar", "column", "line"]
    calculation: Literal["count", "sum", "average", "min", "max"]
    field: str                  # field to calculate on (or count)
    label_field: Optional[str]  # field to group by
    colors: Optional[List[str]] = None  # optional custom palette

class LayoutDefinition(BaseModel):
    columns: int
    charts: List[ChartDefinition]

class ReportRequest(BaseModel):
    data: List[Dict[str, Any]]
    layout: LayoutDefinition

# ─── Aggregation ─────────────────────────────────────────────────────────

def aggregate(data, chart: ChartDefinition) -> Dict[str, float]:
    buckets: Dict[str, List[float]] = {}
    for item in data:
        key = item.get(chart.label_field) or "Unknown"
        raw = item.get(chart.field, 0)
        try:
            val = float(raw)
        except:
            val = 0.0
        buckets.setdefault(key, []).append(val)

    result: Dict[str, float] = {}
    for k, vals in buckets.items():
        if chart.calculation == "count":
            result[k] = len(vals)
        elif chart.calculation == "sum":
            result[k] = sum(vals)
        elif chart.calculation == "average":
            result[k] = statistics.mean(vals) if vals else 0
        elif chart.calculation == "min":
            result[k] = min(vals) if vals else 0
        elif chart.calculation == "max":
            result[k] = max(vals) if vals else 0
    return result

# ─── SVG Generators ────────────────────────────────────────────────────────

DEFAULT_COLORS = ["#4CAF50","#FF9800","#2196F3","#F44336","#9C27B0"]

def gen_pie_svg(agg: Dict[str, float], colors: List[str]) -> str:
    total = sum(agg.values()) or 1
    start = 0.0
    parts = []
    idx = 0
    for label, val in agg.items():
        frac = val / total
        end = start + frac
        large = 1 if frac >= .5 else 0
        # coordinates on unit circle scaled to 100×100
        x1 = 100 + 100*math.cos(2*math.pi*start)
        y1 = 100 + 100*math.sin(2*math.pi*start)
        x2 = 100 + 100*math.cos(2*math.pi*end)
        y2 = 100 + 100*math.sin(2*math.pi*end)
        color = colors[idx % len(colors)]
        parts.append(
            f'<path d="M100,100 L{x1:.2f},{y1:.2f} A100,100 0 {large},1 {x2:.2f},{y2:.2f} Z" fill="{color}" stroke="#fff"/>'
        )
        start = end
        idx += 1
    return f'<svg viewBox="0 0 200 200" width="200" height="200">{"".join(parts)}</svg>'

def gen_bar_svg(agg: Dict[str, float], colors: List[str]) -> str:
    maxv = max(agg.values()) or 1
    parts = []
    idx = 0
    y = 0
    for label, val in agg.items():
        w = (val/maxv)*200
        color = colors[idx % len(colors)]
        parts.append(f'<rect x="0" y="{y}" width="{w:.2f}" height="20" fill="{color}"/>')
        parts.append(f'<text x="{w+5:.2f}" y="{y+15}" font-size="12">{label}: {val:.0f}</text>')
        y += 30
        idx += 1
    height = y
    return f'<svg viewBox="0 0 300 {height}" width="300" height="{height}">' + "".join(parts) + '</svg>'

def gen_column_svg(agg: Dict[str, float], colors: List[str]) -> str:
    maxv = max(agg.values()) or 1
    parts = []
    idx = 0
    x = 0
    for label, val in agg.items():
        h = (val/maxv)*150
        color = colors[idx % len(colors)]
        parts.append(f'<rect x="{x}" y="{150-h:.2f}" width="30" height="{h:.2f}" fill="{color}"/>')
        parts.append(f'<text x="{x+15}" y="170" font-size="12" text-anchor="middle">{label}</text>')
        x += 50
        idx += 1
    width = x
    return f'<svg viewBox="0 0 {width} 200" width="{width}" height="200">' + "".join(parts) + '</svg>'

def gen_line_svg(agg: Dict[str, float], colors: List[str]) -> str:
    maxv = max(agg.values()) or 1
    pts = []
    idx = 0
    n = len(agg)
    for label, val in agg.items():
        x = 200 * idx/(n-1 if n>1 else 1)
        y = 150 - (val/maxv)*150
        pts.append((x,y))
        idx += 1

    # lines + circles
    line_parts = []
    for i in range(len(pts)-1):
        x1,y1 = pts[i]; x2,y2 = pts[i+1]
        line_parts.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{colors[0]}" stroke-width="2"/>')
    for x,y in pts:
        line_parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="{colors[0]}"/>')
    # x labels
    text_parts = []
    idx=0
    for label in agg.keys():
        x = 200 * idx/(n-1 if n>1 else 1)
        text_parts.append(f'<text x="{x:.2f}" y="190" font-size="12" text-anchor="middle">{label}</text>')
        idx+=1

    return (
      f'<svg viewBox="0 0 200 200" width="200" height="200">'
      + "".join(line_parts)
      + "".join(text_parts)
      + '</svg>'
    )

# ─── Chart → HTML ──────────────────────────────────────────────────────

def render_chart(chart: ChartDefinition, data: List[Dict[str,Any]]) -> str:
    agg = aggregate(data, chart)
    colors = chart.colors or DEFAULT_COLORS

    if chart.type == "pie":
        svg = gen_pie_svg(agg, colors)
    elif chart.type == "bar":
        svg = gen_bar_svg(agg, colors)
    elif chart.type == "column":
        svg = gen_column_svg(agg, colors)
    elif chart.type == "line":
        svg = gen_line_svg(agg, colors)
    else:
        return "<div>Unsupported chart type</div>"

    return f"""
      <div style="text-align:center; padding:10px;">
        <div style="font-size:18px; font-weight:bold; margin-bottom:8px;">{chart.title}</div>
        {svg}
      </div>
    """

# ─── Endpoint ──────────────────────────────────────────────────────────

@app.post("/render", response_class=HTMLResponse)
async def render_report(req: ReportRequest):
    html_blocks = []
    for chart in req.layout.charts:
        html_blocks.append(render_chart(chart, req.data))

    # build table rows/cols
    rows = []
    for i in range(0, len(html_blocks), req.layout.columns):
        slice_ = html_blocks[i:i+req.layout.columns]
        cells = "".join(f'<td style="vertical-align:top; border:1px solid #eee; padding:10px;">{b}</td>' for b in slice_)
        # pad
        if len(slice_) < req.layout.columns:
            cells += "<td></td>"*(req.layout.columns-len(slice_))
        rows.append(f"<tr>{cells}</tr>")

    table = "<table style='width:100%; border-collapse:collapse;'>"+ "".join(rows) + "</table>"

    html = f"""
    <html><head>
      <style>
        body {{ font-family:Arial,sans-serif; background:#f9f9f9; padding:20px; }}
        table {{ background:white; }}
      </style>
    </head><body>
      {table}
    </body></html>
    """
    return HTMLResponse(content=html)

if __name__=="__main__":
    port=int(os.environ.get("PORT",8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
