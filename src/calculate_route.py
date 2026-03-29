import networkx as nx
import osmnx as ox

def calculate_shortest_path(graph, start_point, end_point):
    """
    Calculates the shortest path between two points using NetworkX.
    
    Args:
        graph: The street network graph
        start_point (tuple): (lat, lon) of start
        end_point (tuple): (lat, lon) of end
    
    Returns:
        list: List of node IDs representing the path
    """
    try:
        orig_node = ox.distance.nearest_nodes(graph, X=start_point[1], Y=start_point[0])
        dest_node = ox.distance.nearest_nodes(graph, X=end_point[1], Y=end_point[0])
        shortest_path = nx.shortest_path(graph, orig_node, dest_node, weight='length')
        return shortest_path
    except Exception as e:
        print(f"Error calculating path: {e}")
        return None

def get_route_distance(graph, path):
    """
    Calculates the total distance of the route.
    
    Args:
        graph: The street network graph
        path: List of node IDs
    
    Returns:
        float: Total distance in meters
    """
    try:
        route_edges = ox.utils_graph.get_route_edge_attributes(graph, path)
        total_distance = sum(edge['length'] for edge in route_edges)
        return total_distance
    except Exception as e:
        print(f"Error calculating distance: {e}")
        return 0