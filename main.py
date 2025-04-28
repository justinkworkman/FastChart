from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from collections import Counter
import math

app = FastAPI()

class ChartConfig(BaseModel):
    type: str  # "pie" or "bar"
    calculation: str  # "count", "average", etc (only "count" supported now)
    field: str  # field to aggregate on

class LayoutConfig(BaseModel):
    rows: int
    columns: int
    charts: List[ChartConfig]

class ReportRequest(BaseModel):
    data: List[Dict[str, Any]]
    layout: LayoutConfig

@app.post("/generate-report", response_class=HTMLResponse)
async def generate_report(request: ReportRequest):
    data = request.data
    layout = request.layout

    charts_html = []

    for chart in layout.charts:
        aggregation = aggregate_data(data, chart.calculation, chart.field)

        if chart.type == "pie":
            svg = generate_pie_chart(aggregation)
        elif chart.type == "bar":
            svg = generate_bar_chart(aggregation)
        else:
            svg = f"<div>Unsupported chart type: {chart.type}</div>"

        charts_html.append(svg)

    html = build_html_page(charts_html, layout.rows, layout.columns)
    return HTMLResponse(content=html)

def aggregate_data(data, calculation, field):
    if calculation == "count":
        values = [item.get(field, "Unknown") for item in data]
        counter = Counter(values)
        return dict(counter)
    else:
        return {}  # Extend here for average, sum, etc.

def generate_pie_chart(aggregation):
    total = sum(aggregation.values())
    angles = []
    for value in aggregation.values():
        angles.append((value / total) * 360)

    svg_parts = []
    start_angle = 0
    radius = 100
    cx, cy = 120, 120
    colors = ["#4F46E5", "#06B6D4", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"]

    for idx, (label, count) in enumerate(aggregation.items()):
        end_angle = start_angle + (count / total) * 360
        x1 = cx + radius * math.cos(math.radians(start_angle))
        y1 = cy + radius * math.sin(math.radians(start_angle))
        x2 = cx + radius * math.cos(math.radians(end_angle))
        y2 = cy + radius * math.sin(math.radians(end_angle))
        large_arc = 1 if end_angle - start_angle > 180 else 0
        color = colors[idx % len(colors)]

        path = f'''
        <path d="M{cx},{cy} L{x1},{y1} A{radius},{radius} 0 {large_arc},1 {x2},{y2} Z" fill="{color}" />
        '''
        svg_parts.append(path)
        start_angle = end_angle

    svg = f'''
    <svg viewBox="0 0 240 240" width="240" height="240">
        {''.join(svg_parts)}
    </svg>
    '''
    return svg

def generate_bar_chart(aggregation):
    max_value = max(aggregation.values())
    bar_width = 40
    bar_gap = 20
    svg_width = (bar_width + bar_gap) * len(aggregation)
    svg_height = 200
    colors = ["#4F46E5", "#06B6D4", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"]

    svg_parts = []
    for idx, (label, count) in enumerate(aggregation.items()):
        height = (count / max_value) * svg_height
        x = idx * (bar_width + bar_gap)
        y = svg_height - height
        color = colors[idx % len(colors)]
        svg_parts.append(f'''
            <rect x="{x}" y="{y}" width="{bar_width}" height="{height}" fill="{color}" />
            <text x="{x + bar_width / 2}" y="{svg_height + 15}" font-size="12" text-anchor="middle">{label}</text>
        ''')

    svg = f'''
    <svg viewBox="0 0 {svg_width} {svg_height + 30}" width="{svg_width}" height="{svg_height + 30}">
        {''.join(svg_parts)}
    </svg>
    '''
    return svg

def build_html_page(charts_html, rows, columns):
    embedded_css = """
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f9fafb; margin: 0; padding: 2rem; }
        .grid { display: grid; gap: 2rem; }
        .card { background: white; border-radius: 12px; padding: 1.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        svg { display: block; margin: 0 auto; }
    </style>
    """

    grid_style = f"grid-template-columns: repeat({columns}, 1fr);"

    html = f'''
    <html>
    <head>
        <meta charset="UTF-8">
        {embedded_css}
    </head>
    <body>
        <div class="grid" style="{grid_style}">
            {''.join(f'<div class="card">{chart}</div>' for chart in charts_html)}
        </div>
    </body>
    </html>
    '''
    return html
