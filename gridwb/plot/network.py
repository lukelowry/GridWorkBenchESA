from networkx import Graph, draw_networkx_edges, draw_networkx_nodes, relabel_nodes, selfloop_edges
from .generic import Plot


class NetworkPlot(Plot):

    def plot(self, ax):

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