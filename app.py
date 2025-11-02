from flask import Flask, render_template, request, jsonify
import os
import requests
import math
from typing import List, Dict, Tuple, Set

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# OSRM API configuration
OSRM_API_URL = "http://router.project-osrm.org"  # Public OSRM instance


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth using Haversine formula.
    Returns distance in kilometers.
    """
    R = 6371  # Earth's radius in kilometers
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(dlon / 2) ** 2)
    
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def get_distance_osrm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Get distance between two points using OSRM API.
    Falls back to Haversine if OSRM fails.
    """
    try:
        # OSRM API expects [lon, lat] format
        response = requests.get(
            f"{OSRM_API_URL}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}",
            params={"overview": "false"},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == "Ok" and len(data.get("routes", [])) > 0:
                # Distance in meters
                return data["routes"][0]["distance"] / 1000  # Convert to km
    except Exception as e:
        print(f"OSRM API error: {e}")
    
    # Fallback to Haversine
    return haversine_distance(lat1, lon1, lat2, lon2)


def get_route_geometry_osrm(lat1: float, lon1: float, lat2: float, lon2: float) -> List[List[float]]:
    """
    Get detailed route geometry between two points using OSRM API.
    Falls back to straight line if OSRM fails.
    
    Returns:
        List of [lat, lon] coordinates representing the route
    """
    try:
        # OSRM API expects [lon, lat] format
        response = requests.get(
            f"{OSRM_API_URL}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}",
            params={"overview": "full", "geometries": "geojson"},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == "Ok" and len(data.get("routes", [])) > 0:
                # Get geometry coordinates in GeoJSON format [lon, lat]
                geometry = data["routes"][0]["geometry"]["coordinates"]
                # Convert to [lat, lon] format
                return [[coord[1], coord[0]] for coord in geometry]
    except Exception as e:
        print(f"OSRM route geometry error: {e}")
    
    # Fallback to straight line
    return [[lat1, lon1], [lat2, lon2]]


def build_distance_matrix(coords: List[List[float]]) -> List[List[float]]:
    """
    Build a distance matrix between all pairs of coordinates.
    Returns a 2D list where matrix[i][j] = distance between coord i and coord j.
    """
    n = len(coords)
    matrix = [[0.0 for _ in range(n)] for _ in range(n)]
    
    for i in range(n):
        for j in range(i + 1, n):
            lat1, lon1 = coords[i]
            lat2, lon2 = coords[j]
            distance = get_distance_osrm(lat1, lon1, lat2, lon2)
            matrix[i][j] = distance
            matrix[j][i] = distance  # Symmetric matrix
    
    return matrix


class Graph:
    """Adjacency list representation of a graph."""
    
    def __init__(self, num_vertices: int):
        self.num_vertices = num_vertices
        self.adj = {i: [] for i in range(num_vertices)}
    
    def add_edge(self, u: int, v: int, weight: float):
        """Add undirected edge between vertices u and v with given weight."""
        self.adj[u].append((v, weight))
        self.adj[v].append((u, weight))
    
    def get_neighbors(self, u: int) -> List[Tuple[int, float]]:
        """Get all neighbors of vertex u with their edge weights."""
        return self.adj[u]


def dijkstra(graph: Graph, start: int, end: int) -> Tuple[List[int], float]:
    """
    Dijkstra's algorithm to find shortest path from start to end.
    Returns (path, distance).
    """
    distances = [float('inf')] * graph.num_vertices
    previous = [None] * graph.num_vertices
    visited = set()
    distances[start] = 0
    
    while len(visited) < graph.num_vertices:
        # Find unvisited vertex with minimum distance
        u = None
        min_dist = float('inf')
        for i in range(graph.num_vertices):
            if i not in visited and distances[i] < min_dist:
                min_dist = distances[i]
                u = i
        
        if u is None or u == end:
            break
        
        visited.add(u)
        
        # Update distances to neighbors
        for v, weight in graph.get_neighbors(u):
            if v not in visited:
                alt = distances[u] + weight
                if alt < distances[v]:
                    distances[v] = alt
                    previous[v] = u
    
    # Reconstruct path
    path = []
    u = end
    while u is not None:
        path.insert(0, u)
        u = previous[u]
    
    return path, distances[end]


def prim_mst(graph: Graph) -> List[Tuple[int, int]]:
    """
    Prim's algorithm to find Minimum Spanning Tree.
    Returns list of edges in the MST.
    """
    n = graph.num_vertices
    visited = set()
    mst_edges = []
    
    # Start with vertex 0
    visited.add(0)
    
    while len(visited) < n:
        min_edge = None
        min_weight = float('inf')
        
        # Find minimum edge connecting visited to unvisited
        for u in visited:
            for v, weight in graph.get_neighbors(u):
                if v not in visited and weight < min_weight:
                    min_weight = weight
                    min_edge = (u, v)
        
        if min_edge is None:
            break
        
        mst_edges.append(min_edge)
        visited.add(min_edge[1])
    
    return mst_edges


def dfs_traversal(mst_edges: List[Tuple[int, int]], start: int) -> List[int]:
    """
    DFS traversal of MST to generate visiting order.
    Returns list of vertices in DFS order.
    """
    # Build adjacency list from MST edges
    adj = {i: [] for i in range(len(mst_edges) + 1)}
    for u, v in mst_edges:
        adj[u].append(v)
        adj[v].append(u)
    
    visited = set()
    traversal_order = []
    
    def dfs(u: int):
        if u in visited:
            return
        visited.add(u)
        traversal_order.append(u)
        for v in adj[u]:
            dfs(v)
    
    dfs(start)
    return traversal_order


def plan_route(coords: List[List[float]]) -> Dict:
    """
    Main route planning function using Dijkstra, Prim, and DFS.
    
    Args:
        coords: List of [lat, lon] pairs
    
    Returns:
        Dictionary with visiting order, route coordinates, and total distance
    """
    if len(coords) < 2:
        return {
            "visiting_order": [0],
            "route_coords": [coords[0]],
            "total_distance": 0,
            "road_segments": []
        }
    
    # Step 1: Build distance matrix
    print("Building distance matrix...")
    distance_matrix = build_distance_matrix(coords)
    
    # Step 2: Create graph from distance matrix
    graph = Graph(len(coords))
    for i in range(len(coords)):
        for j in range(len(coords)):
            if i != j:
                graph.add_edge(i, j, distance_matrix[i][j])
    
    # Step 3: Generate MST using Prim's algorithm
    print("Generating MST using Prim's algorithm...")
    mst_edges = prim_mst(graph)
    
    # Step 4: DFS traversal to get visiting order
    print("Performing DFS traversal...")
    visiting_order = dfs_traversal(mst_edges, 0)
    
    # Step 5: Calculate total distance using Dijkstra for each segment
    print("Computing path distances...")
    total_distance = 0
    route_coords = []
    
    for i in range(len(visiting_order)):
        current = visiting_order[i]
        route_coords.append(coords[current])
        
        if i < len(visiting_order) - 1:
            next_node = visiting_order[i + 1]
            _, dist = dijkstra(graph, current, next_node)
            total_distance += dist
    
    # Step 6: Get real road geometries using OSRM
    print("Fetching road geometries...")
    road_segments = []
    
    for i in range(len(visiting_order) - 1):
        current_idx = visiting_order[i]
        next_idx = visiting_order[i + 1]
        
        lat1, lon1 = coords[current_idx]
        lat2, lon2 = coords[next_idx]
        
        # Get OSRM route geometry for this segment
        segment_geometry = get_route_geometry_osrm(lat1, lon1, lat2, lon2)
        road_segments.append(segment_geometry)
    
    return {
        "visiting_order": visiting_order,
        "route_coords": route_coords,
        "total_distance": round(total_distance, 2),
        "road_segments": road_segments
    }


@app.route("/")
def index():
    """Serve the main HTML page."""
    return render_template("index.html")


@app.route("/plan_route", methods=["POST"])
def plan_route_endpoint():
    """
    Backend endpoint for route planning.
    Expects: {"coordinates": [[lat1, lon1], [lat2, lon2], ...]}
    Returns: {"visiting_order": [...], "route_coords": [...], "total_distance": ...}
    """
    try:
        data = request.get_json()
        coords = data.get("coordinates", [])
        
        if len(coords) < 2:
            return jsonify({
                "error": "Please select at least 2 tourist spots",
                "visiting_order": [0],
                "route_coords": coords[:1] if coords else [],
                "total_distance": 0
            }), 400
        
        # Plan route using the core algorithms
        result = plan_route(coords)
        
        return jsonify({
            "success": True,
            "visiting_order": result["visiting_order"],
            "route_coords": result["route_coords"],
            "total_distance": result["total_distance"],
            "road_segments": result.get("road_segments", [])
        })
    
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
