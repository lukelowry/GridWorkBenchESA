from .hierarchy import *
from ..components import *

# Custom Graph representing Electrical Connection Network
# 'Node' can be transformed to any Heirarchy Depth
# 'Branch' is edges between 'Node' (which is a function of specified depth)
class GridNetwork(Graph):

    # Initialize with a Grid Heirarchy (Will update if H is updapted :) )
    def __init__(self, incoming_graph_data=None, **attr):
        super().__init__(incoming_graph_data, **attr)
        self.color_key = Sub
        self._indicateMap = {}

    def setHierarchy(self, H: Hierarchy):
        self.H = H

    # Raw Connections are always given as Bus -> Bus
    def addBranch(self, branch: Branch) -> None:
        self.add_edge(branch.from_bus, branch.to_bus, branch=branch)

    def sub(self, bus: Bus) -> Sub:
        return self.H.parent(bus)

    # Return substation pos for a given node
    def subPos(self, node):
        s = self.H.up(node, Sub, True)
        return (s.longitude, s.latitude)
    
    def resetColor(self):
        self._indicateMap = {}
    
    def indicate(self, node, color):
        node = self.H.get(Bus, node) #temp, due to old code
        self._indicateMap[node] = color
    
    # right now its jsut drawing buses in same sub station over each other
    def draw(self, ax):

        #Temp Map graph to Substation Here
        Gx: Graph = relabel_nodes(
            self,
            {bus: self.sub(bus) for bus in self}
        )
        # Remove merged lines (useful in future for 'clusters' or thev eq)
        Gx.remove_edges_from(selfloop_edges(Gx))
        
        # Node Visual Properties
        pos = {n: self.subPos(n) for n in Gx}
        node_colors = {n: 'blue' for n in Gx}
        node_sizes = {n: 40 for n in Gx}

        # Set Indicated Node to Mapped Indication Color
        for bus, color in self._indicateMap.items():
            sub = self.sub(bus)
            node_colors[sub] = color
            node_sizes[sub] = 120
        

        # Draw Nodes, labels, edges
        draw_networkx_nodes(Gx, pos, edgecolors='k', ax=ax,
                            node_color=list(node_colors.values()),
                            node_size=list(node_sizes.values()))
        draw_networkx_edges(Gx, pos, ax=ax)
    


        """
        Gx: Graph = relabel_nodes(
            self.G,
            {bus: self.parent(bus, Sub) for bus in self.buses()}
        )
        # Remove merged lines (useful in future for thev eq)
        Gx.remove_edges_from(selfloop_edges(Gx))
        """