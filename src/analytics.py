"""Urban planning analytics for route usage, hotspots, and suggestions."""

from collections import Counter, defaultdict


def _extract_primary_highway_tag(edge_data):
    highway = (edge_data or {}).get("highway")
    if isinstance(highway, str):
        return highway
    if isinstance(highway, (list, tuple)) and highway:
        return str(highway[0])
    if isinstance(highway, set) and highway:
        return str(next(iter(highway)))
    return "unknown"


def _best_edge_data(graph, u, v):
    edge_data = graph.get_edge_data(u, v)
    if not edge_data:
        return {}

    if "length" in edge_data:
        return edge_data

    return min(edge_data.values(), key=lambda data: float(data.get("length", 0.0)))


def build_route_heatmap_points(graph, routes, sample_step=5):
    """Return weighted [lat, lon, weight] points for folium HeatMap."""
    route_paths = routes or []
    if route_paths and not isinstance(route_paths[0], (list, tuple)):
        route_paths = [route_paths]

    bucket = defaultdict(float)
    for path in route_paths:
        if not path:
            continue

        for index, node_id in enumerate(path):
            if index % max(1, int(sample_step)) != 0 and index != len(path) - 1:
                continue

            node_data = graph.nodes.get(node_id)
            if not node_data:
                continue

            lat = round(float(node_data.get("y", 0.0)), 5)
            lon = round(float(node_data.get("x", 0.0)), 5)
            bucket[(lat, lon)] += 1.0

    return [[lat, lon, weight] for (lat, lon), weight in bucket.items()]


def generate_urban_insights(graph, routes):
    """Generate route-usage analytics and planning recommendations."""
    route_paths = routes or []
    if route_paths and not isinstance(route_paths[0], (list, tuple)):
        route_paths = [route_paths]

    highway_counter = Counter()
    segment_usage = defaultdict(lambda: {"uses": 0, "length_m": 0.0, "highway": "unknown"})

    traversed_segments = 0
    for path in route_paths:
        for u, v in zip(path, path[1:]):
            traversed_segments += 1
            edge_data = _best_edge_data(graph, u, v)
            highway = _extract_primary_highway_tag(edge_data)
            length_m = float(edge_data.get("length", 0.0))

            highway_counter[highway] += 1

            key = (u, v)
            entry = segment_usage[key]
            entry["uses"] += 1
            entry["length_m"] = length_m
            entry["highway"] = highway

    total_highway_edges = sum(highway_counter.values())
    highway_mix = []
    if total_highway_edges > 0:
        for highway, edge_count in highway_counter.most_common():
            highway_mix.append(
                {
                    "highway": highway,
                    "edge_count": edge_count,
                    "share_pct": round(edge_count * 100.0 / total_highway_edges, 2),
                }
            )

    unique_segments = len(segment_usage)
    overlap_pct = 0.0
    if traversed_segments > 0:
        overlap_pct = round((1.0 - (unique_segments / traversed_segments)) * 100.0, 2)

    hotspots = []
    for (u, v), entry in segment_usage.items():
        start_node = graph.nodes.get(u, {})
        end_node = graph.nodes.get(v, {})
        score = float(entry["uses"]) * max(float(entry["length_m"]), 1.0)
        hotspots.append(
            {
                "from_node": int(u),
                "to_node": int(v),
                "from_lat": float(start_node.get("y", 0.0)),
                "from_lon": float(start_node.get("x", 0.0)),
                "to_lat": float(end_node.get("y", 0.0)),
                "to_lon": float(end_node.get("x", 0.0)),
                "highway": entry["highway"],
                "uses": int(entry["uses"]),
                "length_m": round(float(entry["length_m"]), 2),
                "priority_score": round(score, 2),
            }
        )

    hotspots.sort(key=lambda row: row["priority_score"], reverse=True)
    hotspots = hotspots[:8]

    recommendations = []

    if overlap_pct >= 45.0:
        recommendations.append(
            "High route overlap detected: consider parallel connectors or reversible-lane strategies near hotspot corridors."
        )

    primary_share = 0.0
    residential_share = 0.0
    if total_highway_edges > 0:
        primary_share = (
            sum(
                count
                for highway, count in highway_counter.items()
                if highway in {"motorway", "trunk", "primary", "secondary"}
            )
            * 100.0
            / total_highway_edges
        )
        residential_share = (
            sum(
                count
                for highway, count in highway_counter.items()
                if highway in {"residential", "living_street", "service"}
            )
            * 100.0
            / total_highway_edges
        )

    if primary_share >= 50.0:
        recommendations.append(
            "Major arterials dominate route usage: evaluate adaptive signal control and bus-priority windows on top corridors."
        )

    if residential_share >= 35.0:
        recommendations.append(
            "Residential links carry heavy through-traffic: consider traffic calming and dedicated two-wheeler bypass links."
        )

    if hotspots and hotspots[0]["uses"] >= 3:
        recommendations.append(
            "Top hotspot is repeatedly used across alternatives: prioritize junction redesign or turn-lane expansion at this segment."
        )

    if not recommendations:
        recommendations.append(
            "Current route spread is balanced; monitor peak-hour demand before committing major infrastructure changes."
        )

    return {
        "overlap_pct": overlap_pct,
        "highway_mix": highway_mix,
        "hotspots": hotspots,
        "recommendations": recommendations,
    }
