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
    value_field: Optional[str] = None
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
        "body { font-family: Arial, sans-serif; padding: 20px; background: #f9f9f9; }",
        "h1 { font-size: 28px; margin-bottom: 30px; }",
        "h2 { font-size: 22px; margin-top: 40px; margin-bottom: 10px; }",
        ".chart { background: white; border-radius: 8px; padding: 20px; margin-bottom: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }",
        ".bar-container, .column-container { margin-top: 10px; }",
        ".bar, .column { height: 30px; margin: 5px 0; background: #eee; position: relative; }",
        ".bar div, .column div { height: 100%; text-align: right; padding-right: 8px; color: white; font-weight: bold; border-radius: 4px; display: flex; align-items: center; justify-content: flex-end; }",
        ".line-point { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 5px; }",
        "</style></head><body>",
        "<h1>Generated Report</h1>"
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
        for idx, (k, v) in enumerate(agg.items()):
            percent = (v / total) * 100 if total else 0
            color = colors[idx % len(colors)]
            html.append(f'<div style="margin:5px 0;">')
            html.append(f'<div style="width:{percent}%; background:{color}; color:white; padding:5px; border-radius:4px;">{k} ({percent:.1f}%)</div>')
            html.append(f'</div>')

    elif chart_type in {"bar", "column"}:
        max_value = max(agg.values(), default=1)
        container_class = "bar-container" if chart_type == "bar" else "column-container"
        html.append(f'<div class="{container_class}">')
        for idx, (k, v) in enumerate(agg.items()):
            width_percent = (v / max_value) * 100
            color = colors[idx % len(colors)]
            html.append(f'<div class="{chart_type}"><div style="width:{width_percent}%;background:{color};">{k} ({v:.1f})</div></div>')
        html.append('</div>')

    elif chart_type == "line":
        max_value = max(agg.values(), default=1)
        keys = list(agg.keys())
        values = list(agg.values())
        html.append('<div style="margin-top:10px;">')
        for idx, (k, v) in enumerate(zip(keys, values)):
            color = colors[idx % len(colors)]
            size = int((v / max_value) * 20) + 5  # scale dot size
            html.append(f'<div style="display:flex;align-items:center;margin:4px 0;"><div class="line-point" style="background:{color};width:{size}px;height:{size}px;"></div><span style="margin-left:5px;">{k} ({v:.1f})</span></div>')
        html.append('</div>')

    html.append('</div>')
    return "".join(html)
