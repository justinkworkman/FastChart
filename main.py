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

    if chart.type == "pie":
        total = sum(values)
        pie_html = ""
        for label, value in zip(labels, values):
            percentage = (value / total) * 100
            pie_html += f"""
            <div style="width: {percentage}%; background-color: #4CAF50; color: white; text-align: center; padding: 8px;">
                {label}: {value} ({percentage:.2f}%)
            </div>
            """
        return f"""
        <div style="margin-bottom: 20px;">
            <div class="chart-title">{chart.title or ''}</div>
            {pie_html}
        </div>
        """

    elif chart.type in ["bar", "column", "line"]:
        max_value = max(values)
        bar_html = ""
        for label, value in zip(labels, values):
            bar_width = (value / max_value) * 100
            bar_html += f"""
            <div style="margin-bottom: 10px;">
                <div style="background-color: #4CAF50; width: {bar_width}%; height: 30px; color: white; text-align: center; line-height: 30px;">
                    {label}: {value}
                </div>
            </div>
            """
        return f"""
        <div style="margin-bottom: 20px;">
            <div class="chart-title">{chart.title or ''}</div>
            {bar_html}
        </div>
        """
    return ""

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
