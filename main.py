import osmnx as ox
import networkx as nx
import folium

# 1. Define the local area (e.g., Kuthambakkam or your specific city region)
place_name = "Kuthambakkam, Tamil Nadu, India"
graph = ox.graph_from_place(place_name, network_type='drive')

# 2. Define Start and End coordinates (Latitude, Longitude)
start_point = (13.0400, 80.0100) # Example coords
end_point = (13.0500, 80.0200)   # Example coords

# 3. Find the nearest network nodes to the coordinates
orig_node = ox.distance.nearest_nodes(graph, X=start_point[1], Y=start_point[0])
dest_node = ox.distance.nearest_nodes(graph, X=end_point[1], Y=end_point[0])

# 4. Calculate the shortest path using NetworkX
shortest_path = nx.shortest_path(graph, orig_node, dest_node, weight='length')

# 5. Plot the route on an interactive map
route_map = ox.plot_route_folium(graph, shortest_path)
route_map.save('optimized_route.html')
print("Map saved as optimized_route.html! Open it in your browser.")