Parklytics/
├── app_dashboard.py               # Main script that imports all components
├── components/                    # Dashboard layout modules
│   ├── header.py                  # Title and branding
│   ├── weather.py                 # Weather + radar widget
│   ├── park_info_cards.py         # Park hours, early entry, LL pricing, etc.
│   ├── crowd_index_summary.py     # Crowd index score block
│   ├── snapshot_today.py          # Today's attractions snapshot
│   ├── hourly_trends.py           # Top 10 rides hourly trends
│   └── historical_trends.py       # Historical views for all 4 parks
├── planner/                       # Planner page and sub-features
│   ├── itinerary.py               # Daily itinerary logic/UI
│   ├── ride_priority.py           # Ride checklist & ride-down tracking
│   ├── reservation_reminders.py   # Lightsaber/droid/dining
│   ├── packing_list.py            # General trip packing list
│   └── park_bag.py                # Per-day park bag checklist
├── utils/
│   └── crowd_index_utils.py       # External logic and queries
├── assets/                        # CSS, images, fonts
├── roadmap/
│   ├── roadmap_Q3_2025.md
│   ├── roadmap_Q4_2025.md
│   └── archive/
│       └── roadmap_Q2_2025.md
