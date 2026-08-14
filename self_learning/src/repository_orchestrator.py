from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable
from .ocode_execution_adapter import OCodeExecutionAdapter, FileChange, ExecutionResult
from .git_lifecycle import GovernedGitLifecycle, GitEvidence

@dataclass
class ChangeTransactionResult:
    committed: bool
    reason: str
    execution: ExecutionResult | None = None
    pre_git: GitEvidence | None = None
    post_git: GitEvidence | None = None
    events: list[str] = field(default_factory=list)

class GovernedRepositoryChangeOrchestrator:
    """Atomic coordinator: mutate -> verify -> prove exact bytes -> commit or rollback."""
    def __init__(self, executor: OCodeExecutionAdapter, git: GovernedGitLifecycle):
        self.executor=executor; self.git=git
    def transact(self, changes: Iterable[FileChange], commands: Iterable[tuple[str,...]], message: str)->ChangeTransactionResult:
        events=[]
        try:
            if self.git.status():
                return ChangeTransactionResult(False,'DIRTY_REPOSITORY',events=['PRECHECK_BLOCKED'])
            baseline=self.git.capture_tested(); events.append('BASELINE_CAPTURED')
            execution=self.executor.apply_and_verify(changes,commands)
            events.append('EXECUTION_VERIFIED' if execution.executed else 'EXECUTION_BLOCKED')
            if not execution.executed:
                return ChangeTransactionResult(False,execution.reason,execution=execution,pre_git=baseline,events=events)
            tested=self.git.capture_tested(); events.append('TESTED_TREE_CAPTURED')
            try:
                committed=self.git.commit_exact_tested_bytes(tested,message); events.append('COMMITTED')
                return ChangeTransactionResult(True,'COMMITTED',execution,baseline,committed,events)
            except Exception as e:
                self.git.rollback_uncommitted(); events.append('GIT_ROLLBACK')
                return ChangeTransactionResult(False,str(e),execution,baseline,None,events)
        except Exception as e:
            try: self.git.rollback_uncommitted(); events.append('EMERGENCY_ROLLBACK')
            except Exception: events.append('ROLLBACK_FAILED')
            return ChangeTransactionResult(False,str(e),events=events)
