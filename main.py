from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from collections import defaultdict
import statistics
import os

app = FastAPI()

class ChartDefinition(BaseModel):
    title: Optional[str] = None
    type: str  # pie, bar, column, line
    calculation: str  # sum, count, average, min, max
    field: str
    label_field: Optional[str] = None
    color_field: Optional[str] = None

class LayoutDefinition(BaseModel):
    columns: int
    charts: List[ChartDefinition]

class ReportRequest(BaseModel):
    data: List[dict]
    layout: LayoutDefinition

def aggregate_data(data: List[dict], chart: ChartDefinition):
    groups = defaultdict(list)
    for item in data:
        key = item.get(chart.label_field) if chart.label_field else "All"
        value = item.get(chart.field)
        if value is not None:
            groups[key].append(value)

    result = {}
    for key, values in groups.items():
        if chart.calculation == "sum":
            result[key] = sum(values)
        elif chart.calculation == "count":
            result[key] = len(values)
        elif chart.calculation == "average":
            result[key] = statistics.mean(values)
        elif chart.calculation == "min":
            result[key] = min(values)
        elif chart.calculation == "max":
            result[key] = max(values)
        else:
            result[key] = 0
    return result

def generate_chart_html(chart: ChartDefinition, aggregated_data: dict):
    labels = list(aggregated_data.keys())
    values = list(aggregated_data.values())

    # Create simple table chart for email safety
    table_rows = ""
    for label, value in zip(labels, values):
        table_rows += f"""
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd;">{label}</td>
            <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{value}</td>
        </tr>
        """

    return f"""
    <div style="margin-bottom: 20px;">
        <div class="chart-title">{chart.title or ''}</div>
        <table style="width:100%; border-collapse: collapse;">
            <thead>
                <tr>
                    <th style="padding: 8px; border: 1px solid #ddd; background: #f0f0f0;">{chart.label_field or "Label"}</th>
                    <th style="padding: 8px; border: 1px solid #ddd; background: #f0f0f0;">{chart.calculation.title()} of {chart.field}</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
    """

@app.post("/render", response_class=HTMLResponse)
async def render_report(request: ReportRequest):
    data = request.data
    layout = request.layout

    html_charts = []
    for chart_def in layout.charts:
        aggregated = aggregate_data(data, chart_def)
        chart_html = generate_chart_html(chart_def, aggregated)
        html_charts.append(chart_html)

    # Build the full table layout
    rows_html = ""
    for i in range(0, len(html_charts), layout.columns):
        row_charts = html_charts[i:i + layout.columns]
        row_html = "<tr>"
        for chart_html in row_charts:
            row_html += f"<td style='padding: 10px; vertical-align: top;'>{chart_html}</td>"
        # Pad with empty cells if needed
        if len(row_charts) < layout.columns:
            for _ in range(layout.columns - len(row_charts)):
                row_html += "<td></td>"
        row_html += "</tr>"
        rows_html += row_html

    full_html = f"""
    <html>
    <head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background: #f4f6f8;
            padding: 20px;
        }}
        table.layout {{
            width: 100%;
            border-collapse: collapse;
        }}
        table.layout td {{
            background: white;
            border: 1px solid #ddd;
            padding: 20px;
            vertical-align: top;
        }}
        .chart-title {{
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
            text-align: center;
        }}
    </style>
    </head>
    <body>
        <table class="layout">
            {rows_html}
        </table>
    </body>
    </html>
    """

    return HTMLResponse(content=full_html)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
