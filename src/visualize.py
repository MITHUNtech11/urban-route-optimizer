"""Interactive map rendering for route outputs."""

from pathlib import Path

import folium
from folium import plugins
import osmnx as ox


def _best_edge_data(graph, u, v):
    edge_data = graph.get_edge_data(u, v)
    if not edge_data:
        return None

    if "length" in edge_data:
        return edge_data

    return min(edge_data.values(), key=lambda data: float(data.get("length", 0.0)))


def _route_to_coordinates(graph, path):
    if not path or len(path) < 2:
        return []

    route_coords = []
    for u, v in zip(path, path[1:]):
        edge_data = _best_edge_data(graph, u, v)
        if not edge_data:
            continue

        geometry = edge_data.get("geometry")
        if geometry is not None:
            xs, ys = geometry.xy
            segment = list(zip(ys, xs))
        else:
            segment = [
                (graph.nodes[u]["y"], graph.nodes[u]["x"]),
                (graph.nodes[v]["y"], graph.nodes[v]["x"]),
            ]

        if route_coords and segment and route_coords[-1] == segment[0]:
            route_coords.extend(segment[1:])
        else:
            route_coords.extend(segment)

    return route_coords


def _panel_html(place_name, route_summaries, snap_info):
    rows = []
    for summary in route_summaries:
        label = summary.get("route_label")
        if not label:
            label = (
                "Recommended"
                if summary.get("route_index") == 1
                else f"Alternative {summary.get('route_index', 1) - 1}"
            )
        rows.append(
            "<tr>"
            f"<td>{label}</td>"
            f"<td>{summary.get('distance_km', 0.0):.2f} km</td>"
            f"<td>{summary.get('eta_min', 0.0):.1f} min</td>"
            "</tr>"
        )

    snap_html = ""
    if snap_info:
        snap_html = (
            f"<div class='snap'>Start snap: {snap_info.get('start_to_node_m', 0.0):.0f} m</div>"
            f"<div class='snap'>End snap: {snap_info.get('end_to_node_m', 0.0):.0f} m</div>"
        )

    return f"""
    <style>
      .route-panel {{
        position: fixed;
        right: 16px;
        bottom: 22px;
        width: 330px;
        z-index: 9999;
        background: linear-gradient(165deg, #102a43 0%, #243b53 55%, #334e68 100%);
        color: #f0f4f8;
        border-radius: 14px;
        box-shadow: 0 16px 34px rgba(16, 42, 67, 0.38);
        overflow: hidden;
        font-family: 'Trebuchet MS', 'Segoe UI', sans-serif;
      }}
      .route-panel .head {{
        padding: 12px 16px;
        background: rgba(255, 255, 255, 0.08);
        border-bottom: 1px solid rgba(255, 255, 255, 0.2);
      }}
      .route-panel .title {{
        font-size: 15px;
        font-weight: 700;
        margin: 0;
      }}
      .route-panel .place {{
        font-size: 12px;
        margin-top: 4px;
        color: #d9e2ec;
      }}
      .route-panel .body {{
        padding: 10px 14px 14px;
      }}
      .route-panel table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 12px;
      }}
      .route-panel th, .route-panel td {{
        text-align: left;
        padding: 7px 4px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.14);
      }}
      .route-panel th {{
        color: #bcccdc;
        font-weight: 600;
      }}
      .route-panel .snap {{
        font-size: 12px;
        margin-top: 8px;
        color: #d9e2ec;
      }}
    </style>
    <div class="route-panel">
      <div class="head">
        <p class="title">Urban Route Optimizer</p>
        <div class="place">{place_name or 'Selected Area'}</div>
      </div>
      <div class="body">
        <table>
          <thead>
            <tr>
              <th>Route</th>
              <th>Distance</th>
              <th>ETA</th>
            </tr>
          </thead>
          <tbody>
            {''.join(rows)}
          </tbody>
        </table>
        {snap_html}
      </div>
    </div>
    """


def _add_planning_heatmap(route_map, heatmap_points):
    if not heatmap_points:
        return

    heat_layer = folium.FeatureGroup(name="Planning Heatmap", show=False)
    plugins.HeatMap(
        heatmap_points,
        radius=18,
        blur=14,
        min_opacity=0.25,
        max_zoom=17,
    ).add_to(heat_layer)
    heat_layer.add_to(route_map)


def _add_hotspot_markers(route_map, hotspots):
    if not hotspots:
        return

    hotspot_layer = folium.FeatureGroup(name="Hotspot Segments", show=False)
    for index, hotspot in enumerate(hotspots, start=1):
        folium.CircleMarker(
            location=[hotspot.get("from_lat", 0.0), hotspot.get("from_lon", 0.0)],
            radius=6,
            color="#e63946",
            fill=True,
            fill_color="#e63946",
            fill_opacity=0.85,
            tooltip=f"Hotspot {index}",
            popup=(
                f"Uses: {hotspot.get('uses', 0)}<br>"
                f"Road type: {hotspot.get('highway', 'unknown')}<br>"
                f"Length: {hotspot.get('length_m', 0.0):.0f} m"
            ),
        ).add_to(hotspot_layer)

    hotspot_layer.add_to(route_map)


def visualize_route(
    graph,
    routes,
    output_file="output/optimized_route.html",
    distance=0,
    route_summaries=None,
    place_name="",
    snap_info=None,
    map_object=None,
    heatmap_points=None,
    planning_hotspots=None,
):
    """Visualize one or more routes on an interactive Folium map."""
    del distance  # Backward-compatible parameter kept intentionally.

    try:
        if not routes:
            print("Error: no route data to visualize")
            return None

        if routes and not isinstance(routes[0], (list, tuple)):
            routes = [routes]

        route_coordinates = [_route_to_coordinates(graph, route) for route in routes]
        route_coordinates = [coords for coords in route_coordinates if coords]
        if not route_coordinates:
            print("Error: no path coordinates to visualize")
            return None

        if map_object is None:
            primary_coords = route_coordinates[0]
            center_lat = sum(coord[0] for coord in primary_coords) / len(primary_coords)
            center_lon = sum(coord[1] for coord in primary_coords) / len(primary_coords)

            route_map = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=14,
                tiles=None,
                control_scale=True,
            )
            folium.TileLayer("CartoDB positron", name="Light").add_to(route_map)
            folium.TileLayer("OpenStreetMap", name="Street").add_to(route_map)
            folium.TileLayer("CartoDB voyager", name="Voyager").add_to(route_map)
        else:
            route_map = map_object

        recommended_layer = folium.FeatureGroup(name="Recommended Route", show=True)
        alternatives_layer = folium.FeatureGroup(name="Alternative Routes", show=True)
        alt_colors = ["#ff7f50", "#6a4c93", "#2f9e44", "#bc5090", "#f4a261"]

        for idx, coords in enumerate(route_coordinates, start=1):
            if idx == 1:
                folium.PolyLine(
                    coords,
                    color="#0b84f3",
                    weight=7,
                    opacity=0.9,
                    tooltip="Recommended route",
                ).add_to(recommended_layer)

                plugins.AntPath(
                    locations=coords,
                    color="#4cc9f0",
                    pulse_color="#90e0ef",
                    delay=900,
                    weight=5,
                    dash_array=[18, 22],
                ).add_to(recommended_layer)
            else:
                color = alt_colors[(idx - 2) % len(alt_colors)]
                route_name = f"Alternative route {idx - 1}"
                if route_summaries and idx - 1 < len(route_summaries):
                    route_name = route_summaries[idx - 1].get("route_label", route_name)

                folium.PolyLine(
                    coords,
                    color=color,
                    weight=5,
                    opacity=0.78,
                    dash_array="10, 12",
                    tooltip=route_name,
                ).add_to(alternatives_layer)

        start_location = route_coordinates[0][0]
        end_location = route_coordinates[-1][-1]

        folium.Marker(
            location=start_location,
            tooltip="Start",
            popup="Start point",
            icon=folium.Icon(color="green", icon="play"),
        ).add_to(route_map)

        folium.Marker(
            location=end_location,
            tooltip="Destination",
            popup="Destination point",
            icon=folium.Icon(color="red", icon="flag"),
        ).add_to(route_map)

        recommended_layer.add_to(route_map)
        if len(route_coordinates) > 1:
            alternatives_layer.add_to(route_map)

        plugins.Fullscreen(
            position="topright",
            title="Expand",
            title_cancel="Exit",
            force_separate_button=True,
        ).add_to(route_map)

        plugins.MiniMap(toggle_display=True, position="bottomleft", minimized=True).add_to(route_map)

        _add_planning_heatmap(route_map, heatmap_points)
        _add_hotspot_markers(route_map, planning_hotspots)

        if route_summaries:
            panel_html = _panel_html(place_name, route_summaries, snap_info)
            route_map.get_root().html.add_child(folium.Element(panel_html))

        folium.LayerControl(collapsed=False).add_to(route_map)

        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            route_map.save(str(output_path))
            print(f"Saved map to {output_path.resolve()}")

        return route_map

    except Exception as exc:
        print(f"Error visualizing route: {exc}")
        return None


def plot_graph_folium(graph, route_result=None, **kwargs):
    """Plot graph and optional routes on an OSMnx Folium map."""
    if route_result and route_result.get("routes"):
        route_coords = _route_to_coordinates(graph, route_result["routes"][0])
        if route_coords:
            kwargs.setdefault("location", route_coords[len(route_coords) // 2])
            kwargs.setdefault("zoom_start", 14)

    route_map = ox.plot_graph_folium(graph, **kwargs)

    if route_result:
        planning = route_result.get("planning", {})
        route_map = visualize_route(
            graph=graph,
            routes=route_result.get("routes", []),
            output_file=None,
            route_summaries=route_result.get("summaries"),
            place_name=route_result.get("place_name", ""),
            snap_info=route_result.get("snap"),
            map_object=route_map,
            heatmap_points=planning.get("heatmap_points"),
            planning_hotspots=planning.get("hotspots"),
        )

    return route_map
