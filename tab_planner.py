import dash
from dash import html, dcc, Input, Output, State, ALL, ctx
import dash_bootstrap_components as dbc
import uuid
import datetime
from page_park_bag_checklist import checklist_data
from page_water_bottle_refill import water_layout

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
    user_items = mock_users.get(user, set())

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

    return dbc.Container([
        html.H2("🎒 Park Bag Checklist", className="text-center mb-4"),
        html.P("Select your user and check off items you want to pack.", className="text-center"),
        dbc.Row([
            dbc.Col(html.Div(sections), width=10, lg=8, className="mx-auto")
        ])
    ], fluid=True)


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

# water_layout = html.Div([
#     html.H2("Water Bottle Refill Stations (Coming Soon)")
# ])

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


# Show user's itinerary items in layout function (no changes)
def show_user_itinerary(user):
    if not user:
        return html.P("Select a user to view their itinerary.")
    itinerary = mock_users.get(user, {}).get("itinerary", [])
    if not itinerary:
        return html.P("No itinerary items yet.")
    sorted_itinerary = sorted(itinerary, key=lambda item: datetime.datetime.strptime(item['time'], "%I:%M %p"))
    rows = []
    for item in sorted_itinerary:
        rows.append(
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
                    dbc.Col([
                        dbc.Button("Save", id={'type': 'save-item', 'index': item['id']}, color='primary', className='d-block mb-1 w-100'),
                        dbc.Button("Delete", id={'type': 'delete-item', 'index': item['id']}, color='danger', size='sm')
                    ], width=2),
                ], className="mb-2")
            ])
        )
    return html.Div(rows)


# COMBINED CALLBACK to handle user selection, adding, saving, deleting itinerary items
@app.callback(
    Output('user-itinerary', 'children'),
    [
        Input('select-user', 'value'),
        Input('add-item-btn', 'n_clicks'),
        Input({'type': 'save-item', 'index': ALL}, 'n_clicks'),
        Input({'type': 'delete-item', 'index': ALL}, 'n_clicks'),
    ],
    [
        State('select-user', 'value'),
        State('item-time', 'value'),
        State('item-type', 'value'),
        State('item-name', 'value'),
        State('item-location', 'value'),
        State('item-notes', 'value'),
        State({'type': 'edit-time', 'index': ALL}, 'value'),
        State({'type': 'edit-type', 'index': ALL}, 'value'),
        State({'type': 'edit-name', 'index': ALL}, 'value'),
        State({'type': 'edit-location', 'index': ALL}, 'value'),
        State({'type': 'edit-notes', 'index': ALL}, 'value'),
    ],
    prevent_initial_call=True,
)
def handle_itinerary(select_user_val, add_clicks, save_clicks, delete_clicks,
                     user_state,
                     add_time, add_type, add_name, add_location, add_notes,
                     edit_times, edit_types, edit_names, edit_locations, edit_notes):
    
    triggered = ctx.triggered_id

    if triggered is None:
        return dash.no_update

    # User selection changed - show itinerary for that user
    if triggered == 'select-user':
        if not select_user_val:
            return html.P("Select a user to view their itinerary.")
        return show_user_itinerary(select_user_val)

    # Add new item button clicked
    if triggered == 'add-item-btn':
        if not all([user_state, add_time, add_type, add_name]):
            return html.P("All fields except Location and Notes are required.")
        new_item = {
            "id": str(uuid.uuid4()),
            "time": add_time,
            "type": add_type,
            "name": add_name,
            "location": add_location or "",
            "notes": add_notes or ""
        }
        mock_users[user_state]["itinerary"].append(new_item)
        mock_users[user_state]["itinerary"].sort(key=lambda item: datetime.datetime.strptime(item['time'], "%I:%M %p"))
        return show_user_itinerary(user_state)

    # Save button clicked
    if isinstance(triggered, dict) and triggered.get('type') == 'save-item':
        item_id = triggered['index']
        if not user_state:
            return dash.no_update
        itinerary = mock_users[user_state]['itinerary']
        idx = next((i for i, itm in enumerate(itinerary) if itm['id'] == item_id), None)
        if idx is None:
            return dash.no_update
        mock_users[user_state]['itinerary'][idx]['time'] = edit_times[idx]
        mock_users[user_state]['itinerary'][idx]['type'] = edit_types[idx]
        mock_users[user_state]['itinerary'][idx]['name'] = edit_names[idx]
        mock_users[user_state]['itinerary'][idx]['location'] = edit_locations[idx]
        mock_users[user_state]['itinerary'][idx]['notes'] = edit_notes[idx]
        mock_users[user_state]['itinerary'].sort(key=lambda item: datetime.datetime.strptime(item['time'], "%I:%M %p"))
        return show_user_itinerary(user_state)

    # Delete button clicked
    if isinstance(triggered, dict) and triggered.get('type') == 'delete-item':
        item_id = triggered['index']
        if not user_state:
            return dash.no_update
        mock_users[user_state]['itinerary'] = [item for item in mock_users[user_state]['itinerary'] if item['id'] != item_id]
        return show_user_itinerary(user_state)

    return dash.no_update


@app.callback(
    Output('parkbag-layout-container', 'children'),
    Input('select-user-parkbag', 'value')
)
def update_parkbag_for_user(user):
    if not user:
        return html.P("Please select a user.")
    return get_park_bag_layout(user)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8052, debug=True)

