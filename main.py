#!/usr/bin/env python3
"""
Urban Route Optimizer: Graph-Based Path Planning

This script calculates the most efficient path for two-wheelers in urban areas
using OpenStreetMap data and graph algorithms.
"""

import argparse
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from build_graph import build_graph
from calculate_route import calculate_shortest_path, get_route_distance
from visualize import visualize_route

def main():
    parser = argparse.ArgumentParser(description="Calculate optimal route for two-wheelers")
    parser.add_argument('--place', type=str, default="Chennai, Tamil Nadu, India",
                        help="Place name for the area")
    parser.add_argument('--start', type=str, default="13.0400,80.0100",
                        help="Start point as lat,lon")
    parser.add_argument('--end', type=str, default="13.0500,80.0200",
                        help="End point as lat,lon")
    parser.add_argument('--output', type=str, default="output/optimized_route.html",
                        help="Output HTML file path")

    args = parser.parse_args()

    # Parse coordinates
    try:
        start_lat, start_lon = map(float, args.start.split(','))
        end_lat, end_lon = map(float, args.end.split(','))
        start_point = (start_lat, start_lon)
        end_point = (end_lat, end_lon)
    except ValueError:
        print("Invalid coordinate format. Use lat,lon")
        return

    print(f"Building graph for {args.place}...")
    graph = build_graph(args.place, network_type='bike')
    if graph is None:
        return

    print("Calculating shortest path...")
    path = calculate_shortest_path(graph, start_point, end_point)
    if path is None:
        return

    distance = get_route_distance(graph, path)
    print(".2f")

    print("Generating visualization...")
    visualize_route(graph, path, args.output)

if __name__ == "__main__":
    main()