import dash
from dash import html, dcc, Input, Output, State, ALL
import dash_bootstrap_components as dbc
import uuid
import datetime
from park_bag_checklist import checklist_data

# Initialize the app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "Parklytics Planner"
server = app.server  # for deployment later

# Simulated in-memory user data
mock_users = {
    "test_user_1": {"itinerary": [], "park_bag": set()},
    "test_user_2": {"itinerary": [], "park_bag": set()},
}

# Time dropdown options (6:00am to 1:00am in 15-minute increments)
def generate_time_options():
    times = []
    start = datetime.datetime.strptime("06:00", "%H:%M")
    end = datetime.datetime.strptime("01:00", "%H:%M") + datetime.timedelta(days=1)
    while start <= end:
        times.append({"label": start.strftime("%I:%M %p"), "value": start.strftime("%I:%M %p")})
        start += datetime.timedelta(minutes=15)
    return times

# Park Bag checklist layout generator
def get_park_bag_layout(user):
    if not user:
        return html.P("Please select a user to view the checklist.")

    sections = []
    user_items = mock_users.get(user, {}).get("park_bag", set())

    for category, items in checklist_data.items():
        checklist = dcc.Checklist(
            id={'type': 'category-checklist', 'index': category},
            options=[{'label': item, 'value': item} for item in items],
            value=[item for item in items if item in user_items],
            labelStyle={'display': 'block'},
            inputStyle={"margin-right": "8px"}
        )
        sections.append(html.Div([
            html.H5(category),
            checklist,
            html.Hr()
        ]))
    return html.Div(sections)

# Type dropdown options
itinerary_types = [
    "Ride", "Dining", "Lightning Lane", "Individual Lightning Lane",
    "Special Event", "Character Experience", "Tour/Extra", "Galaxy's Edge Reservation",
    "Dessert Party", "Photo Session", "Other"
]

# Top Navigation Menu
nav_menu = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink("Itinerary", href="/itinerary")),
        dbc.NavItem(dbc.NavLink("Packing List", href="/packing")),
        dbc.NavItem(dbc.NavLink("Park Bag", href="/parkbag")),  # Note: no target="_blank" so it loads in same tab
        dbc.NavItem(dbc.NavLink("Water Stations", href="/water")),
    ],
    brand="Parklytics Planner",
    brand_href="/",
    color="primary",
    dark=True,
    className="mb-4"
)

# Page layouts
itinerary_layout = html.Div([
    html.H2("Itinerary Builder"),
    dcc.Dropdown(
        id='select-user',
        options=[{"label": user, "value": user} for user in mock_users.keys()],
        placeholder="Select a user"
    ),
    html.Div(id='user-itinerary'),
    html.Hr(),
    html.Div([
        html.H4("Add New Itinerary Item"),
        dbc.Row([
            dbc.Col(dcc.Dropdown(id='item-time', options=generate_time_options(), placeholder='Time'), width=2),
            dbc.Col(dcc.Dropdown(id='item-type', options=[{"label": t, "value": t} for t in itinerary_types], placeholder='Type'), width=2),
            dbc.Col(dbc.Input(id='item-name', type='text', placeholder='Name/Description'), width=3),
            dbc.Col(dbc.Input(id='item-location', type='text', placeholder='Location (optional)'), width=2),
            dbc.Col(dbc.Input(id='item-notes', type='text', placeholder='Notes (optional)'), width=2),
            dbc.Col(dbc.Button("Add", id='add-item-btn', color='success'), width=1)
        ])
    ])
])

packing_layout = html.Div([
    html.H2("Trip Packing List (Coming Soon)")
])

water_layout = html.Div([
    html.H2("Water Bottle Refill Stations (Coming Soon)")
])

# App Layout
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    nav_menu,
    html.Div(id='page-content'),
])

# Page routing callback
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname'),
    prevent_initial_call=True
)
def display_page(pathname):
    if pathname == '/packing':
        return packing_layout
    elif pathname == '/water':
        return water_layout
    elif pathname == '/itinerary':
        return itinerary_layout
    elif pathname == '/parkbag':
        # Delay showing park bag page until user is selected
        return html.Div([
            dcc.Dropdown(
                id='select-user-parkbag',
                options=[{"label": user, "value": user} for user in mock_users.keys()],
                placeholder="Select a user to view their Park Bag checklist"
            ),
            html.Div(id='parkbag-layout-container')
        ])
    else:
        return itinerary_layout


# Show user's itinerary items
@app.callback(
    Output('user-itinerary', 'children'),
    Input('select-user', 'value')
)
def show_user_itinerary(user):
    if not user:
        return html.P("Select a user to view their itinerary.")
    itinerary = mock_users.get(user, {}).get("itinerary", [])
    if not itinerary:
        return html.P("No itinerary items yet.")
    sorted_itinerary = sorted(itinerary, key=lambda item: datetime.datetime.strptime(item['time'], "%I:%M %p"))
    return html.Div([
        html.Div([
            dbc.Row([
                dbc.Col(dcc.Dropdown(
                    id={'type': 'edit-time', 'index': item['id']},
                    options=generate_time_options(),
                    value=item['time'],
                    clearable=False
                ), width=2),
                dbc.Col(dcc.Dropdown(
                    id={'type': 'edit-type', 'index': item['id']},
                    options=[{"label": t, "value": t} for t in itinerary_types],
                    value=item['type'],
                    clearable=False
                ), width=2),
                dbc.Col(dbc.Input(id={'type': 'edit-name', 'index': item['id']}, value=item['name']), width=3),
                dbc.Col(dbc.Input(id={'type': 'edit-location', 'index': item['id']}, value=item['location']), width=2),
                dbc.Col(dbc.Input(id={'type': 'edit-notes', 'index': item['id']}, value=item['notes']), width=2),
                dbc.Col(dbc.Button("Save", id={'type': 'save-item', 'index': item['id']}, color='primary'), width=1)
            ], className="mb-2")
        ]) for item in sorted_itinerary
    ])

# Save itinerary edits
@app.callback(
    Output('user-itinerary', 'children', allow_duplicate=True),
    Input({'type': 'save-item', 'index': ALL}, 'n_clicks'),
    State('select-user', 'value'),
    State({'type': 'edit-time', 'index': ALL}, 'value'),
    State({'type': 'edit-type', 'index': ALL}, 'value'),
    State({'type': 'edit-name', 'index': ALL}, 'value'),
    State({'type': 'edit-location', 'index': ALL}, 'value'),
    State({'type': 'edit-notes', 'index': ALL}, 'value'),
    prevent_initial_call=True
)
def save_itinerary_edits(n_clicks, user, times, types, names, locations, notes):
    if not user or not n_clicks or not any(n_clicks):
        return dash.no_update
    edited_data = zip(times, types, names, locations, notes)
    for i, (time, type_, name, loc, note) in enumerate(edited_data):
        if i < len(mock_users[user]['itinerary']):
            mock_users[user]['itinerary'][i]['time'] = time
            mock_users[user]['itinerary'][i]['type'] = type_
            mock_users[user]['itinerary'][i]['name'] = name
            mock_users[user]['itinerary'][i]['location'] = loc
            mock_users[user]['itinerary'][i]['notes'] = note
    mock_users[user]['itinerary'].sort(key=lambda item: datetime.datetime.strptime(item['time'], "%I:%M %p"))
    return show_user_itinerary(user)

@app.callback(
    Output('parkbag-layout-container', 'children'),
    Input('select-user-parkbag', 'value')
)
def update_parkbag_for_user(user):
    if not user:
        return html.P("Please select a user.")
    return get_park_bag_layout(user)

# Add new item to itinerary and clear inputs
@app.callback(
    [
        Output('user-itinerary', 'children', allow_duplicate=True),
        Output('item-time', 'value'),
        Output('item-type', 'value'),
        Output('item-name', 'value'),
        Output('item-location', 'value'),
        Output('item-notes', 'value'),
    ],
    Input('add-item-btn', 'n_clicks'),
    State('select-user', 'value'),
    State('item-time', 'value'),
    State('item-type', 'value'),
    State('item-name', 'value'),
    State('item-location', 'value'),
    State('item-notes', 'value'),
    prevent_initial_call=True
)
def add_itinerary_item(n, user, time, type_, name, location, notes):
    if not all([user, time, type_, name]):
        return html.P("All fields except Location and Notes are required."), None, None, None, None, None
    new_item = {
        "id": str(uuid.uuid4()),
        "time": time,
        "type": type_,
        "name": name,
        "location": location or "",
        "notes": notes or ""
    }
    mock_users[user]["itinerary"].append(new_item)
    mock_users[user]["itinerary"].sort(key=lambda item: datetime.datetime.strptime(item['time'], "%I:%M %p"))
    return show_user_itinerary(user), None, None, None, None, None


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8052, debug=True)


# import dash
# from dash import html, dcc, Input, Output, State, ctx, ALL, MATCH
# import dash_bootstrap_components as dbc
# import uuid
# import datetime
# from park_bag_checklist import checklist_data

# # Initialize the app
# app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
# app.title = "Parklytics Planner"
# server = app.server  # for deployment later

# # Simulated in-memory user data
# mock_users = {
#     "test_user_1": {
#         "itinerary": []
#     },
#     "test_user_2": {
#         "itinerary": []
#     }
# }

# # Time dropdown options (6:00am to 1:00am in 15-minute increments)
# def generate_time_options():
#     times = []
#     start = datetime.datetime.strptime("06:00", "%H:%M")
#     end = datetime.datetime.strptime("01:00", "%H:%M") + datetime.timedelta(days=1)
#     while start <= end:
#         times.append({"label": start.strftime("%I:%M %p"), "value": start.strftime("%I:%M %p")})
#         start += datetime.timedelta(minutes=15)
#     return times

# # 06/27/2025 Park Bag link
# def get_park_bag_layout(user):
#     if not user:
#         return html.P("Please select a user to view the checklist.")

#     sections = []
#     user_items = mock_users.get(user, set())

#     for category, items in checklist_data.items():
#         checklist = dcc.Checklist(
#             id={'type': 'category-checklist', 'index': category},
#             options=[{'label': item, 'value': item} for item in items],
#             value=[item for item in items if item in user_items],
#             labelStyle={'display': 'block'},
#             inputStyle={"margin-right": "8px"}
#         )
#         sections.append(html.Div([
#             html.H5(category),
#             checklist,
#             html.Hr()
#         ]))
#     return html.Div(sections)


# # Type dropdown options
# itinerary_types = [
#     "Ride", "Dining", "Lightning Lane", "Individual Lightning Lane",
#     "Special Event", "Character Experience", "Tour/Extra", "Galaxy's Edge Reservation",
#     "Dessert Party", "Photo Session", "Other"
# ]

# # Top Navigation Menu
# nav_menu = dbc.NavbarSimple(
#     children=[
#         dbc.NavItem(dbc.NavLink("Itinerary", href="/itinerary")),
#         dbc.NavItem(dbc.NavLink("Packing List", href="/packing")),
#         dbc.NavItem(dbc.NavLink("Park Bag", href="http://localhost:8053", target="_blank")),
#         dbc.NavItem(dbc.NavLink("Water Stations", href="/water")),
#     ],
#     brand="Parklytics Planner",
#     brand_href="/",
#     color="primary",
#     dark=True,
#     className="mb-4"
# )

# # Page layouts
# itinerary_layout = html.Div([
#     html.H2("Itinerary Builder"),
#     dcc.Dropdown(
#         id='select-user',
#         options=[{"label": user, "value": user} for user in mock_users.keys()],
#         placeholder="Select a user"
#     ),
#     html.Div(id='user-itinerary'),
#     html.Hr(),
#     html.Div([
#         html.H4("Add New Itinerary Item"),
#         dbc.Row([
#             dbc.Col(dcc.Dropdown(id='item-time', options=generate_time_options(), placeholder='Time'), width=2),
#             dbc.Col(dcc.Dropdown(id='item-type', options=[{"label": t, "value": t} for t in itinerary_types], placeholder='Type'), width=2),
#             dbc.Col(dbc.Input(id='item-name', type='text', placeholder='Name/Description'), width=3),
#             dbc.Col(dbc.Input(id='item-location', type='text', placeholder='Location (optional)'), width=2),
#             dbc.Col(dbc.Input(id='item-notes', type='text', placeholder='Notes (optional)'), width=2),
#             dbc.Col(dbc.Button("Add", id='add-item-btn', color='success'), width=1)
#         ])
#     ])
# ])

# packing_layout = html.Div([
#     html.H2("Trip Packing List (Coming Soon)")
# ])

# park_bag_layout = html.Div([
#     html.H2("Park Bag Packing List (Coming Soon)")
# ])

# water_layout = html.Div([
#     html.H2("Water Bottle Refill Stations (Coming Soon)")
# ])

# # App Layout
# app.layout = html.Div([
#     dcc.Location(id='url', refresh=False),
#     nav_menu,
#     html.Div(id='page-content'),
#     dcc.Store(id='itinerary-store', storage_type='memory')
# ])

# # Page routing
# @app.callback(
#     Output('page-content', 'children'), 
#     Input('url', 'pathname'), 
#     State('select-user', 'value')
#     )

# def display_page(pathname, user):
#     if pathname == '/packing':
#         return packing_layout
#     elif pathname == '/parkbag':
#         return get_park_bag_layout(user)
#     elif pathname == '/water':
#         return water_layout
#     else:
#         return itinerary_layout


# # def display_page(pathname):
# #     if pathname == '/packing':
# #         return packing_layout
# #     elif pathname == '/parkbag':
# #         return get_park_bag_layout()
# #     elif pathname == '/water':
# #         return water_layout
# #     else:
# #         return itinerary_layout

# # Display selected user's itinerary
# @app.callback(
#     Output('user-itinerary', 'children'),
#     Input('select-user', 'value')
# )
# def show_user_itinerary(user):
#     if not user:
#         return html.P("Select a user to view their itinerary.")
#     itinerary = mock_users.get(user, {}).get("itinerary", [])
#     if not itinerary:
#         return html.P("No itinerary items yet.")
#     sorted_itinerary = sorted(itinerary, key=lambda item: datetime.datetime.strptime(item['time'], "%I:%M %p"))
#     return html.Div([
#         html.Div([
#             dbc.Row([
#                 dbc.Col(dcc.Dropdown(
#                     id={'type': 'edit-time', 'index': item['id']},
#                     options=generate_time_options(),
#                     value=item['time'],
#                     clearable=False
#                 ), width=2),
#                 dbc.Col(dcc.Dropdown(
#                     id={'type': 'edit-type', 'index': item['id']},
#                     options=[{"label": t, "value": t} for t in itinerary_types],
#                     value=item['type'],
#                     clearable=False
#                 ), width=2),
#                 dbc.Col(dbc.Input(id={'type': 'edit-name', 'index': item['id']}, value=item['name']), width=3),
#                 dbc.Col(dbc.Input(id={'type': 'edit-location', 'index': item['id']}, value=item['location']), width=2),
#                 dbc.Col(dbc.Input(id={'type': 'edit-notes', 'index': item['id']}, value=item['notes']), width=2),
#                 dbc.Col(dbc.Button("Save", id={'type': 'save-item', 'index': item['id']}, color='primary'), width=1)
#             ], className="mb-2")
#         ]) for item in sorted_itinerary
#     ])

# # Save edits to itinerary
# @app.callback(
#     Output('user-itinerary', 'children', allow_duplicate=True),
#     Input({'type': 'save-item', 'index': ALL}, 'n_clicks'),
#     State('select-user', 'value'),
#     State({'type': 'edit-time', 'index': ALL}, 'value'),
#     State({'type': 'edit-type', 'index': ALL}, 'value'),
#     State({'type': 'edit-name', 'index': ALL}, 'value'),
#     State({'type': 'edit-location', 'index': ALL}, 'value'),
#     State({'type': 'edit-notes', 'index': ALL}, 'value'),
#     prevent_initial_call=True
# )
# def save_itinerary_edits(n_clicks, user, times, types, names, locations, notes):
#     if not user or not n_clicks or not any(n_clicks):
#         return dash.no_update
#     edited_data = zip(times, types, names, locations, notes)
#     for i, (time, type_, name, loc, note) in enumerate(edited_data):
#         if i < len(mock_users[user]['itinerary']):
#             mock_users[user]['itinerary'][i]['time'] = time
#             mock_users[user]['itinerary'][i]['type'] = type_
#             mock_users[user]['itinerary'][i]['name'] = name
#             mock_users[user]['itinerary'][i]['location'] = loc
#             mock_users[user]['itinerary'][i]['notes'] = note
#     sorted_itinerary = sorted(mock_users[user]['itinerary'], key=lambda item: datetime.datetime.strptime(item['time'], "%I:%M %p"))
#     mock_users[user]['itinerary'] = sorted_itinerary
#     return show_user_itinerary(user)

# # Add new item to itinerary and clear inputs
# @app.callback(
#     [
#         Output('user-itinerary', 'children', allow_duplicate=True),
#         Output('item-time', 'value'),
#         Output('item-type', 'value'),
#         Output('item-name', 'value'),
#         Output('item-location', 'value'),
#         Output('item-notes', 'value'),
#     ],
#     Input('add-item-btn', 'n_clicks'),
#     State('select-user', 'value'),
#     State('item-time', 'value'),
#     State('item-type', 'value'),
#     State('item-name', 'value'),
#     State('item-location', 'value'),
#     State('item-notes', 'value'),
#     prevent_initial_call=True
# )

# # Add the missing decorator here to make it a callback:
# @app.callback(
#     [
#         Output('user-itinerary', 'children', allow_duplicate=True),
#         Output('item-time', 'value'),
#         Output('item-type', 'value'),
#         Output('item-name', 'value'),
#         Output('item-location', 'value'),
#         Output('item-notes', 'value'),
#     ],
#     Input('add-item-btn', 'n_clicks'),
#     State('select-user', 'value'),
#     State('item-time', 'value'),
#     State('item-type', 'value'),
#     State('item-name', 'value'),
#     State('item-location', 'value'),
#     State('item-notes', 'value'),
#     prevent_initial_call=True
# )
# def add_itinerary_item(n, user, time, type_, name, location, notes):
#     if not all([user, time, type_, name]):
#         return html.P("All fields except Location and Notes are required."), None, None, None, None, None
#     new_item = {
#         "id": str(uuid.uuid4()),
#         "time": time,
#         "type": type_,
#         "name": name,
#         "location": location or "",
#         "notes": notes or ""
#     }
#     mock_users[user]["itinerary"].append(new_item)
#     sorted_itinerary = sorted(mock_users[user]["itinerary"], key=lambda item: datetime.datetime.strptime(item['time'], "%I:%M %p"))
#     mock_users[user]["itinerary"] = sorted_itinerary
#     return show_user_itinerary(user), None, None, None, None, None

# # def add_itinerary_item(n, user, time, type_, name, location, notes):
# #     if not all([user, time, type_, name]):
# #         return html.P("All fields except Location and Notes are required."), None, None, None, None, None
# #     new_item = {
# #         "id": str(uuid.uuid4()),
# #         "time": time,
# #         "type": type_,
# #         "name": name,
# #         "location": location or "",
# #         "notes": notes or ""
# #     }
# #     mock_users[user]["itinerary"].append(new_item)
# #     sorted_itinerary = sorted(mock_users[user]["itinerary"], key=lambda item: datetime.datetime.strptime(item['time'], "%I:%M %p"))
# #     mock_users[user]["itinerary"] = sorted_itinerary
# #     return show_user_itinerary(user), None, None, None, None, None


# # Run the app
# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=8052, debug=True)
