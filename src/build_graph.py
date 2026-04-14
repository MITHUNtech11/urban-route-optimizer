from pathlib import Path
import re

import networkx as nx
import osmnx as ox


PROFILE_TO_NETWORK_TYPE = {
    "scooter": "drive",
    "bike": "bike",
    "drive": "drive",
}

SCOOTER_EXCLUDED_HIGHWAY_TYPES = {
    "motorway",
    "motorway_link",
    "trunk",
    "trunk_link",
    "footway",
    "path",
    "steps",
    "cycleway",
    "pedestrian",
}


def _safe_slug(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def list_cached_graphs(cache_dir="data", profile=None):
    """List locally available graphml files for offline use."""
    cache_folder = Path(cache_dir)
    if not cache_folder.exists():
        return []

    profile = (profile or "").strip().lower()
    pattern = "*.graphml" if not profile else f"*-{profile}.graphml"
    return sorted(cache_folder.glob(pattern))


def _as_tag_set(tag_value):
    if isinstance(tag_value, str):
        return {tag_value}
    if isinstance(tag_value, (list, tuple, set)):
        return {str(item) for item in tag_value}
    return set()


def _filter_for_scooter(graph):
    edges_to_remove = []
    for u, v, key, data in graph.edges(keys=True, data=True):
        highway_tags = _as_tag_set(data.get("highway"))
        if highway_tags.intersection(SCOOTER_EXCLUDED_HIGHWAY_TYPES):
            edges_to_remove.append((u, v, key))

    if edges_to_remove:
        graph.remove_edges_from(edges_to_remove)

    # Remove isolated nodes after edge filtering.
    isolated_nodes = list(nx.isolates(graph))
    if isolated_nodes:
        graph.remove_nodes_from(isolated_nodes)

    return graph


def build_graph(
    place_name,
    profile="scooter",
    use_cache=True,
    cache_dir="data",
    offline=False,
    graph_file=None,
):
    """Build a route graph for the given place and mobility profile.

    The returned graph stays in latitude/longitude CRS so nearest-node queries
    and Folium visualization can use user-provided coordinates directly.
    """
    try:
        profile = (profile or "scooter").lower()
        network_type = PROFILE_TO_NETWORK_TYPE.get(profile, "drive")

        cache_folder = Path(cache_dir)
        cache_folder.mkdir(parents=True, exist_ok=True)
        cache_graph_file = cache_folder / f"{_safe_slug(place_name)}-{profile}.graphml"

        selected_graph_file = Path(graph_file) if graph_file else cache_graph_file

        if selected_graph_file.exists():
            graph = ox.load_graphml(selected_graph_file)
            print(f"Loaded cached graph: {selected_graph_file}")
            return graph

        if offline:
            fallback_candidates = list_cached_graphs(cache_dir=cache_dir, profile=profile)
            if fallback_candidates:
                fallback_graph_file = fallback_candidates[0]
                graph = ox.load_graphml(fallback_graph_file)
                print(
                    "Offline mode: requested graph not found, "
                    f"using fallback cache '{fallback_graph_file.name}'"
                )
                return graph

            print(
                "Offline mode enabled, but no local graph cache was found. "
                "Disable offline mode or provide a valid --graph-file path."
            )
            return None

        print(f"Downloading OSM network for '{place_name}' using profile '{profile}'...")
        graph = ox.graph_from_place(place_name, network_type=network_type, simplify=True)

        if profile == "scooter":
            graph = _filter_for_scooter(graph)

        if use_cache:
            ox.save_graphml(graph, cache_graph_file)
            print(f"Saved graph cache: {cache_graph_file}")

        return graph
    except Exception as e:
        print(f"Error building graph: {e}")
        return None