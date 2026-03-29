import osmnx as ox
import folium

def visualize_route(graph, path, output_file='output/optimized_route.html'):
    """
    Visualizes the route on an interactive map and saves it.
    
    Args:
        graph: The street network graph
        path: List of node IDs
        output_file (str): Path to save the HTML file
    """
    try:
        route_map = ox.plot_route_folium(graph, path)
        route_map.save(output_file)
        print(f"Map saved as {output_file}! Open it in your browser.")
    except Exception as e:
        print(f"Error visualizing route: {e}")