from __future__ import annotations
from dataclasses import dataclass, field
from .lineage_graph import DecisionLineageGraph
from .evidence_bound_change import ChangeIntent, ChangeApproval
from .ocode_execution_adapter import FileChange
from .evidence_bound_change import EvidenceBoundRepositoryOrchestrator

@dataclass
class LineageAwareRuntimeResult:
    committed: bool
    reason: str
    pre_lineage_valid: bool
    post_lineage_valid: bool
    commit_sha: str | None = None
    events: list[str] = field(default_factory=list)

class LineageAwareRuntime:
    def __init__(self, graph: DecisionLineageGraph, repository: EvidenceBoundRepositoryOrchestrator):
        self.graph = graph
        self.repository = repository

    def _bind_actual_commit(self, precommit_commit_node_id: str, actual_commit_sha: str) -> str:
        precommit = self.graph.get_node(precommit_commit_node_id)
        if precommit.node_type != "commit":
            raise RuntimeError("PRECOMMIT_ROOT_NOT_COMMIT")
        parents = self.graph.parents(precommit.node_id)
        if len(parents) != 1:
            raise RuntimeError("PRECOMMIT_LINEAGE_INVALID")
        tested_tree = self.graph.get_node(parents[0].parent_id)
        if tested_tree.node_type != "tested_tree":
            raise RuntimeError("PRECOMMIT_TESTED_TREE_MISSING")
        payload = dict(precommit.payload)
        payload["sha"] = actual_commit_sha
        payload["binding"] = "ACTUAL_GIT_COMMIT"
        actual = self.graph.add_node("commit", payload)
        self.graph.add_edge(actual, tested_tree)
        return actual.node_id

    def execute(self, precommit_commit_node_id: str, intent: ChangeIntent, approval: ChangeApproval,
                changes: tuple[FileChange, ...], commands: tuple[tuple[str, ...], ...], message: str) -> LineageAwareRuntimeResult:
        events=[]
        pre_ok,pre_reason,_ = self.graph.verify_full_chain(precommit_commit_node_id)
        if not pre_ok:
            return LineageAwareRuntimeResult(False, f"PRE_LINEAGE_INVALID:{pre_reason}", False, False, events=["PRE_LINEAGE_BLOCKED"])
        events.append("PRE_LINEAGE_VERIFIED")
        tx = self.repository.transact(intent,approval,changes,commands,message)
        events.extend(tx.events)
        if not tx.committed or not tx.post_git or not tx.post_git.commit_sha:
            return LineageAwareRuntimeResult(False, f"TRANSACTION_FAILED:{tx.reason}", True, False, events=events)
        actual_root = self._bind_actual_commit(precommit_commit_node_id, tx.post_git.commit_sha)
        events.append("ACTUAL_COMMIT_BOUND")
        post_ok,post_reason,_ = self.graph.verify_full_chain(actual_root)
        if not post_ok:
            return LineageAwareRuntimeResult(False, f"POST_LINEAGE_INVALID:{post_reason}", True, False, commit_sha=tx.post_git.commit_sha, events=events + ["POST_LINEAGE_BLOCKED"])
        actual = self.graph.get_node(actual_root)
        if actual.payload.get("sha") != tx.post_git.commit_sha:
            return LineageAwareRuntimeResult(False, "COMMIT_SHA_BINDING_MISMATCH", True, False, commit_sha=tx.post_git.commit_sha, events=events + ["SHA_BINDING_BLOCKED"])
        events.append("POST_LINEAGE_VERIFIED")
        return LineageAwareRuntimeResult(True, "COMMITTED_WITH_VERIFIED_LINEAGE", True, True, commit_sha=tx.post_git.commit_sha, events=events)
