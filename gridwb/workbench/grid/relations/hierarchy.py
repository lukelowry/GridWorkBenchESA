from ...utils.exceptions import GridObjDNE
from ..components import *

from matplotlib import pyplot as plt
from typing import Iterator, Type, TypeVar
from networkx import *

TO = TypeVar('TO', bound=TieredObject)

# Custom DiGraph representing a Heriarchy
# A 'Workspace' can be set to limit scope of operations
class Hierarchy(DiGraph):

    # All direct TieredObject inhertors should be given value here
    precedence: list[TieredObject] = [
        Region,
        Area,
        Sub,
        Bus,
        Device
    ]

    def __init__(self, incoming_graph_data=None, **attr):
        super().__init__(incoming_graph_data, **attr)

        # Empty byTier Dict
        self.byTier: dict[int, list[TieredObject]] = {t: [] for t in range(len(self.precedence))}
        self.color_key = Sub
        self.labels=self.nodes # Drawn Node Labels

    """
    Heirarchy Functions -----------------------
    """
    # Return tier of a node (Only used at assignemnt, then assigned to node)
    def tier(self, node: TieredObject) -> int:
        for tier, precType in enumerate(self.precedence):
            if isinstance(node, precType):
                return tier
    
    # Return Tier of a type
    def tierOfType(self, nType: Type[TieredObject]) -> int:
        for tier, precType in enumerate(self.precedence):
            if issubclass(nType, precType):
                return tier
            
    # Get list of nodes in the tier below a given node
    def tierBelow(self, node: TieredObject) -> list[TieredObject]:
        if node.tier != len(self.byTier)-1:
            yield from self.byTier[node.tier+1]
            
    # Get list of nodes in the tier above a given node
    def tierAbove(self, node: TieredObject) -> list[TieredObject]:
        if node.tier != 0:
            yield from self.byTier[node.tier-1]

    # Returns iterator of neighrs as (parent, child) pair
    def dualAdj(self, node: TieredObject):

        for above in self.tierAbove(node):
            yield (above, node)

        for below in self.tierBelow(node):
            yield (node, below)
    
    def lineage(self, node: TieredObject):
        yield from ancestors(self, node)
        yield self
        yield from descendants(self, node)

    #TODO this will be 'synced' with main graph per api
    def subHierarchy(self, container: TieredObject):
        subEdges = self.edges(nbunch=[container,*descendants(self,container)])
        return self.edge_subgraph(subEdges)
    
    # Add node(s) to True Hierarchy & Update Workspace if user is in one
    def add(self, *nodes: TieredObject):

        # For each element to be added
        for node in nodes:
            
            # Assign Tier to Obj
            node.tier = self.tier(node)

            # Add to 'byTier' dict
            self.byTier[node.tier].append(node)

            # Add Node to Hierarchy 
            self.add_node(node)

            # Add Tier Relations
            for parent, child in self.dualAdj(node):
                if parent.id == child.container_id:
                    self.add_edge(parent, child)

    # Get Node in Workspace of Type (WONT WORK BC DEVICE BY BUS)
    def get(self, nType: Type[TO], key: any=None) -> TO:
        
        # Look through respective tier to mitigate runtime
        for node in self.byTier[self.tierOfType(nType)]:
            if isinstance(node, nType):
                if isinstance(key, int) and node.id==key:
                    return node
                elif isinstance(key, str) and node.name==key:
                    return node
        
        raise GridObjDNE
    
    # Get all nodes of type T in Heriarchy Workspace (return iter)
    def getAll(self, nType: Type[TO]) -> Iterator[TO]:
        for node in self.byTier[self.tierOfType(nType)]:
            if isinstance(node, nType):
                yield node
    
    # Direct Ancestor -> None i
    def parent(self, node: TieredObject) -> TieredObject:
        if self.has_predecessor:
            return list(self.pred[node])[0]
        return None
    
    # Returns first predecessor of type pType and None if it doesn't exists
    # if include_self is true then it will reder node if node is pType
    def up(self, node: TieredObject, pType: Type[TO], include_self=False) -> TO | None:
        for a in ancestors(self, node):
            if isinstance(a, pType):
                return a
        return node if isinstance(node, pType) and include_self else None
    
    #TODO
    #ADJACENCY FUNCTION adjaceny() would return direct child of each node
    
    """
    DRAWING FUNCTIONS ---------------------------------------------
    """

    # Node Positioning in Plot
    def pos(self):

        # Start from MultiPartition Layout
        tMap = {n: n.tier for n in self}
        set_node_attributes(self, tMap, 'subset')
        pos = multipartite_layout(self)
        
        # Helper Functions
        x = lambda n: pos[n][0]
        y = lambda n: pos[n][1]
        parentX = lambda n: x(self.parent(n))
        parentY = lambda n: y(self.parent(n))
        
        def setX(n, x):
            pos[n][0] = x
        def setY(n, y):
            pos[n][1] = y

        # Iteraters and Values to Use
        self._depthTitles = {}

        # Height Targets
        topNode = lambda g: max(g, key=y)
        yMax = y(topNode(self))
        yMax = 1 if yMax==0 else yMax #Branchess Scenario

        # For each layer in Hierarchy
        for depth, depthNodes in self.byTier.items():

            # Current logic assumes 'root' is singular
            if depth != 0:

                # Stretch every layer to be same height if possible
                depthHeight = y(topNode(depthNodes))
                for node in depthNodes:
                    if len(depthNodes) == 0:
                        setY(node, parentY(node))
                    else:
                        setY(node, y(node)*yMax/depthHeight if depthHeight !=0 else depthHeight)

                # Layer Order so hierarchy lines do not overlap
                oldOrder = sorted(depthNodes, key=y, reverse=True)
                newOrder = sorted(depthNodes, key=parentY, reverse=True)
                for dev, height  in zip(newOrder, list(map(y, oldOrder))):
                    setY(dev, height)

                # Horizontal Spacing for Display ratio (otherwise really skinny)
                prevX = parentX(depthNodes[0])
                for node in depthNodes:
                    setX(node, yMax + prevX)

            # Set Text and position of layer title
            self._depthTitles[topNode(depthNodes)] = Device.text if isinstance(n:=depthNodes[0], Device) else n.text
        
        return pos
    
    # Draw the Node Labels (Overwritting Default Labels)
    #TODO Linear Hierarchy doesn't plot labels because ylim becomes really small :( to much work to figure out
    def drawLabels(self, pos, ax):

        depthGroups = self.byTier
        for depth, depthGroup in depthGroups.items():

            for node in depthGroup:
                if isinstance(node, Device):
                    t = f'{node.text}: {self.labels[node]}'
                    ax.text(pos[node][0]+0.06,pos[node][1],s=t,horizontalalignment='left', weight='bold')
                else:
                    ax.text(pos[node][0],pos[node][1]-0.05,s=self.labels[node],horizontalalignment='center', weight='bold')

    # Set node label text with a function that will return text for a given node
    def setLabels(self, func: function):
        self.labels = {n: func(n) for n in self}

    # Draw the Heriarchhy Workspace on a specified ax
    def draw(self, ax):

        # Positioning
        pos = self.pos()

        # Color
        key = lambda n: self.up(n, self.color_key, True)

        # Node Color as Tier Attribute
        node_colors = {n: 0 if (k:=key(n)) is None else pos[k][1] for n in self}
        set_node_attributes(self, node_colors, "color_key")

        # Tier Assignment Color
        edge_colors = [0 if (k:=key(u)) is None else pos[k][1] for u,v in self.edges]

        # Titles
        for top, text in self._depthTitles.items():
            topY = pos[top][1]*1.1 if pos[top][1] !=0 else ax.get_ylim()[1]*0.2
            ax.text(pos[top][0],topY,s=text,horizontalalignment='center', weight='bold')
        
        # Draw
        #self.drawLabels(pos, ax) Node Labels (slow render if enabled)
        draw_networkx_nodes(self, pos, edgecolors='k', node_size=100, node_color=list(node_colors.values()), cmap=plt.cm.viridis,ax=ax)
        draw_networkx_edges(self, pos, edge_color=edge_colors, edge_cmap=plt.cm.viridis,ax=ax)
    