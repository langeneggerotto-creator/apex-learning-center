from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib, subprocess

@dataclass(frozen=True)
class GitCommitAuthority:
    allowed_branch_prefix: str = "apex-learning/"
    allow_commit: bool = False

@dataclass(frozen=True)
class GitEvidence:
    branch: str
    status: str
    diff: str
    tested_tree_hash: str
    commit_sha: str | None = None

class GovernedGitLifecycle:
    def __init__(self, root: str, authority: GitCommitAuthority):
        self.root=Path(root).resolve(); self.authority=authority
    def _git(self,*args,check=True):
        return subprocess.run(['git',*args],cwd=self.root,text=True,capture_output=True,check=check)
    def branch(self): return self._git('branch','--show-current').stdout.strip()
    def _assert_branch(self):
        b=self.branch()
        if not b.startswith(self.authority.allowed_branch_prefix): raise PermissionError('BRANCH_NOT_AUTHORIZED')
        return b
    def status(self): return self._git('status','--porcelain').stdout
    def diff(self): return self._git('diff','--no-ext-diff','--binary').stdout
    def tree_hash(self):
        h=hashlib.sha256()
        for p in sorted(x for x in self.root.rglob('*') if x.is_file() and '.git' not in x.parts):
            h.update(str(p.relative_to(self.root)).encode()); h.update(b'\0'); h.update(p.read_bytes()); h.update(b'\0')
        return h.hexdigest()
    def capture_tested(self): return GitEvidence(self._assert_branch(),self.status(),self.diff(),self.tree_hash())
    def commit_exact_tested_bytes(self,evidence: GitEvidence,message: str):
        self._assert_branch()
        if not self.authority.allow_commit: raise PermissionError('COMMIT_NOT_AUTHORIZED')
        if self.tree_hash()!=evidence.tested_tree_hash: raise RuntimeError('TESTED_BYTES_CHANGED')
        self._git('add','-A'); self._git('commit','-m',message)
        sha=self._git('rev-parse','HEAD').stdout.strip()
        return GitEvidence(self.branch(),self.status(),self.diff(),evidence.tested_tree_hash,sha)
    def rollback_uncommitted(self):
        self._git('reset','--hard','HEAD'); self._git('clean','-fd')
