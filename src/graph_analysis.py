"""Reference-independent graph descriptors and non-induced motif placements."""
from itertools import combinations
import networkx as nx

def graph_summary(n, edges):
    graph=nx.Graph();graph.add_nodes_from(range(int(n)));graph.add_edges_from(tuple(sorted(map(int,e))) for e in edges)
    degrees=dict(graph.degree())
    components=list(nx.connected_components(graph))
    connected=nx.is_connected(graph)
    return {
        "nodes":graph.number_of_nodes(),"edges":graph.number_of_edges(),
        "degree_sequence":sorted(degrees.values(),reverse=True),
        "degree_histogram":{str(k):sum(v==k for v in degrees.values()) for k in sorted(set(degrees.values()))},
        "average_degree":sum(degrees.values())/graph.number_of_nodes(),
        "density":nx.density(graph),"connected":connected,"component_sizes":sorted((len(c) for c in components),reverse=True),
        "diameter":nx.diameter(graph) if connected else None,
        "average_shortest_path_length":nx.average_shortest_path_length(graph) if connected else None,
        "average_clustering":nx.average_clustering(graph),"is_tree":nx.is_tree(graph),
    }

def motif_placements(n, edges):
    """Count distinct edge-set placements; permutations of motif vertices are collapsed.

    Placements are non-induced: extra target edges on the four selected vertices do
    not disqualify a path, cycle, or star.  Distinct motif edge sets remain distinct.
    """
    graph=nx.Graph();graph.add_nodes_from(range(int(n)));graph.add_edges_from(tuple(sorted(map(int,e))) for e in edges)
    motifs={"P4":nx.path_graph(4),"C4":nx.cycle_graph(4),"K1,3":nx.star_graph(3)}
    result={}
    for name,motif in motifs.items():
        k=motif.number_of_edges();placements=set()
        for nodes in combinations(graph.nodes,4):
            available=sorted(tuple(sorted(e)) for e in graph.subgraph(nodes).edges)
            for chosen in combinations(available,k):
                candidate=nx.Graph();candidate.add_nodes_from(nodes);candidate.add_edges_from(chosen)
                if nx.is_isomorphic(candidate,motif):
                    placements.add(tuple(sorted(chosen)))
        result[name]=len(placements)
    return result
