# 📅 Parklytics Roadmap – Q3 2025
🗓 July–September 2025  
🎯 Focus: Dashboard Visual Enhancements, Planner Integration, and Core Stability

---

## ✅ Top Priorities (Now / Actively Working On)
- [ ] **Redesign dashboard to feature only Park Info Cards and Crowd Index Summary on landing**  
      → Make cards clickable to reveal snapshot, trends, and historical data views
- [ ] Implement dynamic hourly trend graphs for each park based on real park hours
- [ ] Adjust historical trend graphs to respect actual closing times (not hardcoded to 11:00pm)
- [ ] Standardize and compact Park Info Cards for consistent layout and sizing
- [ ] Make "Closed Attractions" in Today’s Snapshot expandable (click/tap to reveal)
- [ ] Add 2:00am data reconnection routine to fix rare stale-data edge case
- [ ] Add top navigation link to the new Planner tab
- [ ] Improve Park Bag Checklist UX to actually build a selected list
- [ ] Begin Trip Packing List UI for clothes/gear (basic starter version)
- [ ] Finalize integration of Crowd Index Summary into the dashboard layout
- [ ] Continue wiring and layout polish for `alt_dashboard` v2

---

## 🟡 In Progress / Queued Next
- [ ] Add search functionality to retrieve historical trends for specific attractions
- [ ] Begin testing redesigned itinerary workflow
- [ ] Fix Water Bottle Station layout and formatting for clarity

---

## 🕹️ Notes / Considerations
- Keep code monolithic during Q3 to support active layout updates  
- Defer mobile/responsive design work until Q4  
- Hold off on branding/tagline polish until dashboard content stabilizes

---

## 🟪 Deferred to Q4+
- [ ] Refactor dashboard into modular components (see `Q4 roadmap`)
- [ ] Full itinerary feature rebuild with alerts and reservations
- [ ] Begin AWS migration planning and environment setup

🕓 Last Updated: June 30, 2025
