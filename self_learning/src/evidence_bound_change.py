from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
import hashlib, json
from .ocode_execution_adapter import FileChange
from .repository_orchestrator import GovernedRepositoryChangeOrchestrator, ChangeTransactionResult

@dataclass(frozen=True)
class ChangeIntent:
    intent_id: str
    actor: str
    knowledge_refs: tuple[str, ...]
    wisdom_case_ref: str
    authority_ref: str
    change_digest: str
    rationale: str

@dataclass(frozen=True)
class ChangeApproval:
    intent_id: str
    approver: str
    approved_change_digest: str
    approval_id: str

def canonical_change_digest(changes: Iterable[FileChange]) -> str:
    payload = [{"path": c.path,"expected_sha256": c.expected_sha256,"new_content_sha256": hashlib.sha256(c.new_content.encode("utf-8")).hexdigest()} for c in sorted(changes, key=lambda x: x.path)]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

class EvidenceBoundChangeGate:
    @staticmethod
    def create_intent(actor, knowledge_refs, wisdom_case_ref, authority_ref, changes, rationale):
        digest=canonical_change_digest(changes)
        seed=json.dumps({"actor":actor,"knowledge_refs":knowledge_refs,"wisdom_case_ref":wisdom_case_ref,"authority_ref":authority_ref,"change_digest":digest,"rationale":rationale},sort_keys=True,separators=(",",":"))
        return ChangeIntent(hashlib.sha256(seed.encode()).hexdigest(),actor,knowledge_refs,wisdom_case_ref,authority_ref,digest,rationale)
    @staticmethod
    def approve(intent, approver):
        seed=f"{intent.intent_id}|{approver}|{intent.change_digest}"
        return ChangeApproval(intent.intent_id,approver,intent.change_digest,hashlib.sha256(seed.encode()).hexdigest())
    @staticmethod
    def verify(intent, approval, changes):
        if not intent.knowledge_refs: return False,"MISSING_KNOWLEDGE_EVIDENCE"
        if not intent.wisdom_case_ref: return False,"MISSING_WISDOM_CASE"
        if not intent.authority_ref: return False,"MISSING_AUTHORITY"
        if approval.intent_id != intent.intent_id: return False,"APPROVAL_INTENT_MISMATCH"
        digest=canonical_change_digest(changes)
        if digest != intent.change_digest: return False,"CHANGE_DIGEST_MISMATCH"
        if approval.approved_change_digest != digest: return False,"APPROVAL_DIGEST_MISMATCH"
        return True,"APPROVED"

class EvidenceBoundRepositoryOrchestrator:
    def __init__(self, orchestrator): self.orchestrator=orchestrator
    def transact(self,intent,approval,changes,commands,message):
        changes=tuple(changes)
        ok,reason=EvidenceBoundChangeGate.verify(intent,approval,changes)
        if not ok: return ChangeTransactionResult(False,reason,events=["EVIDENCE_GATE_BLOCKED"])
        result=self.orchestrator.transact(changes,commands,message)
        if result.committed: result.events.insert(0,"EVIDENCE_GATE_APPROVED")
        return result
