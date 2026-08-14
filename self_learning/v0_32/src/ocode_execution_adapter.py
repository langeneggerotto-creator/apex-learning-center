from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
import hashlib, subprocess
PROTECTED_PREFIXES=(".git/","authority/","governance/","control_plane/")
@dataclass(frozen=True)
class ExecutionAuthority:
    repository_root:str; allowed_paths:tuple[str,...]; allowed_commands:tuple[tuple[str,...],...]; allow_commit:bool=False
@dataclass(frozen=True)
class FileChange:
    path:str; expected_sha256:str; new_content:str
@dataclass
class ExecutionResult:
    executed:bool; reason:str; changed_paths:list[str]=field(default_factory=list); command_results:list[dict]=field(default_factory=list); rolled_back:bool=False
class OCodeExecutionAdapter:
    def __init__(self,authority): self.authority=authority; self.root=Path(authority.repository_root).resolve()
    @staticmethod
    def sha256_bytes(data): return hashlib.sha256(data).hexdigest()
    def _resolve(self,rel):
        if rel.startswith('/') or '..' in Path(rel).parts: raise PermissionError('PATH_ESCAPE')
        if any(rel==p.rstrip('/') or rel.startswith(p) for p in PROTECTED_PREFIXES): raise PermissionError('PROTECTED_CONTROL_PLANE')
        p=(self.root/rel).resolve()
        if self.root not in p.parents and p!=self.root: raise PermissionError('PATH_ESCAPE')
        if not any(rel==a.rstrip('/') or rel.startswith(a.rstrip('/')+'/') for a in self.authority.allowed_paths): raise PermissionError('OUTSIDE_AUTHORITY')
        return p
    def apply_and_verify(self,changes,commands):
        snapshots={}; changed=[]
        try:
            for c in changes:
                p=self._resolve(c.path); old=p.read_bytes() if p.exists() else b''
                if self.sha256_bytes(old)!=c.expected_sha256: raise RuntimeError('STALE_CHANGE')
                snapshots[p]=old if p.exists() else None; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(c.new_content,encoding='utf-8'); changed.append(c.path)
            results=[]
            for cmd in commands:
                if tuple(cmd) not in self.authority.allowed_commands: raise PermissionError('COMMAND_NOT_ALLOWED')
                cp=subprocess.run(cmd,cwd=self.root,text=True,capture_output=True,timeout=60); results.append({'command':list(cmd),'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr})
                if cp.returncode!=0: raise RuntimeError('VERIFICATION_FAILED')
            return ExecutionResult(True,'VERIFIED',changed,results,False)
        except Exception as e:
            for p,old in snapshots.items():
                if old is None:
                    if p.exists(): p.unlink()
                else: p.write_bytes(old)
            return ExecutionResult(False,str(e),changed,[],bool(snapshots))
