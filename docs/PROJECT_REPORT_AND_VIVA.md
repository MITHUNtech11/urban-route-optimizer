# Urban Route Optimizer
## Final Project Report + Viva Script

## Student Details
- Name: __________________________
- Register No: ____________________
- Department: _____________________
- College: ________________________
- Guide: __________________________
- Academic Year: __________________

## 1. Abstract
Urban commuters often choose routes based on habit, not optimization. In dense cities, this can increase travel time, fuel usage, and stress due to one-way roads and congestion corridors. The Urban Route Optimizer is a Python-based geospatial decision support system that extracts real road networks from OpenStreetMap, models them as weighted graphs, and computes optimized routes between user-selected points.

The project supports two optimization objectives:
1. Distance-based shortest route.
2. Traffic-aware route based on estimated travel time.

The system includes a command-line workflow for reproducible outputs and a Streamlit dashboard for interactive demonstration. Generated outputs include a map with recommended and alternative routes, route metrics (distance, ETA, node count), and snapping diagnostics.

## 2. Problem Statement
Many urban navigation decisions are suboptimal because users do not explicitly evaluate graph-level path alternatives. Existing map apps are powerful but closed systems with limited transparency in routing logic for academic demonstration. This project addresses the need for an open, explainable route optimization workflow suitable for educational use.

## 3. Objectives
- Build an urban road graph from OpenStreetMap data.
- Filter road segments to support two-wheeler-friendly routing.
- Compute shortest paths using Dijkstra and A*.
- Generate k-shortest alternatives for comparison.
- Add traffic-aware travel-time weighting using time slots and congestion intensity.
- Visualize outputs in an interactive map.
- Provide both CLI and dashboard interfaces for viva/demo use.

## 4. System Architecture

Input Layer:
- Place name (city/region)
- Start and end coordinates (lat, lon)
- Routing profile and algorithm settings

Processing Layer:
- Graph extraction and caching
- Road filtering for profile suitability
- Cost function construction (distance or traffic-aware time)
- Path search (Dijkstra/A*)
- Alternative route generation

Output Layer:
- Route summary table
- Interactive HTML map
- CLI logs and diagnostics
- Streamlit dashboard

ASCII flow:

User Input
  -> Build Graph (OSMnx)
  -> Filter/Cache Graph
  -> Create Edge Weights (distance or traffic-aware)
  -> Run Path Algorithm (Dijkstra/A*)
  -> Generate Alternatives
  -> Compute Metrics
  -> Render Map + Summary

## 5. Technologies Used
- Python 3.13 (venv)
- OSMnx (network extraction)
- NetworkX (graph algorithms)
- Folium + Leaflet plugins (interactive map)
- Streamlit (interactive dashboard)
- Pandas/GeoPandas (data support)
- PyProj (coordinate transformation fallback)

## 6. Data Source
OpenStreetMap (OSM) data fetched dynamically by place name. The graph is cached locally in GraphML format under data/ for faster repeated execution.

## 7. Methodology

### 7.1 Graph Construction
- Query OSM by place.
- Build directed MultiDiGraph.
- Use profile-specific extraction and filtering:
  - scooter profile removes unsuitable highway classes like motorway, trunk, footway, cycleway, etc.

### 7.2 Coordinate to Graph Mapping
- Input coordinates are snapped to nearest valid road-network nodes.
- Fallback logic handles environments where unprojected nearest-node search may require optional dependencies.

### 7.3 Routing Algorithms
- Dijkstra: exact shortest path by chosen edge weight.
- A*: informed shortest path with geodesic heuristic.

### 7.4 Alternative Route Generation
- Uses k-shortest simple path search over weighted directed graph.
- Provides route comparison for decision transparency.

### 7.5 Traffic-Aware Weight Model
Each edge has:
- length_m (meters)
- base_speed_kmph (from maxspeed or highway defaults)
- traffic_multiplier (time-slot dependent)
- travel_time_sec = length_m / effective_speed

For traffic mode:
- effective_speed = base_speed / traffic_multiplier
- traffic_multiplier is scaled by user-selected traffic level (0.0 to 3.0)

For distance mode:
- optimization weight remains edge length.
- ETA still computed for user readability.

### 7.6 Visualization
The final map includes:
- recommended route (animated)
- alternative routes (layer toggles)
- start/end markers
- route info panel (distance, ETA, snap values)
- fullscreen, minimap, and measurement tools

## 8. Key Implementation Files
- main.py: CLI argument parsing, execution flow, summary output.
- src/build_graph.py: graph creation, caching, and scooter filtering.
- src/calculate_route.py: path algorithms, traffic weighting, alternatives, metrics.
- src/visualize.py: interactive map rendering.
- streamlit_app.py: dashboard UI.

## 9. Execution Commands

### 9.1 CLI (distance mode)
python main.py --place "Chennai, Tamil Nadu, India" --start "13.065,80.237" --end "13.045,80.260"

### 9.2 CLI (traffic mode)
python main.py --weight-mode traffic --time-slot evening_peak --traffic-level 1.4 --algorithm astar

### 9.3 Streamlit Dashboard
python -m streamlit run streamlit_app.py

## 10. Sample Observations
Example run (Chennai test points):
- Recommended distance: approximately 4.54 km
- ETA: approximately 9.7 minutes
- Start snap: approximately 35 m
- End snap: approximately 24 m
- Alternatives generated: yes

Interpretation:
- Primary route and alternatives are close in distance.
- Traffic mode can shift ranking if congestion multipliers affect specific corridors.

## 11. Testing and Validation
- CLI parser validation passed.
- Source compilation checks passed.
- End-to-end execution validated for:
  - Dijkstra distance mode
  - A* distance mode
  - traffic-aware mode
- HTML output generated successfully.

## 12. Limitations
- Traffic model is synthetic and profile-based; it is not tied to live traffic APIs.
- Travel-time estimates depend on inferred speeds for roads without explicit maxspeed.
- Very large regions may require significant memory and processing time.

## 13. Future Enhancements
- Integrate live traffic API to update congestion multipliers dynamically.
- Add fuel/cost/emission estimation.
- Add multi-stop route optimization.
- Add turn-by-turn instruction extraction.
- Add persistent run history and comparison analytics.

## 14. Conclusion
The Urban Route Optimizer successfully demonstrates graph-theoretic route planning over real geospatial road networks and extends classic shortest-path logic with a configurable traffic-aware model. The project fulfills academic goals by combining algorithmic rigor, explainability, visual clarity, and practical usability.

## 15. Viva Script (5-7 Minute Delivery)

Opening:
"Good morning. My project is Urban Route Optimizer. It uses graph theory on OpenStreetMap roads to compute optimized scooter routes between two user-defined coordinates."

Problem:
"In cities, route choice is often based on habit. This project shows how algorithmic route selection can reduce travel inefficiency and improve transparency in navigation decisions."

Approach:
"I extract the city road network as a directed graph where intersections are nodes and roads are edges. Then I run Dijkstra or A* on edge weights. I support two modes: pure distance and traffic-aware travel time."

Traffic Logic:
"In traffic mode, each edge gets an estimated travel-time weight using road class, speed defaults, selected time slot, and user-defined congestion intensity. The optimizer then minimizes travel time instead of distance."

Outputs:
"The system returns one recommended route plus alternatives, and renders an interactive map with route layers, ETA, distance, and snap diagnostics. I implemented both CLI and Streamlit UI for demonstration."

Result:
"For Chennai sample points, the system generated a 4.54 km route in about 9.7 minutes with alternatives."

Closing:
"This project combines geospatial data, graph algorithms, and interactive visualization into a reproducible optimization workflow suitable for real-world extension."

## 16. Likely Viva Questions With Answers

Q1. Why did you choose graph representation?
A1. Road networks naturally map to graphs: nodes are junctions and edges are road segments. Graph algorithms give mathematically optimal paths under defined weights.

Q2. Difference between Dijkstra and A* in your project?
A2. Dijkstra explores based on current shortest known distance. A* uses a heuristic toward destination and can reduce search effort while preserving optimality when heuristic is admissible.

Q3. What is your heuristic in A*?
A3. Great-circle distance between current node and destination node. For traffic mode, I convert that to optimistic time using a high heuristic speed.

Q4. How is traffic modeled without live API?
A4. I assign congestion multipliers by road class and time-slot profile (morning/evening peak, etc.) and scale by user traffic intensity. This simulates route shifts under congestion.

Q5. Why alternatives if shortest path already exists?
A5. Alternatives support decision flexibility and provide comparative insight when primary route conditions change or user preferences differ.

Q6. Why use OSMnx?
A6. It simplifies real-world road network extraction from OpenStreetMap and integrates well with NetworkX.

Q7. What is snapping and why report it?
A7. Input coordinates may not lie exactly on road nodes. Snapping maps them to nearest nodes. Reporting snap distance helps validate input quality.

Q8. Major challenge faced?
A8. Nearest-node lookup dependency behavior on unprojected graphs. I solved it with a projected-graph fallback for robust execution.

Q9. Is this production-ready traffic prediction?
A9. Not yet. It is a transparent academic model. Production use would require live traffic ingestion and calibration.

Q10. How can this be improved further?
A10. Add live traffic APIs, multi-stop optimization, fuel/emission analytics, and richer UI filters.

## 17. Demo Checklist (Before Presentation)
- Activate venv.
- Run one CLI command in distance mode.
- Run one CLI command in traffic mode.
- Launch Streamlit app.
- Show route layers and metrics.
- Keep output/optimized_route.html ready as backup.

## 18. Reference Note
All road geometry and metadata are sourced from OpenStreetMap contributors under ODbL.
