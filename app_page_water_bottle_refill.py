import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

# Water station layout
water_layout = dbc.Container(
    [
        dbc.Row(
            dbc.Col(
                html.Div([
                    html.H2("💧 Water Bottle Refill Station Locations", className="text-center my-4"),
                    html.Pre(
                        """🏰 Magic Kingdom
• Cosmic Ray’s Starlight Café (Tomorrowland; between Bays 2 & 3) 
• Pinocchio Village Haus (Fantasyland; just outside exit courtyard) 
• TRON Lightcycle / Run Restrooms (Tomorrowland; just outside attraction queue) 

🌐 EPCOT
• Odyssey Pavilion (World Discovery; inside, near World Showcase entrance) 
• Refreshment Port Restrooms (World Nature / Showcase Entrance) 
• Guest Relations or Connections Restrooms (World Celebration / Discovery) 
• International Gateway Restrooms (between France & UK pavillions) 
• Restrooms near Journey of Water, Inspired by Moana (World Nature) 

🎬 Hollywood Studios
• Galaxy’s Edge:
  o Batuu Market Restrooms (Black Spire Outpost) 
  o Milk Stand area restrooms 
  o Millennium Falcon: Smugglers Run exit queue 
• Outside Park Entrance: bottle fillers at restrooms near security/checkpoint 
• Near Skyliner Station Restrooms (just outside the park) 

🐾 Animal Kingdom
• Avatar Flight of Passage queue (Pandora; just before restroom area) 
• Na’vi River Journey queue (Pandora) 
• First Aid (Discovery Island central area) 

💡 Additional Tips
• Quick-service restaurants throughout all parks allow you to self-fill water bottles at soda fountains (ice + water); ask at counters for a free cup if needed 
• For cold, filtered water, these self-serve fountains often taste better than standard fountain refills, especially compared to some park water sources
""",
                        style={"whiteSpace": "pre-wrap", "textAlign": "center", "fontSize": "1.1rem"},
                        className="text-body"
                    )
                ])
            )
        )
    ],
    fluid=True,
    className="p-5"
)

# Optional run for standalone dev
if __name__ == '__main__':
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.title = "Water Bottle Refill Stations"
    app.layout = water_layout
    app.run(debug=True, port=8053)
