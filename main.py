# main.py

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
import statistics

app = FastAPI()

class LabelsConfig(BaseModel):
    titleFontSize: Optional[str] = "20px"
    labelFontSize: Optional[str] = "14px"
    colors: Optional[List[str]] = Field(default_factory=lambda: [
        "#4CAF50", "#FF9800", "#2196F3", "#F44336", "#9C27B0"
    ])

class ChartDefinition(BaseModel):
    type: Literal["pie", "bar", "column", "line"]
    title: Optional[str] = ""
    calculation: Literal["count", "sum", "average", "min", "max"] = "count"
    field: str
    value_field: Optional[str] = None  # For sum, avg, min, max
    labels: Optional[LabelsConfig] = LabelsConfig()

class LayoutConfig(BaseModel):
    charts: List[ChartDefinition]

class ReportRequest(BaseModel):
    data: List[Dict[str, Any]]
    layout: LayoutConfig

@app.post("/generate", response_class=HTMLResponse)
async def generate_report(request: ReportRequest):
    data = request.data
    layout = request.layout

    html_parts = [
        "<html><head><style>",
        "body { font-family: Arial, sans-serif; padding: 20px; }",
        "h2 { margin-top: 40px; }",
        ".chart { margin-bottom: 40px; }",
        ".bar, .column { background-color: #eee; margin: 5px 0; position: relative; height: 30px; }",
        ".bar div, .column div { height: 100%; text-align: right; padding-right: 5px; color: white; font-weight: bold; }",
        ".line-chart { width: 100%; height: 300px; }",
        ".line { fill: none; stroke-width: 2; }",
        "</style></head><body>",
        "<h1>Report</h1>"
    ]

    for chart_def in layout.charts:
        html_parts.append(render_chart(data, chart_def.model_dump()))

    html_parts.append("</body></html>")
    return "".join(html_parts)

def render_chart(data, chart_def):
    chart_type = chart_def.get("type")
    title = chart_def.get("title", "")
    field = chart_def.get("field")
    calculation = chart_def.get("calculation", "count")
    value_field = chart_def.get("value_field")
    labels_conf = chart_def.get("labels", {})
    colors = labels_conf.get("colors", ["#4CAF50", "#FF9800", "#2196F3", "#F44336", "#9C27B0"])

    # Aggregation
    agg = {}
    for item in data:
        key = item.get(field, "Unknown")
        if calculation == "count":
            agg[key] = agg.get(key, 0) + 1
        else:
            try:
                val = float(item.get(value_field, 0))
            except (TypeError, ValueError):
                val = 0
            if key not in agg:
                agg[key] = []
            agg[key].append(val)

    if calculation in {"sum", "average", "min", "max"}:
        for k in agg:
            if calculation == "sum":
                agg[k] = sum(agg[k])
            elif calculation == "average":
                agg[k] = statistics.mean(agg[k]) if agg[k] else 0
            elif calculation == "min":
                agg[k] = min(agg[k]) if agg[k] else 0
            elif calculation == "max":
                agg[k] = max(agg[k]) if agg[k] else 0

    html = [f'<div class="chart"><h2>{title}</h2>']

    if chart_type == "pie":
        total = sum(agg.values())
        html.append('<svg width="300" height="300" viewBox="0 0 32 32">')
        start_angle = 0
        for idx, (k, v) in enumerate(agg.items()):
            if total == 0:
                continue
            portion = v / total
            end_angle = start_angle + portion * 360
            large_arc = 1 if end_angle - start_angle > 180 else 0
            x1 = 16 + 16 * math.cos(math.radians(start_angle))
            y1 = 16 + 16 * math.sin(math.radians(start_angle))
            x2 = 16 + 16 * math.cos(math.radians(end_angle))
            y2 = 16 + 16 * math.sin(math.radians(end_angle))
            path = f"M16,16 L{x1},{y1} A16,16 0 {large_arc},1 {x2},{y2} z"
            color = colors[idx % len(colors)]
            html.append(f'<path d="{path}" fill="{color}"></path>')
            start_angle = end_angle
        html.append('</svg>')

    elif chart_type in {"bar", "column"}:
        max_value = max(agg.values(), default=1)
        for idx, (k, v) in enumerate(agg.items()):
            width_percent = (v / max_value) * 100
            color = colors[idx % len(colors)]
            html.append(f'<div class="{chart_type}"><div style="width:{width_percent}%;background:{color}">{k} ({v})</div></div>')

    elif chart_type == "line":
        # Simple text-based line chart
        max_value = max(agg.values(), default=1)
        html.append('<svg class="line-chart" viewBox="0 0 100 100">')
        points = []
        keys = list(agg.keys())
        for i, k in enumerate(keys):
            x = (i / (len(keys) - 1)) * 100 if len(keys) > 1 else 50
            y = 100 - (agg[k] / max_value * 100)
            points.append(f"{x},{y}")
        if points:
            color = colors[0 % len(colors)]
            html.append(f'<polyline points="{" ".join(points)}" class="line" stroke="{color}"></polyline>')
        html.append('</svg>')

    html.append('</div>')
    return "".join(html)

import math
