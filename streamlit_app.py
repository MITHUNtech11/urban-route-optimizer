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


def initialize_state():
    defaults = {
        "route_result": None,
        "output_path": None,
        "map_html": None,
        "last_params": None,
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
            padding: 28px 30px;
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
            font-size: 2.15rem;
            font-weight: 800;
            letter-spacing: 0.02em;
            line-height: 1.18;
          }

          .hero p {
            margin: 0;
            max-width: 860px;
            font-family: 'Manrope', sans-serif;
            font-size: 1rem;
            line-height: 1.54;
            opacity: 0.93;
          }

          .hero-badges {
            margin-top: 16px;
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
          }

          .hero-badges span {
            border: 1px solid rgba(255, 255, 255, 0.35);
            border-radius: 999px;
            padding: 6px 12px;
            font-size: 0.8rem;
            background: rgba(255, 255, 255, 0.12);
            font-weight: 600;
          }

          .workflow-card {
            border-radius: 15px;
            border: 1px solid var(--card-border);
            background: var(--card-bg);
            padding: 12px 13px;
            box-shadow: 0 12px 28px rgba(21, 33, 42, 0.08);
            min-height: 106px;
            animation: fadeUp 560ms ease-out;
          }

          .workflow-card h4 {
            margin: 0 0 5px 0;
            color: var(--ink-900);
            font-family: 'Sora', sans-serif;
            font-size: 0.92rem;
            font-weight: 700;
          }

          .workflow-card p {
            margin: 0;
            color: var(--ink-700);
            font-family: 'Manrope', sans-serif;
            font-size: 0.86rem;
            line-height: 1.35;
          }

          .panel {
            border-radius: 18px;
            border: 1px solid var(--card-border);
            background: var(--card-bg);
            padding: 20px 20px 14px 20px;
            box-shadow: 0 16px 34px rgba(21, 33, 42, 0.10);
            animation: fadeUp 620ms ease-out;
          }

                    div[data-testid="stForm"] {
                        border-radius: 18px;
                        border: 1px solid var(--card-border);
                        background: var(--card-bg);
                        padding: 16px 16px 10px 16px;
                        box-shadow: 0 16px 34px rgba(21, 33, 42, 0.10);
                        margin-top: 8px;
                        margin-bottom: 8px;
                    }

          .section-title {
            font-family: 'Sora', sans-serif;
            font-weight: 700;
            color: var(--ink-900);
            letter-spacing: 0.02em;
            margin-bottom: 8px;
            font-size: 1.08rem;
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

          .metric-ribbon {
            margin: 6px 0 14px 0;
            border-radius: 12px;
            border: 1px solid rgba(247, 191, 86, 0.45);
            background: rgba(247, 191, 86, 0.16);
            padding: 8px 10px;
            color: #594420;
            font-weight: 600;
            font-family: 'Manrope', sans-serif;
            font-size: 0.86rem;
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

          .stTabs [data-baseweb="tab-list"] {
                        gap: 14px;
                        margin-bottom: 14px;
                        padding-bottom: 4px;
                        flex-wrap: wrap;
          }

          .stTabs [data-baseweb="tab"] {
            border-radius: 999px;
            border: 1px solid rgba(21, 33, 42, 0.12);
            background: rgba(255, 255, 255, 0.70);
            color: var(--ink-700);
            font-family: 'Manrope', sans-serif;
            font-weight: 700;
                        padding: 10px 18px;
            height: auto;
          }

          .stTabs [aria-selected="true"] {
            background: linear-gradient(90deg, rgba(13, 122, 114, 0.94), rgba(25, 160, 147, 0.94));
            color: #ffffff;
            border-color: rgba(13, 122, 114, 0.2);
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

            .panel {
              padding: 16px 14px 11px 14px;
            }
          }
        </style>

        <section class="hero">
          <div class="hero-kicker">Urban Mobility Platform</div>
          <h1>Urban Route Optimizer Studio</h1>
          <p>Design robust city routes with offline confidence, live operational context, and decision-grade analytics for rider-facing web experiences.</p>
          <div class="hero-badges">
            <span>Traffic-aware ETA</span>
            <span>Delivery leg optimizer</span>
            <span>Emergency priority mode</span>
            <span>Planning intelligence</span>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_workflow_strip():
    cards = [
        ("1. Configure", "Set city, coordinates, and routing profile."),
        ("2. Optimize", "Choose distance or traffic-aware scoring."),
        ("3. Simulate", "Blend live context and offline-safe controls."),
        ("4. Analyze", "Review alternatives, hotspots, and map output."),
    ]
    cols = st.columns(len(cards))
    for col, (title, description) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="workflow-card">
                  <h4>{title}</h4>
                  <p>{description}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_route_studio_form():
    st.markdown("<div class='section-title'>Route Studio</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='helper-note'>Build route scenarios here, then use the tabs below to inspect outputs, metrics, and planning insights.</div>",
        unsafe_allow_html=True,
    )

    with st.form("route_studio_form", clear_on_submit=False):
        left_col, right_col = st.columns([1.03, 0.97], gap="large")

        with left_col:
            st.markdown("### Trip Geometry")
            place_name = st.text_input(
                "City or region",
                value="Chennai, Tamil Nadu, India",
                help="Use place names recognized by OpenStreetMap geocoding.",
            )

            coord_cols = st.columns(2)
            start_raw = coord_cols[0].text_input("Start (lat,lon)", value="13.065,80.237")
            end_raw = coord_cols[1].text_input("End (lat,lon)", value="13.045,80.260")

            mode_cols = st.columns(3)
            use_case = mode_cols[0].selectbox("Use case", USE_CASE_OPTIONS, index=0)
            profile = mode_cols[1].selectbox("Vehicle profile", ["scooter", "bike", "drive"], index=0)
            algorithm = mode_cols[2].selectbox("Search algorithm", ["dijkstra", "astar"], index=0)

            if use_case == "delivery":
                stops_raw = st.text_area(
                    "Delivery stops (one per line)",
                    value="13.055,80.244\n13.048,80.251",
                    height=110,
                    help="Format each stop as lat,lon on a separate line.",
                )
                return_to_start = st.checkbox("Return to origin after final stop", value=False)
            else:
                stops_raw = ""
                return_to_start = False

            st.markdown("### Optimization Controls")
            alternatives = st.slider("Alternative routes", min_value=0, max_value=3, value=1)
            avg_speed = st.slider(
                "Average speed (km/h)",
                min_value=10.0,
                max_value=60.0,
                value=28.0,
                step=1.0,
            )

            weight_mode = st.selectbox("Objective", ["distance", "traffic"], index=1)
            if weight_mode == "traffic":
                time_slot = st.selectbox("Traffic slot", TIME_SLOT_OPTIONS, index=2)
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

        with right_col:
            st.markdown("### Live Operations")
            realtime_enabled = st.checkbox("Enable live operational context", value=False)
            weather_enabled = st.checkbox("Weather-aware weighting", value=True)
            traffic_live_enabled = st.checkbox("Live traffic override (TomTom)", value=False)
            traffic_api_key = st.text_input(
                "TomTom API key",
                value="",
                type="password",
                help="Required only when live traffic override is enabled.",
            )

            st.markdown("### Data Source and Reliability")
            offline_mode = st.checkbox("Offline-only mode", value=False)
            use_cache = st.checkbox("Use graph cache", value=True)

            available_graphs = [
                str(path) for path in list_cached_graphs(cache_dir="data", profile=profile)
            ]
            graph_option_labels = ["Auto-select by place/profile"] + [
                Path(path).name for path in available_graphs
            ]
            graph_option_values = [""] + available_graphs
            graph_option_index = st.selectbox(
                "Offline graph file",
                options=list(range(len(graph_option_values))),
                format_func=lambda idx: graph_option_labels[idx],
                index=0,
                help="Pick a local GraphML file for deterministic routing runs.",
            )

            output_file = st.text_input("Output map HTML", value="output/streamlit_route.html")

            st.markdown("### Run")
            st.caption(
                "Submit once to render map output, route alternatives, and planning intelligence."
            )
            optimize_clicked = st.form_submit_button(
                "Generate Route Experience",
                use_container_width=True,
                type="primary",
            )

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
        "graph_file": graph_option_values[graph_option_index] or None,
        "output_file": output_file,
        "optimize_clicked": optimize_clicked,
    }


def sanitize_params_for_display(params):
    redacted = {
        key: value
        for key, value in params.items()
        if key not in {"optimize_clicked", "traffic_api_key"}
    }
    redacted["traffic_api_key_set"] = bool(params.get("traffic_api_key"))
    return redacted


def execute_optimization(params):
    start_point = parse_coordinate_pair(params["start_raw"])
    end_point = parse_coordinate_pair(params["end_raw"])
    stop_points = parse_stop_points(params["stops_raw"])

    if params["use_case"] == "delivery" and not stop_points:
        raise ValueError("Delivery mode requires at least one stop in the Delivery stops field.")

    graph = load_cached_graph(
        place_name=params["place_name"],
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
        place_name=params["place_name"],
        snap_info=route_result.get("snap"),
        heatmap_points=planning.get("heatmap_points"),
        planning_hotspots=planning.get("hotspots"),
    )

    map_html = output_path.read_text(encoding="utf-8") if output_path.exists() else None

    return route_result, output_path, map_html


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

        if summary.get("from_point") and summary.get("to_point"):
            row["From"] = format_point(summary["from_point"])
            row["To"] = format_point(summary["to_point"])

        rows.append(row)
    return rows


def render_highlights(route_result):
    summaries = route_result.get("summaries", [])
    if not summaries:
        st.warning("No route summaries were generated.")
        return

    routing = route_result.get("routing", {})
    use_case = routing.get("use_case", "standard")
    weight_mode = routing.get("weight_mode", "distance")

    if use_case == "delivery" and route_result.get("delivery"):
        delivery = route_result["delivery"]
        cols = st.columns(4)
        cols[0].metric("Total distance", f"{delivery.get('total_distance_km', 0.0):.2f} km")
        cols[1].metric("Total ETA", f"{delivery.get('total_eta_min', 0.0):.1f} min")
        cols[2].metric("Leg count", f"{delivery.get('total_legs', 0)}")
        cols[3].metric("Unreachable stops", f"{len(delivery.get('unreachable_stops', []))}")
        return

    primary = summaries[0]
    cols = st.columns(4)
    cols[0].metric("Primary distance", f"{primary.get('distance_km', 0.0):.2f} km")
    cols[1].metric("Primary ETA", f"{primary.get('eta_min', 0.0):.1f} min")
    cols[2].metric("Path nodes", f"{primary.get('node_count', 0)}")
    if weight_mode == "traffic":
        cols[3].metric("Traffic delay", f"{primary.get('traffic_delta_min', 0.0):+.1f} min")
    else:
        cols[3].metric("Average speed", f"{primary.get('avg_speed_kmph', 0.0):.1f} km/h")


def render_realtime_context(realtime):
    if not realtime or not realtime.get("enabled"):
        st.info("Live context was disabled for this run.")
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
        st.info("Planning insights are not available for this run.")
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


def render_result_hub(route_result, output_path, map_html, run_params):
    st.markdown("<div class='section-title'>Result Hub</div>", unsafe_allow_html=True)
    tabs = st.tabs(["Map Experience", "Route Intelligence", "Urban Signals", "Run Context"])

    with tabs[0]:
        render_highlights(route_result)
        st.markdown(
            "<div class='metric-ribbon'>Use the map tools to inspect alternatives, measure distances, and compare corridor usage.</div>",
            unsafe_allow_html=True,
        )
        if map_html:
            components.html(map_html, height=780, scrolling=True)
            st.success(f"Route output is displayed above and saved at: {output_path}")
        elif output_path.exists():
            components.html(output_path.read_text(encoding="utf-8"), height=780, scrolling=True)
            st.success(f"Route output is displayed above and saved at: {output_path}")
        else:
            st.warning("Map file is missing. Please run optimization again.")

    with tabs[1]:
        rows = build_route_comparison_rows(route_result)
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        else:
            st.info("No route comparison rows generated for this run.")

        snap = route_result.get("snap") or {}
        st.markdown(
            f"""
            <div class="helper-note">
              <b>Snap diagnostics:</b> start snapped by {snap.get('start_to_node_m', 0.0):.0f} m,
              end snapped by {snap.get('end_to_node_m', 0.0):.0f} m.
            </div>
            """,
            unsafe_allow_html=True,
        )

        render_realtime_context(route_result.get("realtime") or {})

    with tabs[2]:
        render_planning_insights(route_result.get("planning"))

    with tabs[3]:
        st.markdown("#### Inputs used in latest run")
        st.json(run_params)
        st.caption("Secrets are masked. Coordinates and parameters reflect the last successful optimization.")


def render_empty_state():
    st.markdown(
        """
        <div class="empty-state">
          <b>Ready to plan.</b><br/>
          Configure a route scenario in Route Studio and click <i>Generate Route Experience</i>.
          Your map, alternatives, and analytics will appear in the Result Hub.
        </div>
        """,
        unsafe_allow_html=True,
    )


def main():
    render_page_chrome()
    initialize_state()
    render_workflow_strip()
    params = render_route_studio_form()

    if params["optimize_clicked"]:
        try:
            with st.spinner(
                "Preparing graph, integrating context, optimizing routes, and rendering the experience..."
            ):
                route_result, output_path, map_html = execute_optimization(params)

            st.session_state["route_result"] = route_result
            st.session_state["output_path"] = str(output_path)
            st.session_state["map_html"] = map_html
            st.session_state["last_params"] = sanitize_params_for_display(params)
            st.session_state["run_error"] = None
        except (ValueError, RuntimeError) as exc:
            st.session_state["run_error"] = str(exc)

    if st.session_state.get("run_error"):
        st.error(st.session_state["run_error"])

    if st.session_state.get("route_result") and st.session_state.get("output_path"):
        render_result_hub(
            route_result=st.session_state["route_result"],
            output_path=Path(st.session_state["output_path"]),
            map_html=st.session_state.get("map_html"),
            run_params=st.session_state.get("last_params") or {},
        )
    else:
        render_empty_state()


if __name__ == "__main__":
    main()
