"""Specialized routing workflows (delivery and emergency helpers)."""

from src.calculate_route import calculate_routes


def optimize_delivery_route(
    graph,
    start_point,
    stop_points,
    algorithm="dijkstra",
    avg_speed_kmph=28.0,
    weight_mode="traffic",
    time_slot="midday",
    traffic_level=1.0,
    realtime_context=None,
    return_to_start=False,
):
    """Greedy nearest-next-stop delivery optimization with route leg outputs."""
    remaining_stops = [tuple(stop) for stop in (stop_points or [])]
    if not remaining_stops:
        return None

    ordered_stops = []
    leg_results = []
    unreachable_stops = []

    current_point = tuple(start_point)

    while remaining_stops:
        best_index = None
        best_result = None
        best_eta = None

        for index, candidate_stop in enumerate(remaining_stops):
            result = calculate_routes(
                graph=graph,
                start_point=current_point,
                end_point=candidate_stop,
                algorithm=algorithm,
                alternatives=0,
                avg_speed_kmph=avg_speed_kmph,
                weight_mode=weight_mode,
                time_slot=time_slot,
                traffic_level=traffic_level,
                realtime_context=realtime_context,
                use_case="delivery",
            )
            if not result:
                continue

            eta = float(result["summaries"][0]["eta_min"])
            if best_eta is None or eta < best_eta:
                best_eta = eta
                best_index = index
                best_result = result

        if best_index is None or not best_result:
            unreachable_stops.extend(remaining_stops)
            break

        chosen_stop = remaining_stops.pop(best_index)
        ordered_stops.append(chosen_stop)
        leg_results.append(
            {
                "from_point": current_point,
                "to_point": chosen_stop,
                "route_result": best_result,
            }
        )
        current_point = chosen_stop

    if return_to_start and not unreachable_stops and leg_results:
        return_leg = calculate_routes(
            graph=graph,
            start_point=current_point,
            end_point=tuple(start_point),
            algorithm=algorithm,
            alternatives=0,
            avg_speed_kmph=avg_speed_kmph,
            weight_mode=weight_mode,
            time_slot=time_slot,
            traffic_level=traffic_level,
            realtime_context=realtime_context,
            use_case="delivery",
        )
        if return_leg:
            leg_results.append(
                {
                    "from_point": current_point,
                    "to_point": tuple(start_point),
                    "route_result": return_leg,
                }
            )

    if not leg_results:
        return None

    routes = []
    summaries = []
    total_distance_m = 0.0
    total_eta_min = 0.0

    for leg_index, leg in enumerate(leg_results, start=1):
        summary = leg["route_result"]["summaries"][0]
        routes.append(leg["route_result"]["routes"][0])

        total_distance_m += float(summary["distance_m"])
        total_eta_min += float(summary["eta_min"])

        summaries.append(
            {
                "route_index": leg_index,
                "route_label": f"Leg {leg_index}",
                "distance_m": float(summary["distance_m"]),
                "distance_km": float(summary["distance_km"]),
                "eta_min": float(summary["eta_min"]),
                "traffic_delta_min": float(summary.get("traffic_delta_min", 0.0)),
                "avg_speed_kmph": float(summary.get("avg_speed_kmph", 0.0)),
                "node_count": int(summary["node_count"]),
                "from_point": leg["from_point"],
                "to_point": leg["to_point"],
            }
        )

    first_leg = leg_results[0]["route_result"]
    last_leg = leg_results[-1]["route_result"]

    return {
        "origin_node": first_leg.get("origin_node"),
        "destination_node": last_leg.get("destination_node"),
        "routes": routes,
        "summaries": summaries,
        "routing": {
            "weight_mode": first_leg.get("routing", {}).get("weight_mode", weight_mode),
            "weight_key": first_leg.get("routing", {}).get("weight_key", "length"),
            "time_slot": first_leg.get("routing", {}).get("time_slot", time_slot),
            "traffic_level": first_leg.get("routing", {}).get("traffic_level", traffic_level),
            "use_case": "delivery",
        },
        "snap": {
            "start_to_node_m": first_leg.get("snap", {}).get("start_to_node_m", 0.0),
            "end_to_node_m": last_leg.get("snap", {}).get("end_to_node_m", 0.0),
        },
        "delivery": {
            "ordered_stops": ordered_stops,
            "unreachable_stops": unreachable_stops,
            "total_legs": len(leg_results),
            "total_distance_km": round(total_distance_m / 1000.0, 3),
            "total_eta_min": round(total_eta_min, 2),
            "return_to_start": bool(return_to_start),
        },
    }
