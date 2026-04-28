#Project completed 
#Verified on 2024-06-01
"""Urban Route Optimizer CLI entrypoint."""

import argparse
from pathlib import Path

from src.analytics import build_route_heatmap_points, generate_urban_insights
from src.build_graph import build_graph
from src.calculate_route import calculate_routes
from src.realtime import build_realtime_context
from src.specialized import optimize_delivery_route
from src.visualize import visualize_route


def parse_coordinate_pair(value):
    try:
        lat_str, lon_str = [part.strip() for part in value.split(",", maxsplit=1)]
        return float(lat_str), float(lon_str)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid coordinate '{value}'. Use lat,lon format (example: 13.065,80.237)."
        ) from exc


def parse_stop_list(value):
    stops = []
    if not value:
        return stops

    for chunk in value.split(";"):
        cleaned = chunk.strip()
        if not cleaned:
            continue
        stops.append(parse_coordinate_pair(cleaned))
    return stops


def print_route_summary(route_result):
    routing_info = route_result.get("routing", {})
    use_case = routing_info.get("use_case", "standard")
    weight_mode = routing_info.get("weight_mode", "distance")

    print("\nRoute Summary")
    print("-" * 72)

    if use_case == "delivery" and route_result.get("delivery"):
        delivery = route_result["delivery"]
        print(
            "Delivery totals: "
            f"distance={delivery.get('total_distance_km', 0.0):.2f} km, "
            f"eta={delivery.get('total_eta_min', 0.0):.1f} min, "
            f"legs={delivery.get('total_legs', 0)}, "
            f"unreachable={len(delivery.get('unreachable_stops', []))}"
        )

    for summary in route_result.get("summaries", []):
        route_name = summary.get("route_label")
        if not route_name:
            route_name = (
                "Recommended"
                if summary.get("route_index") == 1
                else f"Alternative {summary.get('route_index', 1) - 1}"
            )

        line = (
            f"{route_name:16} | "
            f"Distance: {summary.get('distance_km', 0.0):6.2f} km | "
            f"ETA: {summary.get('eta_min', 0.0):6.1f} min | "
            f"Nodes: {summary.get('node_count', 0):4d}"
        )

        if weight_mode == "traffic":
            line += f" | Delay: {summary.get('traffic_delta_min', 0.0):+5.1f} min"

        print(line)

    print("-" * 72)

    snap = route_result.get("snap", {})
    print(f"Start point snapped by {snap.get('start_to_node_m', 0.0):.0f} m")
    print(f"End point snapped by {snap.get('end_to_node_m', 0.0):.0f} m")

    realtime = route_result.get("realtime", {})
    if realtime.get("enabled"):
        print(
            "Live context: "
            f"weather_penalty=x{realtime.get('weather_penalty_factor', 1.0):.2f}, "
            f"traffic_override={realtime.get('traffic_level_override', 'none')}"
        )

    planning = route_result.get("planning", {})
    if planning:
        print(
            "Planning analytics: "
            f"overlap={planning.get('overlap_pct', 0.0):.2f}%, "
            f"hotspots={len(planning.get('hotspots', []))}"
        )
        for recommendation in planning.get("recommendations", [])[:3]:
            print(f"  - {recommendation}")


def main():
    parser = argparse.ArgumentParser(
        description="Calculate optimized urban routes with offline, real-time, and planning capabilities.",
        epilog="""
Examples:
  python main.py
  python main.py --offline --graph-file "data/chennai-tamil-nadu-india-scooter.graphml"
  python main.py --use-case emergency --weight-mode traffic --realtime --traffic-live --traffic-api-key YOUR_KEY
  python main.py --use-case delivery --stops "13.055,80.244;13.048,80.251" --return-to-start
        """,
    )
    parser.add_argument(
        "--place",
        type=str,
        default="Chennai, Tamil Nadu, India",
        help="Place name for the area (default: Chennai, Tamil Nadu, India)",
    )
    parser.add_argument(
        "--start",
        type=parse_coordinate_pair,
        default=(13.065, 80.237),
        help="Start point as lat,lon (default: 13.065,80.237)",
    )
    parser.add_argument(
        "--end",
        type=parse_coordinate_pair,
        default=(13.045, 80.260),
        help="End point as lat,lon (default: 13.045,80.260)",
    )
    parser.add_argument(
        "--profile",
        type=str,
        choices=["scooter", "bike", "drive"],
        default="scooter",
        help="Mobility profile used while building graph (default: scooter)",
    )
    parser.add_argument(
        "--algorithm",
        type=str,
        choices=["dijkstra", "astar"],
        default="dijkstra",
        help="Pathfinding algorithm (default: dijkstra)",
    )
    parser.add_argument(
        "--alternatives",
        type=int,
        default=2,
        help="Number of alternative routes to include (default: 2)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=28.0,
        help="Average vehicle speed in km/h for ETA estimation (default: 28)",
    )
    parser.add_argument(
        "--weight-mode",
        type=str,
        choices=["distance", "traffic"],
        default="distance",
        help="Route optimization objective (distance or traffic-aware travel time)",
    )
    parser.add_argument(
        "--time-slot",
        type=str,
        choices=["early_morning", "morning_peak", "midday", "evening_peak", "night"],
        default="midday",
        help="Traffic time-slot profile used when --weight-mode traffic",
    )
    parser.add_argument(
        "--traffic-level",
        type=float,
        default=1.0,
        help="Traffic intensity scale from 0.0 (none) to 3.0 (heavy), default 1.0",
    )
    parser.add_argument(
        "--use-case",
        type=str,
        choices=["standard", "delivery", "emergency"],
        default="standard",
        help="Specialized workflow type (standard, delivery, emergency)",
    )
    parser.add_argument(
        "--stops",
        type=str,
        default="",
        help="Delivery stop list in 'lat,lon;lat,lon' format (used when --use-case delivery)",
    )
    parser.add_argument(
        "--return-to-start",
        action="store_true",
        help="In delivery mode, return to the starting point after last stop",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Offline-only mode: never fetch new OSM data",
    )
    parser.add_argument(
        "--graph-file",
        type=str,
        default="",
        help="Optional local .graphml file path for offline or deterministic runs",
    )
    parser.add_argument(
        "--realtime",
        action="store_true",
        help="Enable real-time context integration",
    )
    parser.add_argument(
        "--weather-live",
        action="store_true",
        help="Include live weather impact from Open-Meteo (enabled by default when --realtime)",
    )
    parser.add_argument(
        "--traffic-live",
        action="store_true",
        help="Include live traffic override from TomTom Flow API",
    )
    parser.add_argument(
        "--traffic-api-key",
        type=str,
        default="",
        help="TomTom API key used when --traffic-live is enabled",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable graph caching and always fetch from OpenStreetMap",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output/optimized_route.html",
        help="Output HTML file path (default: output/optimized_route.html)",
    )

    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    start_point = args.start
    end_point = args.end
    stop_points = parse_stop_list(args.stops)

    if args.use_case == "delivery" and not stop_points:
        print("Delivery mode requires at least one stop. Use --stops 'lat,lon;lat,lon'.")
        return

    print("\n" + "=" * 72)
    print("Urban Route Optimizer")
    print("=" * 72)
    print(f"Location: {args.place}")
    print(f"Profile: {args.profile}")
    print(f"Use Case: {args.use_case}")
    print(f"Algorithm: {args.algorithm}")
    print(f"Weight Mode: {args.weight_mode}")
    print(f"Offline: {args.offline}")
    print(f"Realtime: {args.realtime}")
    print(f"Output: {output_path}")
    print("=" * 72 + "\n")

    graph = build_graph(
        place_name=args.place,
        profile=args.profile,
        use_cache=not args.no_cache,
        cache_dir="data",
        offline=args.offline,
        graph_file=args.graph_file or None,
    )
    if graph is None:
        print("Failed to build graph. Check offline cache or network availability.")
        return

    weather_enabled = bool(args.weather_live or args.realtime)
    realtime_context = build_realtime_context(
        start_point=start_point,
        end_point=end_point,
        enabled=args.realtime,
        weather_enabled=weather_enabled,
        traffic_enabled=args.traffic_live,
        traffic_api_key=args.traffic_api_key,
    )

    if args.use_case == "delivery":
        route_result = optimize_delivery_route(
            graph=graph,
            start_point=start_point,
            stop_points=stop_points,
            algorithm=args.algorithm,
            avg_speed_kmph=args.speed,
            weight_mode=args.weight_mode,
            time_slot=args.time_slot,
            traffic_level=max(0.0, min(args.traffic_level, 3.0)),
            realtime_context=realtime_context,
            return_to_start=args.return_to_start,
        )
    else:
        route_result = calculate_routes(
            graph=graph,
            start_point=start_point,
            end_point=end_point,
            algorithm=args.algorithm,
            alternatives=max(0, args.alternatives),
            avg_speed_kmph=args.speed,
            weight_mode=args.weight_mode,
            time_slot=args.time_slot,
            traffic_level=max(0.0, min(args.traffic_level, 3.0)),
            realtime_context=realtime_context,
            use_case=args.use_case,
        )

    if route_result is None:
        print("Failed to calculate route set.")
        return

    planning = generate_urban_insights(graph, route_result.get("routes", []))
    planning["heatmap_points"] = build_route_heatmap_points(graph, route_result.get("routes", []))

    route_result["planning"] = planning
    route_result["realtime"] = realtime_context

    print_route_summary(route_result)

    visualize_route(
        graph=graph,
        routes=route_result["routes"],
        output_file=str(output_path),
        route_summaries=route_result.get("summaries"),
        place_name=args.place,
        snap_info=route_result.get("snap"),
        heatmap_points=planning.get("heatmap_points"),
        planning_hotspots=planning.get("hotspots"),
    )

    print(f"\nMap generated: {output_path.resolve()}")


if __name__ == "__main__":
    main()
