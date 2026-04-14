# Urban Route Optimizer

Graph-based path planning for urban two-wheelers using OpenStreetMap data.

This project calculates realistic routes between two coordinates, supports Dijkstra and A* search, shows alternative paths, estimates travel time, and exports a polished interactive HTML map suitable for demo presentations and college project reviews.

## Project Highlights

- Real city street network extraction from OpenStreetMap.
- Two-wheeler oriented route profile for scooters (filters unsuitable highway types).
- Dijkstra and A* shortest-path algorithms.
- Traffic-aware travel-time routing with configurable time slots and congestion level.
- Alternative route generation using k-shortest simple paths.
- Offline-only routing using cached or explicitly selected local GraphML files.
- Real-time context integration:
	- live weather-aware route weighting (Open-Meteo)
	- optional live traffic override (TomTom Flow API)
- Specialized use cases:
	- emergency response routing priority mode
	- multi-stop delivery optimization workflow
- Urban planning analytics:
	- route-usage heatmap layer
	- hotspot segment detection
	- infrastructure recommendation hints
- Route metrics: distance, ETA, node count, and coordinate snap distance diagnostics.
- Local graph caching for faster repeated runs.
- Presentation-ready Folium map output with:
  - animated primary route
  - alternative route layers
  - fullscreen, minimap, and distance measurement tools
  - styled route summary panel

## Tech Stack

- Python 3.9+
- osmnx
- networkx
- folium
- pandas
- geopandas
- pyproj
- streamlit

## Installation

1. Clone the repository:

	git clone https://github.com/MITHUNtech11/urban-route-optimizer.git

2. Move into the project folder:

	cd urban-route-optimizer

3. Create and activate a virtual environment:

	Windows (PowerShell):
	python -m venv venv
	.\venv\Scripts\Activate.ps1

	macOS/Linux:
	python -m venv venv
	source venv/bin/activate

4. Install dependencies:

	pip install -r requirements.txt

Note: osmnx/geopandas may require platform geospatial binaries. If installation fails on your system, use conda for a smoother geospatial setup.

## Quick Start

Run with defaults (Chennai sample points):

python main.py

Run a custom route:

python main.py --place "Bangalore, Karnataka, India" --start "12.9716,77.5946" --end "12.9689,77.5941"

Use A* with extra alternatives:

python main.py --algorithm astar --alternatives 3 --speed 30

Use traffic-aware travel-time routing:

python main.py --weight-mode traffic --time-slot evening_peak --traffic-level 1.4

Run in offline-only mode using local graph cache:

python main.py --offline --graph-file "data/chennai-tamil-nadu-india-scooter.graphml"

Run emergency routing with real-time context:

python main.py --use-case emergency --realtime --traffic-live --traffic-api-key YOUR_TOMTOM_KEY

Run delivery optimization with multiple stops:

python main.py --use-case delivery --stops "13.055,80.244;13.048,80.251" --return-to-start

Generate bike network output:

python main.py --profile bike --place "Coimbatore, Tamil Nadu, India" --start "11.0168,76.9558" --end "11.0100,76.9700"

Disable cache and force fresh download:

python main.py --no-cache

Launch the interactive Streamlit dashboard:

python -m streamlit run streamlit_app.py

The generated map is saved to:

output/optimized_route.html

## CLI Options

- --place: city/area name (default: Chennai, Tamil Nadu, India)
- --start: start coordinate as lat,lon
- --end: end coordinate as lat,lon
- --profile: scooter, bike, or drive
- --algorithm: dijkstra or astar
- --alternatives: number of additional route options
- --speed: average speed in km/h (for ETA)
- --weight-mode: distance or traffic
- --time-slot: traffic profile (early_morning, morning_peak, midday, evening_peak, night)
- --traffic-level: congestion intensity scale 0.0 to 3.0
- --use-case: standard, delivery, or emergency
- --stops: semicolon-separated delivery stops (lat,lon;lat,lon)
- --return-to-start: in delivery mode, return to start after final stop
- --offline: force offline mode (no OSM download)
- --graph-file: local GraphML path for offline/deterministic runs
- --realtime: enable live context integration
- --weather-live: weather-aware weighting (also enabled by default with --realtime)
- --traffic-live: enable TomTom live traffic override
- --traffic-api-key: TomTom API key used with --traffic-live
- --no-cache: skip graph cache and refetch from OSM
- --output: output HTML path

## Project Structure

urban-route-optimizer/
|- data/                    # Cached graph files
|- notebooks/               # Experimental notebooks
|- output/                  # Generated HTML outputs
|- src/
|  |- __init__.py
|  |- build_graph.py        # Graph download, caching, and profile filtering
|  |- calculate_route.py    # Routing algorithms, alternatives, metrics, traffic weighting
|  |- visualize.py          # Interactive map generation
|- main.py                  # CLI entrypoint
|- streamlit_app.py         # Interactive Streamlit UI
|- docs/PROJECT_REPORT_AND_VIVA.md
|- requirements.txt
|- README.md

## Suggested Demo Flow (For Viva/Presentation)

1. Show terminal run with custom city and points.
2. Explain selected algorithm (Dijkstra or A*).
3. Open HTML map and toggle route layers.
4. Highlight route panel metrics (distance and ETA).
5. Explain two-wheeler filtering and graph caching advantage.

## Future Enhancements

- Public transport and multimodal interchange support.
- Fleet-scale delivery VRP optimization (capacity and time windows).
- Exportable planning reports (CSV/PDF) for city agencies.
- Carbon-emission optimization and sustainability scoring.