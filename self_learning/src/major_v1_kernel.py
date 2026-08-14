from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable
import hashlib, json, uuid

def digest(x: Any)->str:return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
@dataclass(frozen=True)
class PolicyDecision: allowed:bool; reason:str; obligations:tuple[str,...]=()
@dataclass
class PolicyEngine:
 deny_actions:set[str]=field(default_factory=set); protected_prefixes:tuple[str,...]=("authority.","governance.","control_plane.")
 def decide(self,action,target,risk,authority):
  if action in self.deny_actions:return PolicyDecision(False,"ACTION_DENIED")
  if target.startswith(self.protected_prefixes):return PolicyDecision(False,"PROTECTED_CONTROL_PLANE")
  if not authority:return PolicyDecision(False,"NO_AUTHORITY")
  if risk>0.8:return PolicyDecision(False,"RISK_TOO_HIGH",("HUMAN_ESCALATION",))
  return PolicyDecision(True,"AUTHORIZED",("AUDIT","ROLLBACK"))
@dataclass
class CapabilityRegistry:
 capabilities:dict[str,dict]=field(default_factory=dict)
 def register(self,name,scope,reversible=True):self.capabilities[name]={"scope":scope,"reversible":reversible}
 def require(self,name):
  if name not in self.capabilities:raise PermissionError("CAPABILITY_NOT_REGISTERED")
  return self.capabilities[name]
@dataclass
class TrustLedger:
 successes:int=0;failures:int=0
 def record(self,ok):self.successes+=int(ok);self.failures+=int(not ok)
 @property
 def score(self):return (self.successes+1)/(self.successes+self.failures+2)
@dataclass(frozen=True)
class RiskCase:
 impact:float;likelihood:float;reversibility:float;uncertainty:float
 @property
 def score(self):return min(1.0,max(0.0,self.impact*self.likelihood*(1+self.uncertainty)*(1-self.reversibility/2)))
@dataclass
class Budget:
 max_actions:int;used:int=0
 def consume(self,n=1):
  if self.used+n>self.max_actions:raise RuntimeError("BUDGET_EXCEEDED")
  self.used+=n
@dataclass
class EventStore:
 events:list[dict]=field(default_factory=list)
 def append(self,kind,payload):
  prev=self.events[-1]["hash"] if self.events else "GENESIS";e={"seq":len(self.events),"kind":kind,"payload":payload,"prev":prev};e["hash"]=digest(e);self.events.append(e);return e
 def verify(self):
  prev="GENESIS"
  for i,e in enumerate(self.events):
   raw={k:v for k,v in e.items() if k!="hash"}
   if e["seq"]!=i or e["prev"]!=prev or digest(raw)!=e["hash"]:return False
   prev=e["hash"]
  return True
@dataclass(frozen=True)
class Experiment:
 hypothesis:str;baseline:float;candidate:float;safety_ok:bool;held_out:bool
 def decision(self):
  if not self.safety_ok:return "REJECT_SAFETY"
  if not self.held_out:return "MORE_EVIDENCE"
  return "PROMOTE" if self.candidate>self.baseline else "KEEP_BASELINE"
@dataclass
class DriftMonitor:
 baseline:float;threshold:float
 def check(self,current):return abs(current-self.baseline)>self.threshold
@dataclass
class ApprovalQuorum:
 required:int;approvals:set[str]=field(default_factory=set)
 def approve(self,p):self.approvals.add(p)
 def satisfied(self):return len(self.approvals)>=self.required
@dataclass
class LeaseManager:
 holder:str|None=None;token:str|None=None
 def acquire(self,h):
  if self.holder and self.holder!=h:raise RuntimeError("LEASE_HELD")
  self.holder=h;self.token=self.token or uuid.uuid4().hex;return self.token
 def release(self,t):
  if t!=self.token:raise PermissionError("LEASE_TOKEN_MISMATCH")
  self.holder=self.token=None
@dataclass
class IdempotencyRegistry:
 results:dict[str,Any]=field(default_factory=dict)
 def execute(self,key,fn):
  if key not in self.results:self.results[key]=fn()
  return self.results[key]
@dataclass
class ProviderRouter:
 providers:dict[str,float]=field(default_factory=dict)
 def choose(self):
  if not self.providers:raise RuntimeError("NO_PROVIDER")
  return max(self.providers,key=self.providers.get)
@dataclass
class IncidentManager:
 incidents:list[dict]=field(default_factory=list)
 def open(self,severity,reason):
  x={"id":uuid.uuid4().hex,"severity":severity,"reason":reason,"state":"OPEN"};self.incidents.append(x);return x
 def close(self,i):
  for x in self.incidents:
   if x["id"]==i:x["state"]="CLOSED";return x
  raise KeyError("INCIDENT_NOT_FOUND")
@dataclass
class MajorV1Runtime:
 policy:PolicyEngine=field(default_factory=PolicyEngine);capabilities:CapabilityRegistry=field(default_factory=CapabilityRegistry);trust:TrustLedger=field(default_factory=TrustLedger);events:EventStore=field(default_factory=EventStore);budget:Budget=field(default_factory=lambda:Budget(100))
 def govern(self,action,target,capability,risk,authority):
  self.budget.consume();self.capabilities.require(capability);d=self.policy.decide(action,target,risk.score,authority);self.events.append("DECISION",{"action":action,"target":target,"allowed":d.allowed,"reason":d.reason,"risk":risk.score});self.trust.record(d.allowed);return d
