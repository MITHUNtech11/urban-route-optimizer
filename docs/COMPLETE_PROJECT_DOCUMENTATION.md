# Urban Route Optimizer

Complete Project Documentation

Version: 1.0
Date: 2026-04-17
Repository: MITHUNtech11/urban-route-optimizer

---

## 1. Project Overview

Urban Route Optimizer is a Python geospatial routing system that builds real road graphs from OpenStreetMap and computes optimized city routes for two-wheelers and road vehicles.

The system supports:
- distance-based shortest routing
- traffic-aware travel-time routing
- real-time context integration (weather + optional live traffic)
- specialized delivery and emergency use-cases
- urban planning insights (heatmap, hotspots, recommendations)
- two interfaces: CLI and Streamlit web app

Primary goals:
- demonstrate graph algorithms in a real-world mobility context
- provide explainable route alternatives and metrics
- remain reproducible for college demo/viva workflows

---

## 2. Problem Statement

Urban route selection is often habit-driven and non-optimal. This project provides an open, explainable routing pipeline where roads are modeled as a weighted graph and route decisions are algorithmic.

It addresses:
- longer travel times due to non-optimal route choices
- lack of transparency in black-box routing systems for academic evaluation
- need for offline-capable and reproducible demo execution

---

## 3. Scope and Use Cases

### 3.1 Standard routing
Compute recommended and alternative routes between two locations.

### 3.2 Delivery routing
Compute multi-leg delivery path using greedy nearest-next-stop selection.

### 3.3 Emergency routing
Prioritize travel-time performance with emergency speed multipliers by road type.

### 3.4 Planning analytics
Analyze route overlap, corridor hotspots, and road-type usage distribution.

---

## 4. Feature Summary

- OpenStreetMap network extraction by place name
- profile-based graph build: scooter, bike, drive
- scooter profile edge filtering for unsuitable roads
- Dijkstra and A* shortest path
- k-shortest simple path alternatives
- time-slot traffic modeling and intensity scaling
- weather penalty factor from Open-Meteo
- optional live traffic override from TomTom Flow API
- delivery route optimization with optional return-to-start
- route map export to Folium HTML with layers and control tools
- Streamlit UI with city and area suggestion workflow
- offline mode with GraphML loading and fallback cache selection

---

## 5. Technology Stack

- Python 3.x
- osmnx
- networkx
- folium
- pandas
- geopandas
- pyproj
- streamlit

Dependencies are listed in requirements.txt.

---

## 6. Repository Structure

```
urban-route-optimizer/
|-- main.py
|-- streamlit_app.py
|-- requirements.txt
|-- README.md
|-- docs/
|   |-- PROJECT_REPORT_AND_VIVA.md
|   |-- COMPLETE_PROJECT_DOCUMENTATION.md
|-- src/
|   |-- __init__.py
|   |-- build_graph.py
|   |-- calculate_route.py
|   |-- realtime.py
|   |-- specialized.py
|   |-- analytics.py
|   |-- visualize.py
|-- data/
|   |-- *.graphml
|-- cache/
|   |-- *.json
|-- output/
|   |-- *.html
```

---

## 7. Architecture

### 7.1 Layered architecture

Input layer:
- CLI arguments or Streamlit form values
- place/city, source, destination, optimization settings

Processing layer:
- graph creation or loading
- edge weighting (distance or travel-time)
- shortest path and alternatives
- realtime context enrichment
- specialized workflow handling
- planning analytics computation

Output layer:
- terminal summary
- interactive route map
- analytics tables/metrics
- saved HTML output files

### 7.2 End-to-end flow

1. Accept user inputs.
2. Build or load graph.
3. Snap coordinates to nearest graph nodes.
4. Prepare weighted graph based on selected objective.
5. Solve for primary route and alternatives.
6. Compute route metrics and diagnostics.
7. Build planning analytics.
8. Render and save interactive map.
9. Display outputs in CLI or Streamlit.

---

## 8. Core Modules and Responsibilities

### 8.1 main.py
Role:
- CLI entrypoint and orchestration

Key responsibilities:
- parse CLI arguments
- trigger graph build and routing pipeline
- call real-time context integration
- call visualization and print route summary

Important helpers:
- parse_coordinate_pair
- parse_stop_list
- print_route_summary

### 8.2 src/build_graph.py
Role:
- graph creation, filtering, cache management

Key logic:
- map profile to OSM network type
- load graph from explicit graph file or cache if available
- offline fallback to first available cached graph for profile
- download from OSM when online and cache enabled
- scooter-specific edge removal by highway tags

Important constants:
- PROFILE_TO_NETWORK_TYPE
- SCOOTER_EXCLUDED_HIGHWAY_TYPES

### 8.3 src/calculate_route.py
Role:
- route calculation engine

Key logic:
- convert MultiDiGraph to weighted DiGraph
- apply edge speed, traffic, weather, emergency adjustments
- shortest path via Dijkstra or A*
- alternatives using shortest_simple_paths
- compute distance, ETA, delay vs free-flow, average speed
- nearest-node fallback using projected graph when needed

Important constants:
- TRAFFIC_SLOT_MULTIPLIERS
- DEFAULT_SPEED_KMPH_BY_HIGHWAY
- EMERGENCY_SPEED_MULTIPLIER_BY_HIGHWAY

### 8.4 src/realtime.py
Role:
- external context fetch and normalization

Key logic:
- fetch weather from Open-Meteo
- estimate weather slowdown factor
- fetch traffic flow from TomTom (when API key provided)
- convert provider responses into routing context object

### 8.5 src/specialized.py
Role:
- specialized workflow helpers

Key logic:
- optimize_delivery_route implements greedy nearest-next stop selection
- merges leg-level outputs into a combined delivery summary

### 8.6 src/analytics.py
Role:
- route analytics for planning insights

Key logic:
- route heatmap point generation with sampling
- segment usage counting across route set
- overlap percentage and hotspot detection
- recommendation generation from route usage patterns

### 8.7 src/visualize.py
Role:
- interactive Folium map rendering

Key logic:
- convert route node paths to map coordinates
- draw recommended and alternative routes with styles
- add start/end markers
- add planning heatmap and hotspot layers
- add summary panel HTML overlay
- save output map file

### 8.8 streamlit_app.py
Role:
- user-facing web interface

Key logic:
- city suggestions and dynamic area suggestions via OSM features
- strict validation (must choose from suggestions)
- geocoding from selected area labels
- route execution, map embedding, and metrics display
- realtime and planning insight sections
- session state management for persistent results

---

## 9. Routing Algorithms and Models

### 9.1 Graph model
- nodes: road intersections
- edges: road segments with attributes (length, highway, maxspeed, geometry)

### 9.2 Primary algorithms
- Dijkstra: weighted shortest path
- A*: weighted shortest path with geodesic heuristic

### 9.3 Alternative routes
Alternatives are generated with k-shortest simple paths:
- total requested route count = alternatives + 1
- first route is recommended route
- remaining routes are alternatives

### 9.4 Weighting modes

Distance mode:
- optimization weight = edge length

Traffic mode:
- optimization weight = travel_time_sec
- effective speed is adjusted by traffic multiplier and weather penalty

### 9.5 Travel-time model

Given edge length $L$ in meters and effective speed $V$ in km/h,

$$
T_{sec} = \frac{L}{V \times 1000 / 3600}
$$

Weather penalty applies as slowdown factor $W \ge 1$:

$$
V_{weather} = \frac{V}{W}
$$

Traffic multiplier for slot/base profile and traffic level $\lambda$:

$$
M = 1 + (M_{base} - 1) \times \lambda
$$

where $\lambda \in [0, 3]$ and multiplier is clamped.

### 9.6 Emergency adjustment
Emergency mode forces traffic-style objective and scales effective speed by highway-type emergency multipliers.

---

## 10. Real-Time Integration

### 10.1 Weather source
Provider: Open-Meteo
- no API key required
- uses route midpoint coordinates
- captures temperature, precipitation, wind, weather code, day/night

Weather penalty factor:
- starts at 1.0
- increases with precipitation, wind, and severe weather codes
- clamped to range [1.0, 1.75]

### 10.2 Traffic source
Provider: TomTom Flow API
- optional
- requires API key
- uses midpoint coordinates

Result is converted to a traffic_level_override in [0.0, 3.0], used to override configured traffic level when greater.

### 10.3 Context object
Routing consumes a normalized context with fields:
- enabled
- weather_penalty_factor
- traffic_level_override
- weather payload
- live_traffic payload
- notes

---

## 11. Streamlit Application Workflow

### 11.1 Input model
Required user flow:
1. Choose city from predefined list.
2. Load area suggestions for that city.
3. Choose from-area and to-area from suggestion dropdowns.

Advanced options include:
- vehicle profile
- algorithm
- alternatives count
- optimization objective
- speed, time slot, traffic level
- offline mode and cache use
- graph file selection
- live context toggles and TomTom key

### 11.2 Validation behavior
- city must be selected
- area suggestions must be available
- source and destination areas must be selected from valid suggestions
- source and destination cannot be same
- geocoding failures include close-match hints

### 11.3 Output behavior
- map rendered in-page from saved HTML
- summary metrics and route comparison table
- snap diagnostics, realtime context, planning insights
- last search JSON snapshot shown

---

## 12. Command-Line Interface Reference

### 12.1 Base command

python main.py [options]

### 12.2 Key options

Input and profile:
- --place
- --start lat,lon
- --end lat,lon
- --profile scooter|bike|drive

Routing:
- --algorithm dijkstra|astar
- --alternatives N
- --speed KMH
- --weight-mode distance|traffic
- --time-slot early_morning|morning_peak|midday|evening_peak|night
- --traffic-level 0.0 to 3.0

Use-case:
- --use-case standard|delivery|emergency
- --stops lat,lon;lat,lon
- --return-to-start

Data/source behavior:
- --offline
- --graph-file path.graphml
- --no-cache

Real-time:
- --realtime
- --weather-live
- --traffic-live
- --traffic-api-key KEY

Output:
- --output output/optimized_route.html

### 12.3 Example commands

Default run:
python main.py

Traffic-aware run:
python main.py --weight-mode traffic --time-slot evening_peak --traffic-level 1.4

Offline deterministic run:
python main.py --offline --graph-file "data/chennai-tamil-nadu-india-scooter.graphml"

Delivery run:
python main.py --use-case delivery --stops "13.055,80.244;13.048,80.251" --return-to-start

Emergency run with realtime context:
python main.py --use-case emergency --realtime --traffic-live --traffic-api-key YOUR_KEY

---

## 13. Inputs, Outputs, and Artifacts

### 13.1 Inputs
- city/place
- start and end coordinates or areas (Streamlit)
- objective and algorithm settings
- optional realtime API key

### 13.2 Runtime artifacts
- data/*.graphml: cached road graphs
- cache/*.json: provider cache payloads
- output/*.html: generated route maps

### 13.3 Typical output files
- output/optimized_route.html
- output/streamlit_route.html
- output/smoke_route.html
- output/smoke_delivery.html
- output/smoke_emergency.html
- output/smoke_realtime.html

---

## 14. Error Handling and Edge Cases

Handled cases:
- invalid coordinate parsing in CLI
- no local graph in offline mode
- no path between points
- geocoding failures in Streamlit
- provider/API failures in realtime integration
- nearest-node fallback when scikit-learn is unavailable

Behavioral fallback examples:
- realtime disabled or failed provider calls fall back to neutral context
- distance/ETA fallback estimation when travel-time sum is unavailable

---

## 15. Testing and Validation Strategy

Current state:
- manual smoke-output files are present in output/
- no dedicated automated test suite in repository

Recommended manual validation matrix:
1. standard distance mode (dijkstra)
2. standard distance mode (astar)
3. traffic mode without realtime
4. offline mode with explicit graph file
5. delivery mode with 2+ stops
6. emergency mode with realtime weather
7. streamlit input validation paths

Suggested future automated coverage:
- parser and validation unit tests
- deterministic route regression tests on fixed graph
- realtime context mocking tests
- analytics output schema tests

---

## 16. Performance Considerations

- graph download is expensive for large places; caching is enabled by default
- alternatives generation can increase compute cost
- realtime API calls add latency and may fail due to connectivity
- large hotspot/heatmap datasets can increase map render size

Optimization tips:
- use offline mode with cached graph for demos
- limit alternatives during live presentation
- keep city scope moderate for faster execution

---

## 17. Security and Privacy Notes

- TomTom API key is entered via UI/CLI and should not be committed to git
- generated map outputs may contain sensitive route points if using real user locations
- no authentication/access control layer is implemented in this project

---

## 18. Limitations

- traffic model is partly synthetic unless live TomTom override is enabled
- ETA depends on inferred default speeds where maxspeed is absent
- delivery strategy is greedy nearest-next, not full VRP optimization
- no persistent database/history tracking
- no CI test pipeline included currently

---

## 19. Future Enhancements

- exact VRP solver for delivery with constraints
- stronger emergency routing policy with turn restrictions/priorities
- richer geocoding confidence and ambiguity handling
- persistence layer for route runs and analytics trends
- unit and integration test suite with CI
- packaged deployment (Docker + cloud runtime)
- role-based access and API-first architecture

---

## 20. Setup and Run Guide

### 20.1 Environment setup

Windows PowerShell:
1. python -m venv venv
2. .\venv\Scripts\Activate.ps1
3. pip install -r requirements.txt

### 20.2 Run CLI

python main.py

### 20.3 Run Streamlit app

python -m streamlit run streamlit_app.py

### 20.4 Offline demo run

python main.py --offline --graph-file "data/chennai-tamil-nadu-india-scooter.graphml"

---

## 21. Viva-Ready Quick Explanation

One-minute summary:
- The project extracts a real city road network from OpenStreetMap.
- It models roads as a weighted graph and computes optimal paths with Dijkstra/A*.
- It supports traffic-aware weighting, alternatives, and live weather/traffic context.
- It renders interactive maps and planning analytics for practical interpretation.

Common differentiators:
- explainable routing (not a black box)
- offline reproducibility for demos
- both user-friendly UI and engineering-oriented CLI

---

## 22. Maintainer Notes

If you extend this project:
- keep src modules independent and testable
- add new weight models inside calculate_route.py to centralize routing logic
- preserve output schema keys used by Streamlit renderer
- document any new CLI flags in README.md and this file

---

## 23. Appendix: Important Data Schemas

### 23.1 Route result (high level)

- origin_node: int
- destination_node: int
- routes: list[list[int]]
- summaries: list[route_summary]
- routing: object
- realtime: object
- snap: object
- planning: object (added by caller)

### 23.2 Route summary item

- route_index
- route_label (optional)
- distance_m
- distance_km
- eta_min
- traffic_delta_min
- avg_speed_kmph
- node_count

### 23.3 Planning object

- overlap_pct
- highway_mix (list)
- hotspots (list)
- recommendations (list)
- heatmap_points (list) [attached by caller]

---

## 24. License and Attribution

Road and map data are sourced from OpenStreetMap contributors (ODbL).

If this project is submitted academically, include:
- repository link
- dependency list
- data attribution statement
- your own implementation and architecture explanation
