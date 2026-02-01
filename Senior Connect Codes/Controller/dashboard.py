from dash import Dash, html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import os
import time
from excel_lock import excel_lock
import re

# ================= CONFIG =================
FILE_PATH = "/home/admin/seniorconnect_repo/SeniorConnect_MasterLog.xlsx"
AUTO_REFRESH_INTERVAL = 10 * 1000  # 10 seconds

# ================= SAFE EXCEL READ =================
def safe_read_excel(sheet_name):
    for _ in range(5):
        try:
            with excel_lock:
                if os.path.exists(FILE_PATH):
                    return pd.read_excel(FILE_PATH, sheet_name=sheet_name, engine="openpyxl")
        except Exception as e:
            print(f"Warning: Excel read failed: {e}. Retrying...")
            time.sleep(0.2)
    return pd.DataFrame()

# ================= DEFAULT DROPDOWN STYLE =================
dropdown_style_default = {"backgroundColor": "white", "color": "black", "border": "1px solid #ccc"}

# ================= APP INIT =================
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

# ================= APP LAYOUT =================
def serve_layout():
    return html.Div(
        id="page-wrapper",
        children=[
            dbc.Container(
                fluid=True,
                style={"maxWidth": "1200px"},
                children=[

                    dcc.Interval(id="auto-refresh", interval=AUTO_REFRESH_INTERVAL, n_intervals=0),

                    # ===== HEADER =====
                    dbc.Row(
                        [
                            dbc.Col(html.H2("SeniorConnect Master Log Viewer",
                                            id="title-text",
                                            className="my-4 fw-bold"), md=9),
                            dbc.Col(dbc.Switch(id="dark-mode-toggle", label="Dark Mode", value=False,
                                               className="mt-4"), md=3,
                                    style={"textAlign": "right"}),
                        ]
                    ),

                    # ===== KPI ROW =====
                    dbc.Row(
                        [
                            dbc.Col(dbc.Card(dbc.CardBody([
                                html.H6("Total Records", id="kpi-title-total"),
                                html.H3(id="kpi-total", className="fw-bold")
                            ]), id="kpi-card-total"), md=3),

                            dbc.Col(dbc.Card(dbc.CardBody([
                                html.H6("Critical Alerts", id="kpi-title-critical"),
                                html.H3(id="kpi-critical", className="fw-bold")
                            ]), id="kpi-card-critical"), md=3),

                            dbc.Col(dbc.Card(dbc.CardBody([
                                html.H6("Moderate Alerts", id="kpi-title-moderate"),
                                html.H3(id="kpi-moderate", className="fw-bold")
                            ]), id="kpi-card-moderate"), md=3),

                            dbc.Col(dbc.Card(dbc.CardBody([
                                html.H6("Minimal Alerts", id="kpi-title-low"),
                                html.H3(id="kpi-low", className="fw-bold")
                            ]), id="kpi-card-low"), md=3),
                        ],
                        className="mb-4"
                    ),

                    # ===== FILTER PANEL =====
                    dbc.Card(id="filter-card", className="mb-4 shadow-sm", children=[
                        dbc.CardBody(
                            dbc.Row(
                                [
                                    dbc.Col([html.Label("Excel Tab"),
                                             dcc.Dropdown(
                                                 id="sheet-dropdown",
                                                 clearable=False,
                                                 style=dropdown_style_default
                                             )], md=4),

                                    dbc.Col([html.Label("Date"),
                                             dcc.Dropdown(id="date-dropdown", clearable=False,
                                                          style=dropdown_style_default)], md=4),

                                    dbc.Col([html.Label("Location"),
                                             dcc.Dropdown(id="location-dropdown", clearable=False,
                                                          style=dropdown_style_default)], md=4),
                                ],
                                className="g-3"
                            )
                        )
                    ]),

                    # ===== GRAPH =====
                    dbc.Card(id="graph-card", className="shadow-sm", children=[
                        dbc.CardBody(dcc.Graph(id="graph-content", config={"displayModeBar": False}))
                    ])
                ]
            )
        ]
    )

app.layout = serve_layout

# ================= DARK MODE CALLBACK =================
@callback(
    Output("page-wrapper", "style"),
    Output("filter-card", "style"),
    Output("graph-card", "style"),
    Output("title-text", "style"),
    Output("kpi-card-total", "style"),
    Output("kpi-card-critical", "style"),
    Output("kpi-card-moderate", "style"),
    Output("kpi-card-low", "style"),
    Output("sheet-dropdown", "style"),
    Output("date-dropdown", "style"),
    Output("location-dropdown", "style"),
    Input("dark-mode-toggle", "value")
)
def toggle_dark_mode(is_dark):
    if is_dark:
        page_style = {"backgroundColor": "#121212", "minHeight": "100vh", "color": "white", "paddingBottom": "20px"}
        card_style = {"backgroundColor": "#1e1e1e", "color": "white", "border": "1px solid #2c2c2c"}
        title_style = {"color": "white"}
        dropdown_style = {"backgroundColor": "white", "color": "black", "border": "1px solid #555"}
    else:
        page_style = {"backgroundColor": "#f8f9fa", "minHeight": "100vh", "color": "black", "paddingBottom": "20px"}
        card_style = {"backgroundColor": "white", "color": "black"}
        title_style = {"color": "black"}
        dropdown_style = {"backgroundColor": "white", "color": "black", "border": "1px solid #ccc"}

    return (
        page_style, card_style, card_style, title_style,
        card_style, card_style, card_style, card_style,
        dropdown_style, dropdown_style, dropdown_style
    )

# ================= DROPDOWN CALLBACKS =================
@callback(
    Output("sheet-dropdown", "options"),
    Output("sheet-dropdown", "value"),
    Input("auto-refresh", "n_intervals"),
    State("sheet-dropdown", "value")
)
def update_sheets(_interval, current_sheet):
    if not os.path.exists(FILE_PATH):
        return [], None
    xls = pd.ExcelFile(FILE_PATH)
    sheets = xls.sheet_names
    options = [{"label": s, "value": s} for s in sheets]
    value = current_sheet if current_sheet in sheets else (sheets[0] if sheets else None)
    return options, value

@callback(
    Output("date-dropdown", "options"),
    Output("date-dropdown", "value"),
    Input("sheet-dropdown", "value"),
    Input("auto-refresh", "n_intervals"),
    State("date-dropdown", "value")
)
def update_dates(sheet, _interval, current_date):
    df = safe_read_excel(sheet)
    if df.empty or "Date" not in df.columns:
        return [], None
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
    dates = sorted(df["Date"].dropna().unique())
    options = [{"label": str(d), "value": str(d)} for d in dates]
    value = current_date if current_date in [o["value"] for o in options] else (options[0]["value"] if options else None)
    return options, value

@callback(
    Output("location-dropdown", "options"),
    Output("location-dropdown", "value"),
    Input("sheet-dropdown", "value"),
    Input("date-dropdown", "value"),
    Input("auto-refresh", "n_intervals"),
    State("location-dropdown", "value")
)
def update_locations(sheet, date, _interval, current_location):
    df = safe_read_excel(sheet)
    if df.empty or "Date" not in df.columns or "Location" not in df.columns or not date:
        return [], None
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
    dff = df[df["Date"].astype(str) == date]
    locs = sorted(dff["Location"].dropna().unique())
    options = [{"label": l, "value": l} for l in locs]
    value = current_location if current_location in locs else (locs[0] if locs else None)
    return options, value

# ================= KPI CALLBACK =================
@callback(
    Output("kpi-total", "children"),
    Output("kpi-critical", "children"),
    Output("kpi-moderate", "children"),
    Output("kpi-low", "children"),
    Input("sheet-dropdown", "value"),
    Input("date-dropdown", "value"),
    Input("location-dropdown", "value"),
    Input("auto-refresh", "n_intervals")
)
def update_kpis(sheet, date, location, _):
    total = critical = moderate = minimal = 0
    df = safe_read_excel(sheet)
    if df.empty or "Date" not in df.columns or "Location" not in df.columns:
        return total, critical, moderate, minimal
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
    dff = df[(df["Date"].astype(str) == date) & (df["Location"] == location)]
    total = len(dff)
    if "Value" in dff.columns:
        values = dff["Value"].dropna().str.lower()
        critical = sum(values == "critical")
        moderate = sum(values == "moderate")
        minimal = sum(values == "minimal")
    return total, critical, moderate, minimal

# ================= GRAPH CALLBACK =================
@callback(
    Output("graph-content", "figure"),
    Input("sheet-dropdown", "value"),
    Input("date-dropdown", "value"),
    Input("location-dropdown", "value"),
    Input("dark-mode-toggle", "value"),
    Input("auto-refresh", "n_intervals")
)
def update_graph(sheet, date, location, dark, _):
    df = safe_read_excel(sheet)
    if df.empty or "Date" not in df.columns or "Location" not in df.columns or "Timestamp" not in df.columns:
        return px.line(title="No data")
    
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    dff = df[(df["Date"].astype(str) == date) & (df["Location"] == location)]
    if dff.empty:
        return px.line(title="No data")
    
    template = "plotly_dark" if dark else "plotly_white"

    # ================= ALERTS =================
    if sheet.lower() == "alert":
        dff["Size"] = dff["Value"].apply(lambda x: 18 if str(x).lower() == "critical" else 10)
        fig = px.scatter(
            dff, x="Timestamp", y="Value", color="Value", size="Size",
            color_discrete_map={"Critical": "red", "Moderate": "orange", "Minimal": "green"},
            title=f"{sheet} — {location} ({date})",
            labels={"Value": "Alert Level"}
        )

    # ================= HUMIDITY / TEMPERATURE =================
    elif sheet.lower() in ["humidity", "temperature"]:
        dff["NumericValue"] = pd.to_numeric(dff["Value"].astype(str).str.extract(r"([-+]?\d*\.?\d+)")[0], errors="coerce")
        use_markers = len(dff) <= 50

        y_label = "Temperature (°C)" if sheet.lower() == "temperature" else "Humidity (%)"

        fig = px.line(
            dff.sort_values("Timestamp"),
            x="Timestamp", y="NumericValue",
            markers=use_markers,
            title=f"{sheet} — {location} ({date})",
            labels={"NumericValue": y_label}
        )

        ymin = dff["NumericValue"].min()
        ymax = dff["NumericValue"].max()
        padding = max((ymax - ymin) * 0.1, 1)
        fig.update_yaxes(range=[ymin - padding, ymax + padding])

    # ================= OTHER SHEETS (STRING VALUES) =================
    else:
        use_markers = len(dff) <= 50
        fig = px.line(
            dff.sort_values("Timestamp"),
            x="Timestamp", y="Value",
            markers=use_markers,
            title=f"{sheet} — {location} ({date})",
            labels={"Value": sheet}
        )

    fig.update_traces(line=dict(width=2))
    fig.update_xaxes(nticks=8, tickformat="%H:%M", rangeslider_visible=True)
    fig.update_layout(template=template, title_x=0.5, hovermode="x unified")

    return fig

# ================= RUN APP =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
