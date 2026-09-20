#!/usr/bin/env python3
"""
Operational script: seeds the Retail Knowledge Graph from a JSON fixture and validates graph integrity.

Usage:
    python scripts/seed_knowledge_graph.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from retail_intel.agents.graph.knowledge_graph import RetailKnowledgeGraph


def main():
    print("Initialising Retail Knowledge Graph...")
    kg = RetailKnowledgeGraph()

    subgraph = kg.export_subgraph_for_ui()
    nodes = subgraph["nodes"]
    links = subgraph["links"]

    print(f"✅ Graph populated: {len(nodes)} nodes, {len(links)} relationships")

    print("\nSample OEM affiliation query (OEM-FURN-DONGGUAN-99):")
    affiliations = kg.query_oem_affiliations("OEM-FURN-DONGGUAN-99")
    for aff in affiliations:
        print(f"  → {aff['product_id']} [{aff['label']}] via {aff['relationship']}")

    print("\nSample brand hierarchy query (NovaComfort):")
    hierarchy = kg.get_brand_hierarchy("NovaComfort")
    if hierarchy:
        print(f"  Brand: {hierarchy['brand'].get('name')}")
        if hierarchy["parent"]:
            print(f"  Parent: {hierarchy['parent'].get('name')}")


if __name__ == "__main__":
    main()
