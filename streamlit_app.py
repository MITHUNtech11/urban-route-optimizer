#!/usr/bin/env python3
"""Streamlit front-end for the Urban Route Optimizer project."""

from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


ROOT_DIR = Path(__file__).resolve().parent

from src.analytics import build_route_heatmap_points, generate_urban_insights
from src.build_graph import build_graph, list_cached_graphs
from src.calculate_route import calculate_routes
from src.realtime import build_realtime_context
from src.specialized import optimize_delivery_route
from src.visualize import visualize_route


TIME_SLOT_OPTIONS = [
    "early_morning",
    "morning_peak",
    "midday",
    "evening_peak",
    "night",
]

USE_CASE_OPTIONS = ["standard", "delivery", "emergency"]


def parse_coordinate_pair(value):
    try:
        lat_str, lon_str = [part.strip() for part in value.split(",", maxsplit=1)]
        return float(lat_str), float(lon_str)
    except ValueError as exc:
        raise ValueError(
            f"Invalid coordinate '{value}'. Use lat,lon format like 13.065,80.237"
        ) from exc


def parse_stop_points(value):
    stop_points = []
    for line in (value or "").splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        stop_points.append(parse_coordinate_pair(cleaned))
    return stop_points


def format_point(point):
    return f"{float(point[0]):.5f},{float(point[1]):.5f}"


@st.cache_resource(show_spinner=False)
def load_cached_graph(place_name, profile, use_cache, offline, graph_file):
    return build_graph(
        place_name=place_name,
        profile=profile,
        use_cache=use_cache,
        cache_dir="data",
        offline=offline,
        graph_file=graph_file,
    )


def render_page_chrome():
    st.set_page_config(
        page_title="Urban Route Optimizer",
        page_icon="U",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800&display=swap');

          html, body, [class*="css"] {
            font-family: 'Poppins', sans-serif;
          }

          .hero {
            border-radius: 18px;
            background: linear-gradient(120deg, #264653 0%, #2a9d8f 100%);
            color: #ffffff;
            padding: 20px 24px;
            margin-bottom: 16px;
            box-shadow: 0 14px 30px rgba(38, 70, 83, 0.25);
          }

          .hero h1 {
            font-family: 'Poppins', sans-serif;
            font-weight: 800;
            font-size: 2.0rem;
            margin: 0;
            letter-spacing: 0.4px;
          }

          .hero p {
            margin-top: 8px;
            margin-bottom: 0;
            font-size: 1.0rem;
            opacity: 0.9;
          }

          .note {
            background: #f0f8ff;
            border: 1px solid #e0f2fe;
            border-left: 6px solid #2a9d8f;
            border-radius: 10px;
            padding: 10px 12px;
            margin-bottom: 10px;
            color: #0f172a;
          }
        </style>

        <div class="hero">
          <h1>Urban Route Optimizer Dashboard</h1>
          <p>Offline-ready routes, specialized delivery and emergency workflows, live context integration, and urban planning analytics.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_sidebar():
    with st.sidebar:
        st.header("Route Inputs")
        place_name = st.text_input(
            "Place",
            value="Chennai, Tamil Nadu, India",
            help="Use a city or region format recognized by OpenStreetMap.",
        )
        start_raw = st.text_input("Start (lat,lon)", value="13.065,80.237")
        end_raw = st.text_input("End (lat,lon)", value="13.045,80.260")

        st.divider()
        use_case = st.selectbox("Use case", USE_CASE_OPTIONS, index=0)
        if use_case == "delivery":
            stops_raw = st.text_area(
                "Delivery stops (one per line as lat,lon)",
                value="13.055,80.244\n13.048,80.251",
                height=100,
            )
            return_to_start = st.checkbox("Return to start after deliveries", value=False)
        else:
            stops_raw = ""
            return_to_start = False

        st.divider()
        profile = st.selectbox("Profile", ["scooter", "bike", "drive"], index=0)
        algorithm = st.selectbox("Algorithm", ["dijkstra", "astar"], index=0)
        alternatives = st.slider("Alternative routes", min_value=0, max_value=3, value=1)
        avg_speed = st.slider(
            "Average speed (km/h)",
            min_value=10.0,
            max_value=60.0,
            value=28.0,
            step=1.0,
        )

        st.divider()
        weight_mode = st.selectbox("Optimization mode", ["distance", "traffic"], index=1)
        if weight_mode == "traffic":
            time_slot = st.selectbox("Traffic time slot", TIME_SLOT_OPTIONS, index=2)
            traffic_level = st.slider(
                "Traffic intensity",
                min_value=0.0,
                max_value=3.0,
                value=1.0,
                step=0.05,
            )
        else:
            time_slot = "midday"
            traffic_level = 1.0

        st.divider()
        st.subheader("Real-Time Integration")
        realtime_enabled = st.checkbox("Enable live context", value=False)
        weather_enabled = st.checkbox("Weather-aware weighting", value=True)
        traffic_live_enabled = st.checkbox("Live traffic override (TomTom)", value=False)
        traffic_api_key = st.text_input(
            "TomTom API key",
            value="",
            type="password",
            help="Optional. Required only for live traffic override.",
        )

        st.divider()
        st.subheader("Offline")
        offline_mode = st.checkbox("Offline-only routing", value=False)
        use_cache = st.checkbox("Use graph cache", value=True)

        available_graphs = [str(path) for path in list_cached_graphs(cache_dir="data", profile=profile)]
        graph_option_label = ["Auto-select by place/profile"] + [Path(path).name for path in available_graphs]
        graph_option_values = [""] + available_graphs

        graph_file = st.selectbox(
            "Offline graph source",
            options=list(range(len(graph_option_values))),
            format_func=lambda idx: graph_option_label[idx],
            index=0,
            help="Pick a local .graphml cache file for fully offline execution.",
        )

        st.divider()
        output_file = st.text_input("Output HTML", value="output/streamlit_route.html")

        optimize_clicked = st.button("Optimize Route", use_container_width=True, type="primary")

    return {
        "place_name": place_name,
        "start_raw": start_raw,
        "end_raw": end_raw,
        "profile": profile,
        "use_case": use_case,
        "stops_raw": stops_raw,
        "return_to_start": return_to_start,
        "algorithm": algorithm,
        "alternatives": alternatives,
        "avg_speed": avg_speed,
        "weight_mode": weight_mode,
        "time_slot": time_slot,
        "traffic_level": traffic_level,
        "realtime_enabled": realtime_enabled,
        "weather_enabled": weather_enabled,
        "traffic_live_enabled": traffic_live_enabled,
        "traffic_api_key": traffic_api_key,
        "offline_mode": offline_mode,
        "use_cache": use_cache,
        "graph_file": graph_option_values[graph_file] or None,
        "output_file": output_file,
        "optimize_clicked": optimize_clicked,
    }


def render_realtime_context(realtime):
    if not realtime or not realtime.get("enabled"):
        return

    st.subheader("Real-Time Context")
    metric_cols = st.columns(3)
    metric_cols[0].metric("Weather slowdown factor", f"x{realtime.get('weather_penalty_factor', 1.0):.2f}")

    override = realtime.get("traffic_level_override")
    if override is None:
        metric_cols[1].metric("Live traffic level", "Not active")
    else:
        metric_cols[1].metric("Live traffic level", f"{float(override):.2f} / 3.0")

    metric_cols[2].metric("Context notes", f"{len(realtime.get('notes', []))}")

    weather = realtime.get("weather") or {}
    if weather.get("ok"):
        st.caption(
            "Weather snapshot: "
            f"{weather.get('temperature_c', 0.0):.1f} C, "
            f"precipitation {weather.get('precipitation_mm', 0.0):.2f} mm, "
            f"wind {weather.get('wind_kmph', 0.0):.1f} km/h."
        )

    traffic = realtime.get("live_traffic") or {}
    if traffic.get("ok"):
        st.caption(
            "Live traffic: "
            f"current speed {traffic.get('current_speed_kmph', 0.0):.1f} km/h, "
            f"free-flow {traffic.get('free_flow_speed_kmph', 0.0):.1f} km/h."
        )

    notes = realtime.get("notes", [])
    if notes:
        st.markdown("\n".join([f"- {note}" for note in notes]))


def render_results(route_result):
    summaries = route_result.get("summaries", [])
    if not summaries:
        st.warning("No route summaries were generated.")
        return

    routing = route_result.get("routing", {})
    use_case = routing.get("use_case", "standard")
    weight_mode = routing.get("weight_mode", "distance")

    if use_case == "delivery" and route_result.get("delivery"):
        delivery = route_result["delivery"]
        metric_cols = st.columns(4)
        metric_cols[0].metric("Total distance", f"{delivery.get('total_distance_km', 0.0):.2f} km")
        metric_cols[1].metric("Total ETA", f"{delivery.get('total_eta_min', 0.0):.1f} min")
        metric_cols[2].metric("Leg count", f"{delivery.get('total_legs', 0)}")
        metric_cols[3].metric("Unreachable stops", f"{len(delivery.get('unreachable_stops', []))}")
    else:
        primary = summaries[0]
        metric_cols = st.columns(4)
        metric_cols[0].metric("Primary distance", f"{primary.get('distance_km', 0.0):.2f} km")
        metric_cols[1].metric("Primary ETA", f"{primary.get('eta_min', 0.0):.1f} min")
        metric_cols[2].metric("Nodes", f"{primary.get('node_count', 0)}")

        if weight_mode == "traffic":
            metric_cols[3].metric("Traffic delay", f"{primary.get('traffic_delta_min', 0.0):+.1f} min")
        else:
            metric_cols[3].metric("Avg speed", f"{primary.get('avg_speed_kmph', 0.0):.1f} km/h")

    rows = []
    for summary in summaries:
        route_name = summary.get("route_label")
        if not route_name:
            route_name = (
                "Recommended"
                if summary.get("route_index") == 1
                else f"Alternative {summary.get('route_index', 1) - 1}"
            )

        row = {
            "Route": route_name,
            "Distance (km)": round(float(summary.get("distance_km", 0.0)), 3),
            "ETA (min)": round(float(summary.get("eta_min", 0.0)), 2),
            "Nodes": int(summary.get("node_count", 0)),
            "Delay vs free-flow (min)": round(float(summary.get("traffic_delta_min", 0.0)), 2),
            "Avg speed (km/h)": round(float(summary.get("avg_speed_kmph", 0.0)), 2),
        }

        if summary.get("from_point") and summary.get("to_point"):
            row["From"] = format_point(summary["from_point"])
            row["To"] = format_point(summary["to_point"])

        rows.append(row)

    st.subheader("Route Comparison")
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    snap = route_result.get("snap") or {}
    st.markdown(
        f"<div class='note'><b>Snap diagnostics:</b> start snapped by {snap.get('start_to_node_m', 0.0):.0f} m, "
        f"end snapped by {snap.get('end_to_node_m', 0.0):.0f} m.</div>",
        unsafe_allow_html=True,
    )

    render_realtime_context(route_result.get("realtime") or {})


def render_planning_insights(planning):
    if not planning:
        return

    st.subheader("Urban Planning and Analysis")
    cols = st.columns(2)
    cols[0].metric("Route overlap", f"{float(planning.get('overlap_pct', 0.0)):.2f}%")
    cols[1].metric("Hotspot segments", f"{len(planning.get('hotspots', []))}")

    highway_mix = planning.get("highway_mix") or []
    if highway_mix:
        st.markdown("Highway usage mix")
        st.dataframe(pd.DataFrame(highway_mix), hide_index=True, use_container_width=True)

    hotspots = planning.get("hotspots") or []
    if hotspots:
        st.markdown("Top hotspot segments")
        st.dataframe(pd.DataFrame(hotspots), hide_index=True, use_container_width=True)

    recommendations = planning.get("recommendations") or []
    if recommendations:
        st.markdown("Planning recommendations")
        st.markdown("\n".join([f"- {item}" for item in recommendations]))


def main():
    render_page_chrome()
    params = build_sidebar()

    st.markdown(
        """
        <div class="note">
          Tip: enable <b>live context</b> and switch to <b>delivery</b> or <b>emergency</b> to see project-specific capabilities beyond standard shortest path demos.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not params["optimize_clicked"]:
        st.info("Fill inputs in the sidebar and click Optimize Route to generate your interactive map.")
        return

    try:
        start_point = parse_coordinate_pair(params["start_raw"])
        end_point = parse_coordinate_pair(params["end_raw"])
        stop_points = parse_stop_points(params["stops_raw"])
    except ValueError as exc:
        st.error(str(exc))
        return

    if params["use_case"] == "delivery" and not stop_points:
        st.error("Delivery mode requires at least one stop in the Delivery stops field.")
        return

    with st.spinner("Preparing graph, integrating live context, calculating routes, and rendering map..."):
        graph = load_cached_graph(
            place_name=params["place_name"],
            profile=params["profile"],
            use_cache=params["use_cache"],
            offline=params["offline_mode"],
            graph_file=params["graph_file"],
        )

        if graph is None:
            if params["offline_mode"]:
                st.error("Offline graph not available. Choose a local graph cache file or disable offline mode.")
            else:
                st.error("Failed to build graph. Check place name and network connection.")
            return

        realtime_context = build_realtime_context(
            start_point=start_point,
            end_point=end_point,
            enabled=params["realtime_enabled"],
            weather_enabled=params["weather_enabled"],
            traffic_enabled=params["traffic_live_enabled"],
            traffic_api_key=params["traffic_api_key"],
        )

        if params["use_case"] == "delivery":
            route_result = optimize_delivery_route(
                graph=graph,
                start_point=start_point,
                stop_points=stop_points,
                algorithm=params["algorithm"],
                avg_speed_kmph=params["avg_speed"],
                weight_mode=params["weight_mode"],
                time_slot=params["time_slot"],
                traffic_level=params["traffic_level"],
                realtime_context=realtime_context,
                return_to_start=params["return_to_start"],
            )
        else:
            route_result = calculate_routes(
                graph=graph,
                start_point=start_point,
                end_point=end_point,
                algorithm=params["algorithm"],
                alternatives=params["alternatives"],
                avg_speed_kmph=params["avg_speed"],
                weight_mode=params["weight_mode"],
                time_slot=params["time_slot"],
                traffic_level=params["traffic_level"],
                realtime_context=realtime_context,
                use_case=params["use_case"],
            )

        if route_result is None:
            st.error("No path found for the selected points and settings.")
            return

        planning = generate_urban_insights(graph, route_result.get("routes", []))
        planning["heatmap_points"] = build_route_heatmap_points(graph, route_result.get("routes", []))

        route_result["planning"] = planning
        route_result["realtime"] = realtime_context

        output_path = Path(params["output_file"])
        if not output_path.is_absolute():
            output_path = ROOT_DIR / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        visualize_route(
            graph=graph,
            routes=route_result["routes"],
            output_file=str(output_path),
            route_summaries=route_result.get("summaries"),
            place_name=params["place_name"],
            snap_info=route_result.get("snap"),
            heatmap_points=planning.get("heatmap_points"),
            planning_hotspots=planning.get("hotspots"),
        )

    render_results(route_result)
    render_planning_insights(route_result.get("planning"))

    st.subheader("Interactive Map")
    with open(output_path, "r", encoding="utf-8") as html_file:
        components.html(html_file.read(), height=760, scrolling=True)

    st.success(f"Map generated successfully at: {output_path}")


if __name__ == "__main__":
    main()
