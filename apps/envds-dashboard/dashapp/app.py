import dash
from flask import Flask
from dash import Dash, html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from dash_extensions import WebSocket
# from dash_extensions.enrich import html, dcc, Output, Input, DashProxy, State


server = Flask(__name__, instance_relative_config=False)
app = Dash(
    # app = DashProxy(
    __name__,
    server=server,
    use_pages=True,
    requests_pathname_prefix="/envds/dashboard/dash/",#sensor/",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

sidebar_header = dbc.Row(
    [
        dbc.Col(html.H4("UAS-DAQ", className="display-4")),
        dbc.Col(
            html.Button(
                # use the Bootstrap navbar-toggler classes to style the toggle
                html.Span(className="navbar-toggler-icon"),
                className="navbar-toggler",
                # the navbar-toggler classes don't set color, so we do it here
                style={
                    "color": "rgba(0,0,0,.5)",
                    "border-color": "rgba(0,0,0,.1)",
                },
                id="toggle",
            ),
            # the column containing the toggle will be only as wide as the
            # toggle, resulting in the toggle being right aligned
            width="auto",
            # vertically align the toggle in the center
            align="center",
        ),
    ]
)

sidebar = html.Div(
    [
        sidebar_header,
        # we wrap the horizontal rule and short blurb in a div that can be
        # hidden on a small screen
        # html.Div(
        #     [
        #         html.Hr(),
        #         html.P(
        #             "A responsive sidebar layout with collapsible navigation " "links.",
        #             className="lead",
        #         ),
        #     ],
        #     id="blurb",
        # ),
        # use the Collapse component to animate hiding / revealing links
        dbc.Collapse(
            dbc.Nav(
                # [
                #     dbc.NavLink("Home", href="/uasdaq/dashboard/sensor", active="exact"),
                #     dbc.NavLink("Page 1", href="/uasdaq/dashboard/sensor1", active="exact"),
                #     dbc.NavLink("Page 2", href="/uasdaq/dashboard/sensor2", active="exact"),
                # ],
                [
                    dbc.NavLink(
                        html.Div(page["name"], className="ms-2"),
                        href=f'/envds/dashboard/dash{page["path"]}',
                        active="exact",
                    )
                    for page in dash.page_registry.values()
                ],
                vertical=True,
                pills=True,
            ),
            id="collapse",
        ),
    ],
    id="sidebar"
)

# footer = html.Div(
#     [
#         html.Footer(
#             children=[
#                 dbc.Row([
#                     dbc.Input(id="chat-input", autoComplete="off", debounce=True),
#                     dbc.Card(id="chat-output", body=True)                    
#                 ])
#             ],
#             id="footer-content"
#         ),
#         WebSocket(id="chat-ws", url=f"ws://uasdaq.pmel.noaa.gov/uasdaq/dashboard/ws/chat/dash")

#     ]
# )

# def get_layout():
# layout = html.Div(
#     [
#         html.H1("Multi-page app with Dash Pages"),
#         html.Div(
#             [
#                 html.Div(
#                     dcc.Link(
#                         f"{page['name']} - {page['path']}",
#                         href=page["relative_path"],
#                     )
#                 )
#                 for page in dash.page_registry.values()
#             ]
#         ),
#         dash.page_container,
#     ]
# )

# content = html.Div(id="page-content")

# print("sensor app: get_layout")
# return layout


# app.layout = get_layout()
app.layout = html.Div([dcc.Location(id="url"), sidebar, dash.page_container])#, footer])
# app.layout = html.Div([dcc.Location(id="url"), dash.page_container])

@app.callback(
    Output("sidebar", "className"),
    Input("toggle", "n_clicks"),
    State("sidebar", "className"),
)
def toggle_classname(n, classname):
    if n and classname == "":
        return "collapsed"
    return ""


@app.callback(
    Output("collapse", "is_open"),
    Input("toggle", "n_clicks"),
    State("collapse", "is_open"),
)
def toggle_collapse(n, is_open):
    if n:
        return not is_open
    return is_open

# @app.callback(
#     Output('chat-ws', "send"),
#     [Input("chat-input", "value")]
# )
# def send(value):
#     print(f"sending to chat: {value}")
#     return value

# @app.callback(Output("chat-output", "children"), [Input("chat-ws", "message")])
# def message(e):
#     if e:
#         print(f"e: {e}, data: {e['data']}")
#         return e['data']
#         # return f"Response from chat: {e['data']}"
#     else:
#         return "No response"


if __name__ == "__main__":
    server.run(debug=True)
