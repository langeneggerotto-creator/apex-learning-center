from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Iterable
from functools import lru_cache
import hashlib, importlib.metadata, json, os, platform, sys, subprocess

def _hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class RuntimeIdentity:
    python_version: str
    implementation: str
    platform: str
    machine: str

@dataclass(frozen=True)
class DependencySnapshot:
    packages: tuple[str, ...]
    snapshot_hash: str

@dataclass(frozen=True)
class CommandAttestation:
    argv: tuple[str, ...]
    returncode: int
    stdout_hash: str
    stderr_hash: str

@dataclass(frozen=True)
class ArtifactAttestation:
    path: str
    sha256: str
    size_bytes: int

@dataclass(frozen=True)
class RuntimeAttestation:
    runtime: RuntimeIdentity
    dependencies: DependencySnapshot
    commands: tuple[CommandAttestation, ...]
    artifacts: tuple[ArtifactAttestation, ...]
    attestation_hash: str

class RuntimeAttestor:
    @staticmethod
    @lru_cache(maxsize=1)
    def capture_runtime_identity():
        return RuntimeIdentity(sys.version.split()[0],platform.python_implementation(),platform.platform(),platform.machine())
    @staticmethod
    @lru_cache(maxsize=1)
    def capture_dependencies():
        packages=[]
        for dist in importlib.metadata.distributions():
            name=dist.metadata.get("Name"); version=dist.version
            if name and version: packages.append(f"{name}=={version}")
        frozen=tuple(sorted(set(packages),key=str.lower))
        return DependencySnapshot(frozen,_hash(frozen))
    @staticmethod
    def run_command(argv,cwd):
        cp=subprocess.run(argv,cwd=cwd,text=True,capture_output=True,timeout=60)
        return CommandAttestation(tuple(argv),cp.returncode,hashlib.sha256(cp.stdout.encode()).hexdigest(),hashlib.sha256(cp.stderr.encode()).hexdigest())
    @staticmethod
    def attest_artifact(path,root):
        full=os.path.realpath(os.path.join(root,path)); rr=os.path.realpath(root)
        if not (full==rr or full.startswith(rr+os.sep)): raise PermissionError("ARTIFACT_PATH_ESCAPE")
        data=open(full,"rb").read(); return ArtifactAttestation(path,hashlib.sha256(data).hexdigest(),len(data))
    @classmethod
    def build_attestation(cls,cwd,commands,artifact_paths):
        runtime=cls.capture_runtime_identity(); deps=cls.capture_dependencies(); cr=tuple(cls.run_command(tuple(c),cwd) for c in commands)
        if any(c.returncode != 0 for c in cr): raise RuntimeError("ATTESTED_COMMAND_FAILED")
        arts=tuple(cls.attest_artifact(p,cwd) for p in sorted(artifact_paths))
        body={"runtime":asdict(runtime),"dependencies":asdict(deps),"commands":[asdict(x) for x in cr],"artifacts":[asdict(x) for x in arts]}
        return RuntimeAttestation(runtime,deps,cr,arts,_hash(body))
    @staticmethod
    def verify(att,cwd):
        if _hash(att.dependencies.packages)!=att.dependencies.snapshot_hash:return False,"DEPENDENCY_SNAPSHOT_TAMPERED"
        body={"runtime":asdict(att.runtime),"dependencies":asdict(att.dependencies),"commands":[asdict(x) for x in att.commands],"artifacts":[asdict(x) for x in att.artifacts]}
        if _hash(body)!=att.attestation_hash:return False,"ATTESTATION_TAMPERED"
        for a in att.artifacts:
            try: current=RuntimeAttestor.attest_artifact(a.path,cwd)
            except FileNotFoundError:return False,"ATTESTED_ARTIFACT_MISSING"
            if current.sha256!=a.sha256 or current.size_bytes!=a.size_bytes:return False,"ATTESTED_ARTIFACT_CHANGED"
        return True,"VALID_RUNTIME_ATTESTATION"
