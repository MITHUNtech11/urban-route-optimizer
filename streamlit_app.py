#!/usr/bin/env python3
"""Streamlit front-end for the Urban Route Optimizer project."""

from pathlib import Path

import osmnx as ox
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


ROOT_DIR = Path(__file__).resolve().parent

from src.analytics import build_route_heatmap_points, generate_urban_insights
from src.build_graph import build_graph, list_cached_graphs
from src.calculate_route import calculate_routes
from src.realtime import build_realtime_context
from src.visualize import visualize_route


TIME_SLOT_OPTIONS = [
    "early_morning",
    "morning_peak",
    "midday",
    "evening_peak",
    "night",
]

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


@st.cache_data(show_spinner=False)
def geocode_location(query):
    point = ox.geocode(query)
    return float(point[0]), float(point[1])


def initialize_state():
    defaults = {
        "route_result": None,
        "output_path": None,
        "map_html": None,
        "last_inputs": None,
        "run_error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_page_chrome():
    st.set_page_config(
        page_title="Urban Route Optimizer Studio",
        page_icon="U",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.markdown(
        """
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=Sora:wght@500;700;800&display=swap');

          :root {
            --ink-900: #15212a;
            --ink-700: #2c3a44;
            --teal-700: #0d7a72;
            --teal-500: #19a093;
            --sand-100: #f6f1e8;
            --amber-300: #f7bf56;
            --card-bg: rgba(255, 255, 255, 0.84);
            --card-border: rgba(21, 33, 42, 0.12);
          }

          .stApp {
            background:
              radial-gradient(circle at 12% 15%, rgba(25, 160, 147, 0.14) 0%, rgba(25, 160, 147, 0) 35%),
              radial-gradient(circle at 88% 15%, rgba(247, 191, 86, 0.20) 0%, rgba(247, 191, 86, 0) 38%),
              linear-gradient(160deg, #f7f3eb 0%, #eef4f3 42%, #f7f4ed 100%);
          }

          [data-testid="stHeader"] {
            background: transparent;
          }

          [data-testid="stToolbar"] {
            right: 0.85rem;
          }

          .block-container {
            max-width: 1180px;
            padding-top: 1.25rem;
            padding-bottom: 2.5rem;
          }

          .hero {
            border-radius: 22px;
            border: 1px solid rgba(255, 255, 255, 0.52);
            background:
              linear-gradient(135deg, rgba(11, 107, 100, 0.94) 0%, rgba(23, 142, 131, 0.92) 48%, rgba(33, 165, 152, 0.94) 100%);
            color: #ffffff;
                        padding: 24px 26px;
            box-shadow: 0 24px 44px rgba(19, 83, 82, 0.28);
            animation: fadeUp 520ms ease-out;
          }

          .hero-kicker {
            font-family: 'Sora', sans-serif;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-size: 0.73rem;
            opacity: 0.92;
            font-weight: 600;
          }

          .hero h1 {
            margin: 10px 0 8px 0;
            font-family: 'Sora', sans-serif;
                        font-size: 2rem;
            font-weight: 800;
            letter-spacing: 0.02em;
            line-height: 1.18;
          }

          .hero p {
            margin: 0;
            max-width: 860px;
            font-family: 'Manrope', sans-serif;
                        font-size: 0.98rem;
            line-height: 1.54;
            opacity: 0.93;
          }

                    div[data-testid="stForm"] {
                        border-radius: 18px;
                        border: 1px solid var(--card-border);
                        background: var(--card-bg);
                        padding: 16px 16px 10px 16px;
                        box-shadow: 0 16px 34px rgba(21, 33, 42, 0.10);
                        margin-top: 10px;
                        margin-bottom: 14px;
                    }

          .helper-note {
            border-radius: 12px;
            border-left: 5px solid var(--teal-500);
            border: 1px solid rgba(13, 122, 114, 0.18);
            background: rgba(13, 122, 114, 0.07);
            padding: 11px 12px;
            color: #12403f;
            font-size: 0.9rem;
            font-family: 'Manrope', sans-serif;
            margin-top: 8px;
            margin-bottom: 8px;
          }

          div[data-testid="stMetric"] {
            border: 1px solid rgba(21, 33, 42, 0.10);
            background: rgba(255, 255, 255, 0.77);
            border-radius: 12px;
            padding: 9px 10px;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.5);
          }

          div[data-testid="stMetricLabel"] {
            color: #35515f;
            font-family: 'Manrope', sans-serif;
            font-weight: 700;
          }

          div[data-testid="stMetricValue"] {
            color: #102026;
            font-family: 'Sora', sans-serif;
            font-weight: 700;
          }

          .empty-state {
            border: 1px dashed rgba(21, 33, 42, 0.24);
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.6);
            padding: 16px;
            font-family: 'Manrope', sans-serif;
            color: #2e4552;
          }

          @keyframes fadeUp {
            0% {
              opacity: 0;
              transform: translateY(10px);
            }
            100% {
              opacity: 1;
              transform: translateY(0);
            }
          }

          @media (max-width: 880px) {
            .hero {
              padding: 20px 18px;
            }

            .hero h1 {
              font-size: 1.7rem;
            }

                        div[data-testid="stForm"] {
                            padding: 14px 12px 10px 12px;
            }
          }
        </style>

        <section class="hero">
          <div class="hero-kicker">Urban Mobility Platform</div>
          <h1>Find the best route in one step</h1>
          <p>Enter your city and two area names. The app handles geocoding, routing, and map output automatically.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_simple_form():
    st.markdown(
        "<div class='helper-note'>Simple mode: fill City, From area, and To area, then click Find Route.</div>",
        unsafe_allow_html=True,
    )

    with st.form("simple_route_form", clear_on_submit=False):
        st.markdown("### Route Input")
        city = st.text_input(
            "City",
            value="Chennai, Tamil Nadu, India",
            help="Example: Chennai, Tamil Nadu, India",
        )

        area_cols = st.columns(2)
        start_area = area_cols[0].text_input(
            "From area",
            value="T Nagar",
            help="Use a neighborhood, landmark, or area name.",
        )
        end_area = area_cols[1].text_input(
            "To area",
            value="Adyar",
            help="Use a neighborhood, landmark, or area name.",
        )

        with st.expander("Advanced settings (optional)", expanded=False):
            tuning_cols = st.columns(3)
            profile = tuning_cols[0].selectbox("Vehicle", ["scooter", "bike", "drive"], index=0)
            algorithm = tuning_cols[1].selectbox("Algorithm", ["dijkstra", "astar"], index=0)
            alternatives = tuning_cols[2].slider("Alternatives", min_value=0, max_value=3, value=1)

            weight_cols = st.columns(3)
            weight_mode = weight_cols[0].selectbox("Objective", ["traffic", "distance"], index=0)
            avg_speed = weight_cols[1].slider(
                "Avg speed (km/h)",
                min_value=10.0,
                max_value=60.0,
                value=28.0,
                step=1.0,
            )
            if weight_mode == "traffic":
                time_slot = weight_cols[2].selectbox("Traffic slot", TIME_SLOT_OPTIONS, index=2)
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

            data_cols = st.columns(2)
            offline_mode = data_cols[0].checkbox("Offline-only mode", value=False)
            use_cache = data_cols[1].checkbox("Use graph cache", value=True)

            available_graphs = [
                str(path) for path in list_cached_graphs(cache_dir="data", profile=profile)
            ]
            graph_labels = ["Auto-select by city/profile"] + [Path(path).name for path in available_graphs]
            graph_values = [""] + available_graphs
            graph_option_index = st.selectbox(
                "Offline graph file",
                options=list(range(len(graph_values))),
                format_func=lambda idx: graph_labels[idx],
                index=0,
            )

            realtime_enabled = st.checkbox("Enable live context", value=False)
            weather_enabled = st.checkbox("Weather-aware weighting", value=True)
            traffic_live_enabled = st.checkbox("Live traffic override (TomTom)", value=False)
            traffic_api_key = st.text_input("TomTom API key", value="", type="password")

        optimize_clicked = st.form_submit_button(
            "Find Route",
            use_container_width=True,
            type="primary",
        )

    return {
        "city": city.strip(),
        "start_area": start_area.strip(),
        "end_area": end_area.strip(),
        "profile": profile,
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
        "graph_file": graph_values[graph_option_index] or None,
        "output_file": "output/streamlit_route.html",
        "optimize_clicked": optimize_clicked,
    }


def validate_simple_inputs(params):
    if not params["city"]:
        raise ValueError("Please enter a city.")
    if not params["start_area"]:
        raise ValueError("Please enter a start area.")
    if not params["end_area"]:
        raise ValueError("Please enter a destination area.")


def geocode_area(city, area_label, area_type):
    query = f"{area_label}, {city}"
    try:
        point = geocode_location(query)
        return point, query
    except Exception as exc:
        raise ValueError(
            f"Could not find the {area_type} area '{area_label}' in '{city}'. Try a nearby landmark or neighborhood name."
        ) from exc


def execute_optimization(params):
    validate_simple_inputs(params)

    start_point, start_query = geocode_area(
        city=params["city"],
        area_label=params["start_area"],
        area_type="start",
    )
    end_point, end_query = geocode_area(
        city=params["city"],
        area_label=params["end_area"],
        area_type="destination",
    )

    graph = load_cached_graph(
        place_name=params["city"],
        profile=params["profile"],
        use_cache=params["use_cache"],
        offline=params["offline_mode"],
        graph_file=params["graph_file"],
    )

    if graph is None:
        if params["offline_mode"]:
            raise RuntimeError(
                "Offline graph not available. Choose a local graph cache file or disable offline mode."
            )
        raise RuntimeError("Failed to build graph. Check place name and network connection.")

    realtime_context = build_realtime_context(
        start_point=start_point,
        end_point=end_point,
        enabled=params["realtime_enabled"],
        weather_enabled=params["weather_enabled"],
        traffic_enabled=params["traffic_live_enabled"],
        traffic_api_key=params["traffic_api_key"],
    )

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
        use_case="standard",
    )

    if route_result is None:
        raise RuntimeError("No path found for the selected points and settings.")

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
        place_name=params["city"],
        snap_info=route_result.get("snap"),
        heatmap_points=planning.get("heatmap_points"),
        planning_hotspots=planning.get("hotspots"),
    )

    map_html = output_path.read_text(encoding="utf-8") if output_path.exists() else None

    simple_inputs = {
        "city": params["city"],
        "from": params["start_area"],
        "to": params["end_area"],
        "resolved_from": start_query,
        "resolved_to": end_query,
        "profile": params["profile"],
        "objective": params["weight_mode"],
        "traffic_slot": params["time_slot"],
    }
    return route_result, output_path, map_html, simple_inputs


def build_route_comparison_rows(route_result):
    rows = []
    summaries = route_result.get("summaries", [])
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

        rows.append(row)
    return rows


def render_highlights(route_result, last_inputs):
    summaries = route_result.get("summaries", [])
    if not summaries:
        st.warning("No route summaries were generated.")
        return

    primary = summaries[0]
    cols = st.columns(4)
    cols[0].metric("Distance", f"{primary.get('distance_km', 0.0):.2f} km")
    cols[1].metric("ETA", f"{primary.get('eta_min', 0.0):.1f} min")
    cols[2].metric("Path nodes", f"{primary.get('node_count', 0)}")
    cols[3].metric("Average speed", f"{primary.get('avg_speed_kmph', 0.0):.1f} km/h")

    st.caption(
        f"Showing route from {last_inputs.get('from', 'Start')} to {last_inputs.get('to', 'End')} in {last_inputs.get('city', 'selected city')}."
    )


def render_realtime_context(realtime):
    if not realtime or not realtime.get("enabled"):
        st.caption("Live context was disabled for this run.")
        return

    st.markdown("#### Real-Time Context")
    metric_cols = st.columns(3)
    metric_cols[0].metric("Weather slowdown factor", f"x{realtime.get('weather_penalty_factor', 1.0):.2f}")

    override = realtime.get("traffic_level_override")
    if override is None:
        metric_cols[1].metric("Live traffic level", "Not active")
    else:
        metric_cols[1].metric("Live traffic level", f"{float(override):.2f} / 3.0")

    notes = realtime.get("notes", [])
    metric_cols[2].metric("Context notes", f"{len(notes)}")

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

    if notes:
        st.markdown("\n".join([f"- {note}" for note in notes]))


def render_planning_insights(planning):
    if not planning:
        st.caption("Planning insights are not available for this run.")
        return

    cols = st.columns(2)
    cols[0].metric("Route overlap", f"{float(planning.get('overlap_pct', 0.0)):.2f}%")
    cols[1].metric("Hotspot segments", f"{len(planning.get('hotspots', []))}")

    highway_mix = planning.get("highway_mix") or []
    if highway_mix:
        st.markdown("#### Highway Usage Mix")
        st.dataframe(pd.DataFrame(highway_mix), hide_index=True, use_container_width=True)

    hotspots = planning.get("hotspots") or []
    if hotspots:
        st.markdown("#### Top Hotspot Segments")
        st.dataframe(pd.DataFrame(hotspots), hide_index=True, use_container_width=True)

    recommendations = planning.get("recommendations") or []
    if recommendations:
        st.markdown("#### Recommendations")
        st.markdown("\n".join([f"- {item}" for item in recommendations]))


def render_result_section(route_result, output_path, map_html, last_inputs):
    st.markdown("### Route Output")
    render_highlights(route_result, last_inputs)

    if map_html:
        components.html(map_html, height=780, scrolling=True)
        st.success(f"Route output is displayed above and saved at: {output_path}")
    elif output_path.exists():
        components.html(output_path.read_text(encoding="utf-8"), height=780, scrolling=True)
        st.success(f"Route output is displayed above and saved at: {output_path}")
    else:
        st.warning("Map file is missing. Please run again.")

    with st.expander("See detailed route data", expanded=False):
        rows = build_route_comparison_rows(route_result)
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

        snap = route_result.get("snap") or {}
        st.caption(
            f"Snap diagnostics: start snapped by {snap.get('start_to_node_m', 0.0):.0f} m, end snapped by {snap.get('end_to_node_m', 0.0):.0f} m."
        )

        render_realtime_context(route_result.get("realtime") or {})
        render_planning_insights(route_result.get("planning"))

        st.markdown("#### Last search")
        st.json(last_inputs)


def render_empty_state():
    st.markdown(
        """
        <div class="empty-state">
          <b>Ready to plan.</b><br/>
                    Enter your City, From area, and To area, then click <i>Find Route</i>.
                    The optimized map will appear right below.
        </div>
        """,
        unsafe_allow_html=True,
    )


def main():
    render_page_chrome()
    initialize_state()
    params = render_simple_form()

    if params["optimize_clicked"]:
        try:
            with st.spinner(
                "Finding areas, building graph, optimizing route, and rendering map..."
            ):
                route_result, output_path, map_html, last_inputs = execute_optimization(params)

            st.session_state["route_result"] = route_result
            st.session_state["output_path"] = str(output_path)
            st.session_state["map_html"] = map_html
            st.session_state["last_inputs"] = last_inputs
            st.session_state["run_error"] = None
        except (ValueError, RuntimeError) as exc:
            st.session_state["run_error"] = str(exc)

    if st.session_state.get("run_error"):
        st.error(st.session_state["run_error"])

    if st.session_state.get("route_result") and st.session_state.get("output_path"):
        render_result_section(
            route_result=st.session_state["route_result"],
            output_path=Path(st.session_state["output_path"]),
            map_html=st.session_state.get("map_html"),
            last_inputs=st.session_state.get("last_inputs") or {},
        )
    else:
        render_empty_state()


if __name__ == "__main__":
    main()
