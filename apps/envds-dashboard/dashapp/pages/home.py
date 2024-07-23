import dash
from dash import html, callback, dcc, Input, Output
import dash_bootstrap_components as dbc
from dash_extensions import WebSocket
from ulid import ULID

dash.register_page(__name__, path='/')

CONTENT_STYLE = {
    "margin-left": "18rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
}

# print("here:1")
def get_layout():
    layout = html.Div([
        html.H1('This is our Home page'),
        dbc.Card('This is our Home page content.', body=True),
        # html.Div('This is our Home page content.'),
        dcc.Input(id="input", autoComplete="off", debounce=True),
        html.Div(id="message"),
        WebSocket(id="ws", url=f"ws://10.55.169.1:8080/envds/dashboard/ws/sensor/main")
    # ], style=CONTENT_STYLE)
    ])
    # try:
    #     send("init request")
    # except Exception as e:
    #     print(e)

    return layout

layout = get_layout()

@callback(
    Output('ws', "send"),
    Input("input", "value")
)
def send(value):
    print(f"sending: {value}")
    return value

@callback(Output("message", "children"), Input("ws", "message"))
def message(e):
    if e:
        return f"Response from websocket: {e['data']}"
    else:
        return "No response"
    
# # startup code
# send("startup request")
