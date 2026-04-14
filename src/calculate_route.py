from itertools import islice
import re

import networkx as nx
import osmnx as ox
import pyproj


DEFAULT_SPEED_KMPH_BY_HIGHWAY = {
    "motorway": 65.0,
    "trunk": 55.0,
    "primary": 45.0,
    "secondary": 40.0,
    "tertiary": 35.0,
    "residential": 28.0,
    "service": 20.0,
    "living_street": 15.0,
}

TRAFFIC_SLOT_MULTIPLIERS = {
    "early_morning": {
        "default": 0.85,
        "primary": 0.80,
        "secondary": 0.82,
        "tertiary": 0.86,
        "residential": 0.90,
    },
    "morning_peak": {
        "default": 1.30,
        "motorway": 1.45,
        "trunk": 1.45,
        "primary": 1.55,
        "secondary": 1.45,
        "tertiary": 1.35,
        "residential": 1.15,
    },
    "midday": {
        "default": 1.00,
        "primary": 1.05,
        "secondary": 1.02,
        "tertiary": 1.00,
        "residential": 0.98,
    },
    "evening_peak": {
        "default": 1.35,
        "motorway": 1.50,
        "trunk": 1.50,
        "primary": 1.60,
        "secondary": 1.50,
        "tertiary": 1.38,
        "residential": 1.20,
    },
    "night": {
        "default": 0.80,
        "motorway": 0.85,
        "trunk": 0.85,
        "primary": 0.78,
        "secondary": 0.78,
        "tertiary": 0.82,
        "residential": 0.90,
    },
}

TIME_SLOT_ALIASES = {
    "morning": "morning_peak",
    "evening": "evening_peak",
}

MAX_HEURISTIC_SPEED_KMPH = 70.0
MIN_EFFECTIVE_SPEED_KMPH = 5.0

EMERGENCY_SPEED_MULTIPLIER_BY_HIGHWAY = {
    "motorway": 1.30,
    "trunk": 1.25,
    "primary": 1.20,
    "secondary": 1.15,
    "tertiary": 1.10,
    "residential": 0.95,
    "service": 0.90,
    "living_street": 0.85,
}


def _to_weighted_digraph(graph):
    """Convert MultiDiGraph to DiGraph by keeping the shortest edge per pair."""
    try:
        return ox.convert.to_digraph(graph, weight="length")
    except AttributeError:
        # Backward compatibility with older OSMnx releases.
        return ox.utils_graph.get_digraph(graph, weight="length")


def _normalize_time_slot(time_slot):
    slot = (time_slot or "midday").lower()
    slot = TIME_SLOT_ALIASES.get(slot, slot)
    return slot if slot in TRAFFIC_SLOT_MULTIPLIERS else "midday"


def _extract_primary_highway_tag(edge_data):
    highway = edge_data.get("highway")
    if isinstance(highway, str):
        return highway
    if isinstance(highway, (list, tuple)) and highway:
        return str(highway[0])
    if isinstance(highway, set) and highway:
        return str(next(iter(highway)))
    return "residential"


def _parse_maxspeed_kmph(raw_maxspeed):
    if raw_maxspeed is None:
        return None

    if isinstance(raw_maxspeed, (list, tuple, set)):
        values = [_parse_maxspeed_kmph(item) for item in raw_maxspeed]
        values = [value for value in values if value is not None and value > 0]
        return min(values) if values else None

    value = str(raw_maxspeed).strip().lower()
    if not value:
        return None

    match = re.search(r"(\d+(?:\.\d+)?)", value)
    if not match:
        return None

    speed = float(match.group(1))
    if "mph" in value:
        speed *= 1.60934
    return speed


def _base_speed_kmph_for_edge(edge_data, fallback_speed_kmph=28.0):
    parsed_speed = _parse_maxspeed_kmph(edge_data.get("maxspeed"))
    if parsed_speed and parsed_speed > 0:
        return max(parsed_speed, MIN_EFFECTIVE_SPEED_KMPH)

    highway_tag = _extract_primary_highway_tag(edge_data)
    return max(
        float(DEFAULT_SPEED_KMPH_BY_HIGHWAY.get(highway_tag, fallback_speed_kmph)),
        MIN_EFFECTIVE_SPEED_KMPH,
    )


def _traffic_multiplier_for_edge(edge_data, time_slot="midday", traffic_level=1.0):
    slot = _normalize_time_slot(time_slot)
    slot_profile = TRAFFIC_SLOT_MULTIPLIERS.get(slot, TRAFFIC_SLOT_MULTIPLIERS["midday"])

    highway_tag = _extract_primary_highway_tag(edge_data)
    base_multiplier = float(slot_profile.get(highway_tag, slot_profile.get("default", 1.0)))

    level = max(0.0, min(float(traffic_level), 3.0))
    adjusted_multiplier = 1.0 + (base_multiplier - 1.0) * level
    return max(0.45, adjusted_multiplier)


def _travel_time_seconds(length_meters, speed_kmph):
    if length_meters <= 0 or speed_kmph <= 0:
        return 0.0
    return length_meters / (speed_kmph * 1000.0 / 3600.0)


def _emergency_speed_multiplier(edge_data):
    highway_tag = _extract_primary_highway_tag(edge_data)
    return float(EMERGENCY_SPEED_MULTIPLIER_BY_HIGHWAY.get(highway_tag, 1.0))


def _prepare_route_graph(
    graph,
    weight_mode="distance",
    time_slot="midday",
    traffic_level=1.0,
    avg_speed_kmph=28.0,
    realtime_context=None,
    use_case="standard",
):
    route_graph = _to_weighted_digraph(graph)

    normalized_mode = (weight_mode or "distance").lower()
    if normalized_mode not in {"distance", "traffic"}:
        normalized_mode = "distance"

    normalized_use_case = (use_case or "standard").lower()
    if normalized_use_case not in {"standard", "delivery", "emergency"}:
        normalized_use_case = "standard"

    if normalized_use_case == "emergency":
        normalized_mode = "traffic"

    normalized_slot = _normalize_time_slot(time_slot)
    normalized_traffic_level = max(0.0, min(float(traffic_level), 3.0))
    normalized_avg_speed = float(avg_speed_kmph) if float(avg_speed_kmph) > 0 else 28.0

    realtime_context = realtime_context or {}
    weather_penalty_factor = max(
        1.0,
        float(realtime_context.get("weather_penalty_factor", 1.0)),
    )
    traffic_level_override = realtime_context.get("traffic_level_override")
    if traffic_level_override is not None:
        normalized_traffic_level = max(
            normalized_traffic_level,
            max(0.0, min(float(traffic_level_override), 3.0)),
        )

    for _, _, edge_data in route_graph.edges(data=True):
        length_m = float(edge_data.get("length", 0.0))
        base_speed = _base_speed_kmph_for_edge(edge_data, fallback_speed_kmph=normalized_avg_speed)
        free_flow_sec = _travel_time_seconds(length_m, base_speed)

        if normalized_mode == "traffic":
            traffic_multiplier = _traffic_multiplier_for_edge(
                edge_data,
                time_slot=normalized_slot,
                traffic_level=normalized_traffic_level,
            )
            effective_speed = max(MIN_EFFECTIVE_SPEED_KMPH, base_speed / traffic_multiplier)
        else:
            traffic_multiplier = 1.0
            effective_speed = max(MIN_EFFECTIVE_SPEED_KMPH, normalized_avg_speed)

        effective_speed = max(
            MIN_EFFECTIVE_SPEED_KMPH,
            effective_speed / weather_penalty_factor,
        )

        if normalized_use_case == "emergency":
            effective_speed = max(
                MIN_EFFECTIVE_SPEED_KMPH,
                effective_speed * _emergency_speed_multiplier(edge_data),
            )

        edge_data["base_speed_kmph"] = base_speed
        edge_data["traffic_multiplier"] = traffic_multiplier
        edge_data["effective_speed_kmph"] = effective_speed
        edge_data["free_flow_sec"] = free_flow_sec
        edge_data["weather_penalty_factor"] = weather_penalty_factor
        edge_data["use_case"] = normalized_use_case
        edge_data["travel_time_sec"] = _travel_time_seconds(length_m, effective_speed)

    weight_key = "travel_time_sec" if normalized_mode == "traffic" else "length"
    return (
        route_graph,
        weight_key,
        normalized_slot,
        normalized_traffic_level,
        normalized_use_case,
    )


def _heuristic(route_graph, node_a, node_b, as_time=False):
    a = route_graph.nodes[node_a]
    b = route_graph.nodes[node_b]
    distance_m = float(ox.distance.great_circle(a["y"], a["x"], b["y"], b["x"]))
    if as_time:
        return _travel_time_seconds(distance_m, MAX_HEURISTIC_SPEED_KMPH)
    return distance_m


def _find_path(route_graph, origin_node, destination_node, algorithm="dijkstra", weight_key="length"):
    algorithm = (algorithm or "dijkstra").lower()
    if algorithm == "astar":
        heuristic_fn = (
            lambda u, v: _heuristic(route_graph, u, v, as_time=True)
            if weight_key == "travel_time_sec"
            else _heuristic(route_graph, u, v, as_time=False)
        )
        return nx.astar_path(
            route_graph,
            origin_node,
            destination_node,
            heuristic=heuristic_fn,
            weight=weight_key,
        )

    return nx.shortest_path(route_graph, origin_node, destination_node, weight=weight_key)


def _k_shortest_paths(route_graph, origin_node, destination_node, count, weight_key="length"):
    count = max(1, int(count))
    return list(
        islice(
            nx.shortest_simple_paths(
                route_graph,
                origin_node,
                destination_node,
                weight=weight_key,
            ),
            count,
        )
    )


def _snap_distance_m(graph, point, node_id):
    node = graph.nodes[node_id]
    return float(ox.distance.great_circle(point[0], point[1], node["y"], node["x"]))


def _nearest_nodes_with_fallback(graph, start_point, end_point):
    """Find nearest nodes without requiring scikit-learn on unprojected graphs."""
    try:
        origin_node = ox.distance.nearest_nodes(graph, X=start_point[1], Y=start_point[0])
        destination_node = ox.distance.nearest_nodes(graph, X=end_point[1], Y=end_point[0])
        return origin_node, destination_node
    except Exception as exc:
        if "scikit-learn" not in str(exc).lower():
            raise

    projected_graph = ox.project_graph(graph)
    source_crs = graph.graph.get("crs")
    target_crs = projected_graph.graph.get("crs")

    transformer = pyproj.Transformer.from_crs(source_crs, target_crs, always_xy=True)
    start_x, start_y = transformer.transform(start_point[1], start_point[0])
    end_x, end_y = transformer.transform(end_point[1], end_point[0])

    origin_node = ox.distance.nearest_nodes(projected_graph, X=start_x, Y=start_y)
    destination_node = ox.distance.nearest_nodes(projected_graph, X=end_x, Y=end_y)
    return origin_node, destination_node


def estimate_travel_time_minutes(distance_meters, avg_speed_kmph=28.0):
    if avg_speed_kmph <= 0:
        return 0.0
    return (distance_meters / 1000.0) / avg_speed_kmph * 60.0


def get_route_distance(graph, path):
    """Calculate route distance in meters for DiGraph or MultiDiGraph."""
    try:
        if not path or len(path) < 2:
            return 0.0

        total_distance = 0.0
        for u, v in zip(path, path[1:]):
            edge_data = graph.get_edge_data(u, v)
            if not edge_data:
                continue

            if "length" in edge_data:
                total_distance += float(edge_data.get("length", 0.0))
            else:
                lengths = [float(data.get("length", 0.0)) for data in edge_data.values()]
                if lengths:
                    total_distance += min(lengths)

        return total_distance
    except Exception as e:
        print(f"Error calculating distance: {e}")
        return 0.0


def _get_route_travel_seconds(route_graph, path):
    travel_seconds = 0.0
    free_flow_seconds = 0.0

    for u, v in zip(path, path[1:]):
        edge_data = route_graph.get_edge_data(u, v)
        if not edge_data:
            continue
        travel_seconds += float(edge_data.get("travel_time_sec", 0.0))
        free_flow_seconds += float(edge_data.get("free_flow_sec", 0.0))

    return travel_seconds, free_flow_seconds


def calculate_routes(
    graph,
    start_point,
    end_point,
    algorithm="dijkstra",
    alternatives=0,
    avg_speed_kmph=28.0,
    weight_mode="distance",
    time_slot="midday",
    traffic_level=1.0,
    realtime_context=None,
    use_case="standard",
):
    """Calculate primary and optional alternative routes between two coordinates."""
    try:
        (
            route_graph,
            weight_key,
            normalized_slot,
            normalized_traffic_level,
            normalized_use_case,
        ) = _prepare_route_graph(
            graph,
            weight_mode=weight_mode,
            time_slot=time_slot,
            traffic_level=traffic_level,
            avg_speed_kmph=avg_speed_kmph,
            realtime_context=realtime_context,
            use_case=use_case,
        )

        origin_node, destination_node = _nearest_nodes_with_fallback(
            graph, start_point, end_point
        )

        primary_path = _find_path(
            route_graph,
            origin_node,
            destination_node,
            algorithm=algorithm,
            weight_key=weight_key,
        )

        route_count = max(1, int(alternatives) + 1)
        route_paths = [primary_path]
        if route_count > 1:
            route_paths = _k_shortest_paths(
                route_graph,
                origin_node,
                destination_node,
                route_count,
                weight_key=weight_key,
            )
            if primary_path not in route_paths:
                route_paths.insert(0, primary_path)
                route_paths = route_paths[:route_count]

        route_summaries = []
        for idx, path in enumerate(route_paths, start=1):
            distance_m = get_route_distance(route_graph, path)
            travel_seconds, free_flow_seconds = _get_route_travel_seconds(route_graph, path)
            if travel_seconds <= 0:
                travel_seconds = estimate_travel_time_minutes(
                    distance_m,
                    avg_speed_kmph=avg_speed_kmph,
                ) * 60.0

            eta_min = travel_seconds / 60.0
            avg_speed = (
                (distance_m / 1000.0) / (travel_seconds / 3600.0)
                if travel_seconds > 0
                else 0.0
            )

            route_summaries.append(
                {
                    "route_index": idx,
                    "distance_m": distance_m,
                    "distance_km": distance_m / 1000.0,
                    "eta_min": eta_min,
                    "traffic_delta_min": (travel_seconds - free_flow_seconds) / 60.0,
                    "avg_speed_kmph": avg_speed,
                    "node_count": len(path),
                }
            )

        return {
            "origin_node": origin_node,
            "destination_node": destination_node,
            "routes": route_paths,
            "summaries": route_summaries,
            "routing": {
                "weight_mode": "traffic" if weight_key == "travel_time_sec" else "distance",
                "weight_key": weight_key,
                "time_slot": normalized_slot,
                "traffic_level": normalized_traffic_level,
                "use_case": normalized_use_case,
            },
            "realtime": {
                "enabled": bool((realtime_context or {}).get("enabled", False)),
                "weather_penalty_factor": float((realtime_context or {}).get("weather_penalty_factor", 1.0)),
                "traffic_level_override": (realtime_context or {}).get("traffic_level_override"),
                "notes": list((realtime_context or {}).get("notes", [])),
            },
            "snap": {
                "start_to_node_m": _snap_distance_m(graph, start_point, origin_node),
                "end_to_node_m": _snap_distance_m(graph, end_point, destination_node),
            },
        }
    except nx.NetworkXNoPath:
        print("No drivable path found between the selected points.")
        return None
    except Exception as e:
        print(f"Error calculating path: {e}")
        return None


def calculate_shortest_path(graph, start_point, end_point, algorithm="dijkstra"):
    """Backward-compatible helper that returns only the primary path."""
    result = calculate_routes(graph, start_point, end_point, algorithm=algorithm, alternatives=0)
    if not result:
        return None
    return result["routes"][0]