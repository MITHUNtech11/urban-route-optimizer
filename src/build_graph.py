import osmnx as ox

def build_graph(place_name, network_type='bike'):
    """
    Builds a graph from OpenStreetMap data for the given place.
    
    Args:
        place_name (str): Name of the place (e.g., "Kuthambakkam, Tamil Nadu, India")
        network_type (str): Type of network ('drive', 'bike', etc.)
    
    Returns:
        networkx.MultiDiGraph: The graph representing the street network
    """
    try:
        graph = ox.graph_from_place(place_name, network_type=network_type)
        # Project the graph to UTM for accurate distance calculations
        graph = ox.project_graph(graph)
        return graph
    except Exception as e:
        print(f"Error building graph: {e}")
        return None