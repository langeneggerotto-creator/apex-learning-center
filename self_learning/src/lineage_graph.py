from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable
import hashlib, json, sqlite3

LINEAGE_ORDER = (
    "commit",
    "tested_tree",
    "patch",
    "approval",
    "authority",
    "wisdom",
    "understanding",
    "knowledge",
    "evidence",
    "source",
)

@dataclass(frozen=True)
class LineageNode:
    node_id: str
    node_type: str
    payload: dict
    payload_hash: str

@dataclass(frozen=True)
class LineageEdge:
    child_id: str
    parent_id: str
    relation: str
    edge_hash: str

def canonical_hash(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

class DecisionLineageGraph:
    """Persistent decision-to-source lineage graph with fail-closed integrity checks."""

    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        self.db = sqlite3.connect(self.db_path)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS lineage_nodes(
                node_id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                payload_hash TEXT NOT NULL
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS lineage_edges(
                child_id TEXT NOT NULL,
                parent_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                edge_hash TEXT NOT NULL,
                PRIMARY KEY(child_id,parent_id,relation)
            )
        """)
        self.db.commit()

    def close(self):
        self.db.close()

    def add_node(self, node_type: str, payload: dict, node_id: str | None = None) -> LineageNode:
        if node_type not in LINEAGE_ORDER:
            raise ValueError("UNKNOWN_LINEAGE_NODE_TYPE")
        payload_hash = canonical_hash(payload)
        node_id = node_id or hashlib.sha256(f"{node_type}|{payload_hash}".encode()).hexdigest()
        existing = self.db.execute(
            "SELECT node_type,payload_json,payload_hash FROM lineage_nodes WHERE node_id=?",
            (node_id,),
        ).fetchone()
        if existing:
            if existing[0] != node_type or existing[2] != payload_hash:
                raise RuntimeError("NODE_ID_SUBSTITUTION_DETECTED")
            return LineageNode(node_id, node_type, json.loads(existing[1]), existing[2])
        self.db.execute(
            "INSERT INTO lineage_nodes VALUES(?,?,?,?)",
            (node_id, node_type, json.dumps(payload, sort_keys=True), payload_hash),
        )
        self.db.commit()
        return LineageNode(node_id, node_type, payload, payload_hash)

    def add_edge(self, child: LineageNode, parent: LineageNode, relation: str = "DERIVED_FROM") -> LineageEdge:
        edge_hash = canonical_hash({
            "child_id": child.node_id,
            "parent_id": parent.node_id,
            "relation": relation,
            "child_hash": child.payload_hash,
            "parent_hash": parent.payload_hash,
        })
        self.db.execute(
            "INSERT OR REPLACE INTO lineage_edges VALUES(?,?,?,?)",
            (child.node_id, parent.node_id, relation, edge_hash),
        )
        self.db.commit()
        return LineageEdge(child.node_id, parent.node_id, relation, edge_hash)

    def get_node(self, node_id: str) -> LineageNode:
        row = self.db.execute(
            "SELECT node_type,payload_json,payload_hash FROM lineage_nodes WHERE node_id=?",
            (node_id,),
        ).fetchone()
        if not row:
            raise KeyError("LINEAGE_NODE_NOT_FOUND")
        return LineageNode(node_id, row[0], json.loads(row[1]), row[2])

    def parents(self, child_id: str) -> list[LineageEdge]:
        rows = self.db.execute(
            "SELECT child_id,parent_id,relation,edge_hash FROM lineage_edges WHERE child_id=?",
            (child_id,),
        ).fetchall()
        return [LineageEdge(*r) for r in rows]

    def verify_node(self, node_id: str) -> tuple[bool,str]:
        try:
            n=self.get_node(node_id)
        except KeyError:
            return False,"MISSING_NODE"
        if canonical_hash(n.payload) != n.payload_hash:
            return False,"NODE_PAYLOAD_TAMPERED"
        return True,"VALID"

    def verify_edge(self, edge: LineageEdge) -> tuple[bool,str]:
        try:
            child=self.get_node(edge.child_id)
            parent=self.get_node(edge.parent_id)
        except KeyError:
            return False,"BROKEN_EDGE"
        expected=canonical_hash({
            "child_id": child.node_id,
            "parent_id": parent.node_id,
            "relation": edge.relation,
            "child_hash": child.payload_hash,
            "parent_hash": parent.payload_hash,
        })
        if expected != edge.edge_hash:
            return False,"EDGE_SUBSTITUTION_DETECTED"
        return True,"VALID"

    def verify_full_chain(self, commit_node_id: str) -> tuple[bool,str,list[str]]:
        visited=[]
        current=self.get_node(commit_node_id)
        if current.node_type != "commit":
            return False,"ROOT_NOT_COMMIT",visited
        for expected_type in LINEAGE_ORDER:
            if current.node_type != expected_type:
                return False,f"EXPECTED_{expected_type.upper()}_GOT_{current.node_type.upper()}",visited
            ok,reason=self.verify_node(current.node_id)
            if not ok:
                return False,reason,visited
            visited.append(current.node_id)
            if expected_type == "source":
                return True,"VALID_FULL_LINEAGE",visited
            edges=self.parents(current.node_id)
            if len(edges) != 1:
                return False,"AMBIGUOUS_OR_MISSING_PARENT",visited
            ok,reason=self.verify_edge(edges[0])
            if not ok:
                return False,reason,visited
            current=self.get_node(edges[0].parent_id)
        return False,"INCOMPLETE_LINEAGE",visited

    def export_chain(self, commit_node_id: str) -> dict:
        ok,reason,ids=self.verify_full_chain(commit_node_id)
        return {
            "valid": ok,
            "reason": reason,
            "nodes": [asdict(self.get_node(i)) for i in ids],
        }

def build_full_lineage(graph: DecisionLineageGraph, payloads: dict) -> str:
    nodes={}
    for node_type in reversed(LINEAGE_ORDER):
        if node_type not in payloads:
            raise ValueError(f"MISSING_{node_type.upper()}_PAYLOAD")
        nodes[node_type]=graph.add_node(node_type,payloads[node_type])
    for idx in range(len(LINEAGE_ORDER)-1):
        child=nodes[LINEAGE_ORDER[idx]]
        parent=nodes[LINEAGE_ORDER[idx+1]]
        graph.add_edge(child,parent)
    return nodes["commit"].node_id
