# GeoGraph: Graph theory with geometric functions as well
#
# Adam Birchfield, Texas A&M University
# 
# Log:
# 8/8/22 Created initial version
#
from scipy.spatial import Delaunay
import networkx as nx
import numpy as np

class GeoGraph:

    def __init__(self, wb):

        # Graph (Nodes: Bus, Edge: Lines)
        self.busG = nx.Graph() 
        self.busG.add_nodes_from([(b.number, dict(info=b)) for b in wb.buses])
        busedges = list(map(lambda b: (b.from_bus.number, b.to_bus.number), wb.branches))
        self.busG.add_edges_from(busedges)

        # Auxillary Info
        self.nodeInfo = nx.get_node_attributes(self.busG, "info")
        self.edgeInfo = nx.get_edge_attributes(self.busG, "info")

        # Plotting Info
        self.edgeColors = [('blue') for id in busedges]
        self.nodeColors = [('blue') for id in self.busG]
        self.pos = {id: (info.sub.longitude, info.sub.latitude) for id, info in self.nodeInfo.items()}
        
    # Add an edge post-construction
    def add_edges(self, edges):
        self.g.add_edges_from(edges)

    #Default Colors for Nodes and Branches
    def clearColors(self):
        for i in range(len(self.nodeInfo)):
            self.nodeColors[i] = (0,1,0,0.3)

        for i in range(len(self.edgeInfo)):
            self.edgeColors[i] = (0,0,1,0.3)

    # Highlight a node with a specific color
    def indicate(self, color, edge=None, node=None):
        if node:
            self.nodeColors[node-1] = color
        if edge:
            self.edgeColors[edge-1] = color

    # Plots Graph with matplotlib
    def drawGraph(self, ax=None):
        
        # Draw on specified axis
        if ax:
            nx.draw(self.busG, pos=self.pos, node_color = self.nodeColors, with_labels=True, font_weight='bold', ax=ax)
        
        # Draw on current figure
        else:
            nx.draw(self.busG, pos=self.pos, node_color = self.nodeColors, with_labels=True, font_weight='bold')


    def Delaunay(self, del_dist=1):
        nodes = list(self.g.nodes)
        points = [(self.g.nodes[n]["x"], self.g.nodes[n]["y"]) for n in nodes]
        tri = Delaunay(points)
        pairs = set()
        for simp in tri.simplices:
            pairs.add(tuple(sorted([simp[0], simp[1]])))
            pairs.add(tuple(sorted([simp[0], simp[2]])))
            pairs.add(tuple(sorted([simp[2], simp[1]])))
        edges = [(nodes[p[0]], nodes[p[1]], dict(dist=great_circle_dist(
            self.g.nodes[nodes[p[0]]]["x"], self.g.nodes[nodes[p[0]]]["y"], 
            self.g.nodes[nodes[p[1]]]["x"], self.g.nodes[nodes[p[1]]]["y"], 
            True), dela_dist=1)) for p in pairs]
            
        g = nx.Graph()
        g.add_edges_from(edges)
        g2 = nx.minimum_spanning_tree(g, weight="dist")
        edges_mst = []
        for edge in edges:
            if g2.has_edge(edge[0],edge[1]):
                edge[2]["dela_dist"] = 0
                edges_mst.append(edge)

        '''
        # MST Algorithm (Kruskals from http://algs4.cs.princeton.edu/43mst/)
        edges.sort(key=lambda e:e[2]["dist"])
        node_index = {nodes[i]:i for i in range(len(nodes))}
        parent = list(range(len(nodes)))
        rank = [0 for _ in range(len(nodes))]
        edges_mst = []
        for e in edges:
            g1 = node_index[e[0]]
            g2 = node_index[e[1]]
            while g1 != parent[g1]:
                g1 = parent[g1] = parent[parent[g1]]
            while g2 != parent[g2]:
                g2 = parent[g2] = parent[parent[g2]]
            if g1 == g2:
                continue
            if rank[g1] < rank[g2]:
                parent[g1] = g2 
            elif rank[g2] < rank[g1]:
                parent[g2] = g1
            else:
                parent[g2] = g1
                rank[g1] += 1
            e[2]["dela_dist"] = 0
            edges_mst.append(e)
'''
        if del_dist == 0:
            self.g.add_edges_from(edges_mst)
            return

        self.g.add_edges_from(edges)

        if del_dist == 1:
            return

        # BFS to find second and third neighbors
        d23edges = []
        edge_lookup = {(e[0], e[1]):e for e in edges}
        for n in self.g.nodes:
            for n1 in self.g.adj[n]:
                for n2 in self.g.adj[n1]:
                    if n2 == n:
                        continue
                    if (n, n2) in edge_lookup:
                        if edge_lookup[(n, n2)][2]["dela_dist"] == 3:
                            edge_lookup[(n, n2)][2]["dela_dist"] = 2
                    elif (n2, n) in edge_lookup:
                        if edge_lookup[(n2, n)][2]["dela_dist"] == 3:
                            edge_lookup[(n2, n)][2]["dela_dist"] = 2
                    else:
                        e = (n, n2, dict(dist=great_circle_dist(
                            self.g.nodes[n]["x"], self.g.nodes[n]["y"], 
                            self.g.nodes[n2]["x"], self.g.nodes[n2]["y"], 
                            True), dela_dist=2))
                        edge_lookup[(n, n2)] = e
                        d23edges.append(e)
                    if del_dist == 3:
                        for n3 in self.g.adj[n2]:
                            if n3 == n1 or n3 == n:
                                continue
                            if (n, n3) in edge_lookup:
                                continue
                            if (n3, n) in edge_lookup:
                                continue
                            e = (n, n3, dict(dist=great_circle_dist(
                                self.g.nodes[n]["x"], self.g.nodes[n]["y"], 
                                self.g.nodes[n3]["x"], self.g.nodes[n3]["y"], 
                                True), dela_dist=3))
                            edge_lookup[(n, n3)] = e
                            d23edges.append(e)
        self.g.add_edges_from(d23edges)


def great_circle_dist(el1, p1, el2, p2, deg=False, km=False, rearth=3959):
    if deg:
        el1 = el1*np.pi/180
        p1 = p1*np.pi/180
        el2 = el2*np.pi/180
        p2 = p2*np.pi/180
    part1 = np.power(np.sin((p2 - p1) / 2), 2)
    part2 = np.cos(p1) * np.cos(p2) * np.power(np.sin((el2 - el1) / 2), 2)
    if km: rearth *= 1.60934
    return rearth * 2 * np.arcsin(np.sqrt(part1 + part2))

def transverse_mercator(lat, lon, center_merid, deg=True, rearth=6378.137, mi=False, 
        f=0.0033528106647474805, northing_equator=0, easting_center_merid=0,
        k0=0.9996):
    if deg:
        lat = lat*np.pi/180
        lon = lon*np.pi/180
        center_merid = center_merid*np.pi/180
    if mi: rearth /= 1.60934
    n = f/(2-f)
    A = rearth/(1+n)*(1+n**2/4+n**4/64)
    alpha1 = 1/2*n-2/3*n**2+5/16*n**3
    alpha2 = 13/48*n**2-3/5*n**3
    alpha3 = 61/240*n**3
    t = np.sinh(np.arctanh(np.sin(lat)) 
        - 2*np.sqrt(n)/(1+n)*np.arctanh(2*np.sqrt(n)/(1+n)*np.sin(lat)))
    xi_prime = np.arctan(t/np.cos(lon-center_merid))
    eta_prime = np.arctanh(np.sin(lon-center_merid)/np.sqrt(1+t**2))
    easting = easting_center_merid + k0*A*(eta_prime 
        + (alpha1*np.cos(2*xi_prime)*np.sinh(2*eta_prime))
        + (alpha2*np.cos(4*xi_prime)*np.sinh(4*eta_prime))
        + (alpha3*np.cos(6*xi_prime)*np.sinh(6*eta_prime)))
    northing = northing_equator + k0*A*(xi_prime 
        + (alpha1*np.sin(2*xi_prime)*np.cosh(2*eta_prime))
        + (alpha2*np.sin(4*xi_prime)*np.cosh(4*eta_prime))
        + (alpha3*np.sin(6*xi_prime)*np.cosh(6*eta_prime)))
    return easting, northing

def transverse_mercator_inv(easting, northing, center_merid, deg=True, 
        rearth=6378.137, mi=False, f=0.0033528106647474805, northing_equator=0, 
        easting_center_merid=0, k0=0.9996):
    if deg: center_merid = center_merid*np.pi/180
    if mi: rearth /= 1.60934
    n = f/(2-f)
    A = rearth/(1+n)*(1+n**2/4+n**4/64)
    beta1 = 1/2*n-2/3*n**2+37/96*n**3
    beta2 = 1/48*n**2+1/15*n**3
    beta3 = 17/480*n**3
    delta1 = 2*n-2/3*n**2-2*n**3
    delta2 = 7/3*n**2-8/5*n**3
    delta3 = 56/15*n**3
    xi = (northing - northing_equator) / (k0*A)
    eta = (easting - easting_center_merid) / (k0*A)
    xi_prime = xi - (
        + (beta1*np.sin(2*xi)*np.cosh(2*eta))
        + (beta2*np.sin(4*xi)*np.cosh(4*eta))
        + (beta3*np.sin(6*xi)*np.cosh(6*eta)))
    eta_prime = eta - (
        + (beta1*np.cos(2*xi)*np.sinh(2*eta))
        + (beta2*np.cos(4*xi)*np.sinh(4*eta))
        + (beta3*np.cos(6*xi)*np.sinh(6*eta)))
    chi = np.arcsin(np.sin(xi_prime)/np.cosh(eta_prime))
    lat = chi + (
        + (delta1*np.sin(2*chi))
        + (delta2*np.sin(4*chi))
        + (delta3*np.sin(6*chi)))
    lon = center_merid + np.arctan(np.sinh(eta_prime) / np.cos(xi_prime))
    if deg: 
        lat = lat*180/np.pi
        lon = lon*180/np.pi
    return lat, lon

def pick_utm_zone(lat, lon, deg=True):
    if not deg:
        lat = lat*180/np.pi
        lon = lon*180/np.pi
    if lat < -80: lat_band = "A" if lon < 0 else "B"
    elif lat > 84: lat_band = "Y" if lon < 0 else "Z"
    else: lat_band = "CDEFGHJKLMNPQRSTUVWXX"[int(np.floor((lat + 80) / 8))]
    lon_band = int(np.floor((lon + 180)/6)+1)
    if lat_band == "V" and lon_band == 31 and lon >= 3:
        lon_band = 32
    if lat_band == "X" and 0 <= lon <= 42:
        if lon < 9: lon_band = 31
        elif lon < 21: lon_band = 33
        elif lon < 33: lon_band = 37
    zone = str(lon_band) + lat_band
    return zone

def interpret_utm_zone(zone):
    lat_band = zone[-1]
    if lat_band.lower() in "cdefghjklm":
        northing_equator = 10000
    elif lat_band.lower() in "npqrstuvwx":
        northing_equator = 0
    else:
        raise NotImplementedError(f"Latitude band {lat_band} not allowed!")
    lon_band = int(zone[:-1])
    center_merid = (-183 + 6*lon_band)
    easting_center_merid = 500
    return center_merid, northing_equator, easting_center_merid

def utm(lat, lon, zone=None, deg=True):
    if not deg:
        lat = lat*180/np.pi
        lon = lon*180/np.pi
    zone2 = pick_utm_zone(lat, lon) if zone is None else zone
    center_merid, northing_equator, easting_center_merid = interpret_utm_zone(zone2)
    easting, northing = transverse_mercator(lat, lon, center_merid, deg=True,
        northing_equator=northing_equator, easting_center_merid=easting_center_merid)
    if zone is None: return zone2, easting*1000, northing*1000
    else: return easting*1000, northing*1000

def utm_inv(zone, easting, northing, deg=True):
    center_merid, northing_equator, easting_center_merid = interpret_utm_zone(zone)
    lat, lon = transverse_mercator_inv(easting/1000, northing/1000, center_merid, 
        northing_equator=northing_equator, easting_center_merid=easting_center_merid,
        deg=True)
    if not deg: 
        lat = lat*np.pi/180
        lon = lon*np.pi/180
    return lat, lon


def ccw(v1,v2,v3):
    tri_area = (v2[0]-v1[0])*(v3[1]-v1[1])-(v3[0]-v1[0])*(v2[1]-v1[1])
    return tri_area > 0

def intersect_bool(x1,y1,x2,y2,x3,y3,x4,y4):
    return not ((x1==x3 and y1==y3) or (x1==x4 and y1==y4) \
        or (x2==x3 and y2==y3) or (x2==x4 and x2==y4) \
        or ccw((x1,y1),(x3,y3),(x4,y4)) == ccw((x2,y2),(x3,y3),(x4,y4)) \
        or ccw((x1,y1),(x2,y2),(x3,y3)) == ccw((x1,y1),(x2,y2),(x4,y4)))

def calc_intersection(x1,y1,x2,y2,x3,y3,x4,y4):
    if not intersect_bool(x1,y1,x2,y2,x3,y3,x4,y4): return None
    if x1 == x2 and x3 == x4: return None # Parallel, should be unncessary
    if x1 == x2:
        m2 = (y3-y4)/(x3-x4)
        xm = x1
        ym = y3 + m2*(xm-x3)
        return xm, ym
    if x3 == x4:
        m1 = (y1-y2)/(x1-x2)
        xm = x3
        ym = y1 + m1*(xm-x1)
        return xm, ym
    m1 = (y1-y2)/(x1-x2)
    m2 = (y3-y4)/(x3-x4)
    if m1 == m2: return None # Parallel lines (shouldn't get here)
    xm = (y3-y1+m1*x1-m2*x3)/(m1-m2)
    ym = y1+m1*(xm-x1)
    return xm,ym
    