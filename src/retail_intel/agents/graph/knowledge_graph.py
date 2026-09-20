"""Enterprise Retail Property Knowledge Graph built on NetworkX with rich entity relationships."""

from typing import Any, Dict, List, Optional

import networkx as nx
from pydantic import BaseModel

from retail_intel.core.logging import get_logger

logger = get_logger("agents.graph")


class GraphNode(BaseModel):
    id: str
    label: str  # "Internal_SKU", "Competitor_SKU", "Brand", "Parent_Company", "OEM_Factory"
    properties: Dict[str, Any]


class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str  # "MAPS_TO", "SUBSIDIARY_OF", "MANUFACTURED_BY", "SHARED_PATENT"
    properties: Dict[str, Any]


class RetailKnowledgeGraph:
    """Enterprise Retail Knowledge Graph anchoring entity resolution and strategic inference."""

    def __init__(self):
        self.graph = nx.MultiDiGraph()
        self._initialize_seed_graph()

    def _initialize_seed_graph(self) -> None:
        """Populates seed knowledge graph with parent companies, brands, and OEM factory nodes."""
        # 1. Parent Companies & Brands
        self.add_node("PARENT-HORIZON", "Parent_Company", {"name": "Horizon Consumer Goods Global"})
        self.add_node("BRAND-AURA", "Brand", {"name": "AuraWave", "tier": "Premium Audio"})
        self.add_node("BRAND-VORTEX", "Brand", {"name": "VortexView", "tier": "Cinema Visuals"})
        self.add_node("BRAND-ERGO", "Brand", {"name": "ErgoSpine", "tier": "Executive Furniture"})
        self.add_node("BRAND-NOVA", "Brand", {"name": "NovaComfort", "tier": "Direct-to-Consumer Value"})

        self.add_edge("BRAND-AURA", "PARENT-HORIZON", "SUBSIDIARY_OF", {"acquired_year": 2021})
        self.add_edge("BRAND-VORTEX", "PARENT-HORIZON", "SUBSIDIARY_OF", {"acquired_year": 2019})
        self.add_edge("BRAND-NOVA", "PARENT-HORIZON", "SUBSIDIARY_OF", {"acquired_year": 2024, "type": "Private Label Line"})

        # 2. OEM Manufacturing Nodes
        self.add_node("OEM-AUDIO-SHENZHEN-88", "OEM_Factory", {"region": "Shenzhen", "tier": "Tier-1 Acoustic"})
        self.add_node("OEM-DISPLAYS-KOREA-12", "OEM_Factory", {"region": "Gumi", "tier": "Gen-8 OLED Fab"})
        self.add_node("OEM-FURN-DONGGUAN-99", "OEM_Factory", {"region": "Dongguan", "specialty": "Ergonomic Mesh Hardware"})

        # 3. Internal SKUs
        self.add_node("INT-EL-001", "Internal_SKU", {"title": "AuraWave Pro Headphones", "msrp": 349.99})
        self.add_node("INT-EL-002", "Internal_SKU", {"title": "VortexView 65 OLED", "msrp": 1999.99})
        self.add_node("INT-HOME-201", "Internal_SKU", {"title": "ErgoSpine Mesh Chair", "msrp": 499.00})

        self.add_edge("INT-EL-001", "OEM-AUDIO-SHENZHEN-88", "MANUFACTURED_BY", {"lead_time_days": 21})
        self.add_edge("INT-EL-002", "OEM-DISPLAYS-KOREA-12", "MANUFACTURED_BY", {"lead_time_days": 35})
        self.add_edge("INT-HOME-201", "OEM-FURN-DONGGUAN-99", "MANUFACTURED_BY", {"patent": "PAT-FURN-2024-8871"})

        # 4. Cross-elasticity edge
        self.add_edge("INT-EL-001", "INT-EL-002", "CROSS_ELASTIC_WITH", {"elasticity_coefficient": -0.15})

    def clear(self) -> None:
        """Clears the knowledge graph and re-initialises the seed graph."""
        self.graph.clear()
        self._initialize_seed_graph()

    def add_node(self, node_id: str, label: str, properties: Dict[str, Any]) -> None:
        self.graph.add_node(node_id, label=label, **properties)

    def add_edge(self, source: str, target: str, relationship: str, properties: Dict[str, Any]) -> None:
        self.graph.add_edge(source, target, key=relationship, relationship=relationship, **properties)

    def query_oem_affiliations(self, oem_factory_id: str) -> List[Dict[str, Any]]:
        """Finds all internal and competitor products sharing an OEM manufacturing partner."""
        affiliations = []
        if not self.graph.has_node(oem_factory_id):
            return affiliations

        in_edges = self.graph.in_edges(oem_factory_id, data=True)
        for src, _, data in in_edges:
            node_data = self.graph.nodes[src]
            affiliations.append({
                "product_id": src,
                "label": node_data.get("label"),
                "title": node_data.get("title", src),
                "relationship": data.get("relationship"),
                "edge_properties": data,
            })
        return affiliations

    def get_brand_hierarchy(self, brand_name: str) -> Optional[Dict[str, Any]]:
        """Traverses brand ownership up to parent conglomerate."""
        for node, data in self.graph.nodes(data=True):
            if data.get("label") == "Brand" and brand_name.lower() in data.get("name", "").lower():
                parent = None
                for _, target, edge_data in self.graph.out_edges(node, data=True):
                    if edge_data.get("relationship") == "SUBSIDIARY_OF":
                        parent = self.graph.nodes[target]
                return {"brand": data, "parent": parent}
        return None

    def export_subgraph_for_ui(self) -> Dict[str, Any]:
        """Serializes the graph into nodes and links format for D3 / Vis.js / frontend UI."""
        nodes = [
            {"id": n, "label": d.get("label", "Node"), "name": d.get("name", d.get("title", n))}
            for n, d in self.graph.nodes(data=True)
        ]
        links = [
            {"source": u, "target": v, "relationship": d.get("relationship", k)}
            for u, v, k, d in self.graph.edges(keys=True, data=True)
        ]
        return {"nodes": nodes, "links": links}
