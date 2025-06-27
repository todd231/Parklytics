# park_bag_checklist.py

import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc

# Initialize the app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Park Bag Checklist"
server = app.server

# Simulated in-memory user data
mock_users = {
    "test_user_1": set(),
    "test_user_2": set(),
}

# List of all checklist items (grouped by category)
checklist_data = {
    "Health & Comfort": [
        "Tylenol (acetaminophen)", "Advil (ibuprofen)", "Tums", "Imodium", "Gas-X",
        "Dramamine (non-drowsy)", "Liquid I.V. / Propel / DripDrop",
        "Reusable water bottle", "Sunscreen (travel size)", "Mini UV umbrella",
        "Portable fan (USB)", "Cooling towel", "Sweat rag", "Poncho",
        "Compact travel umbrella", "Ziplock bags", "Individual medications"
    ],
    "First Aid": [
        "Band-Aids", "Moleskin/blister pads", "Antiseptic wipes", "Hand sanitizer",
        "Neosporin (mini tube)", "Allergy meds (Benadryl/Claritin)",
        "Contact lens case + solution", "Spare mask"
    ],
    "Tech & Power": [
        "Charging brick (10k+ mAh)", "Charging cable",
        "MagicBand+ charger", "AirTag/Tile in bag"
    ],
    "Personal Items": [
        "Chapstick (SPF)", "Mints/gum", "Tissues", "Hair ties/clips",
        "Mini deodorant", "Compact mirror", "Feminine hygiene items",
        "Mini brush/comb", "Face blotting sheets"
    ],
    "For Families or Littles": [
        "Wipes", "Snacks", "Change of clothes",
        "Autograph book + pen", "Stroller fan", "Glow sticks/bubbles"
    ],
    "Docs & Organization": [
        "Park tickets / MagicBand / ID", "Credit card / Apple Pay / Cash",
        "Photocopy of ID or insurance card", "Zip pouch for receipts", "Extra ziplock bags"
    ],
    "Optional Add-Ons": [
        "Earplugs", "Foldable sit pad"
    ]
}

# User selector dropdown
user_selector = dcc.Dropdown(
    id='select-user',
    options=[{"label": user, "value": user} for user in mock_users.keys()],
    placeholder="Select a user"
)

# Layout
app.layout = dbc.Container([
    html.H2("🎒 Park Bag Checklist"),
    html.P("Select your user and check off items you want to pack. We'll save them for your session."),
    user_selector,
    html.Div(id='checklist-container')
], fluid=True)

# Display checklist per user
@app.callback(
    Output('checklist-container', 'children'),
    Input('select-user', 'value')
)
def update_checklist(user):
    if not user:
        return html.P("Please select a user.")

    sections = []
    user_items = mock_users[user]

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

# Update user-specific checklist data
@app.callback(
    Output({'type': 'category-checklist', 'index': dash.MATCH}, 'value'),
    Input({'type': 'category-checklist', 'index': dash.MATCH}, 'value'),
    State('select-user', 'value'),
    prevent_initial_call=True
)
def update_user_checklist(selected_items, user):
    if user:
        # Reset and repopulate based on all categories
        mock_users[user].difference_update(checklist_data[dash.callback_context.triggered_id['index']])
        mock_users[user].update(selected_items)
    return selected_items

# Run the app
# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=8053, debug=True)

if __name__ == '__main__':
    app.run(debug=True, port=8053)