import hashlib, tempfile, unittest, subprocess
from pathlib import Path
from self_learning.src.ocode_execution_adapter import *
from self_learning.src.git_lifecycle import *
from self_learning.src.repository_orchestrator import *
from self_learning.src.evidence_bound_change import *
from self_learning.src.lineage_graph import *
from self_learning.src.lineage_runtime import *

def lineage_payloads():
    return {
        "commit":{"sha":"PENDING","binding":"PRECOMMIT_INTENT"},
        "tested_tree":{"hash":"tree1"},
        "patch":{"digest":"patch1"},
        "approval":{"approval_id":"ap1"},
        "authority":{"authority_id":"auth1"},
        "wisdom":{"wisdom_case_id":"w1"},
        "understanding":{"understanding_id":"u1"},
        "knowledge":{"knowledge_id":"k1"},
        "evidence":{"evidence_id":"e1"},
        "source":{"source_id":"s1","content_hash":"src1"},
    }

class LineageRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.repo_temp=tempfile.TemporaryDirectory(); self.lineage_temp=tempfile.TemporaryDirectory(); self.r=Path(self.repo_temp.name)
        subprocess.run(['git','init','-q'],cwd=self.r); subprocess.run(['git','config','user.email','test@example.com'],cwd=self.r); subprocess.run(['git','config','user.name','APEX'],cwd=self.r)
        (self.r/'workspace').mkdir(); (self.r/'workspace'/'a.txt').write_text('A')
        subprocess.run(['git','add','.'],cwd=self.r); subprocess.run(['git','commit','-qm','seed'],cwd=self.r); subprocess.run(['git','checkout','-qb','apex-learning/test'],cwd=self.r)
        ea=ExecutionAuthority(str(self.r),('workspace',),(('python','-c','print("ok")'),)); ex=OCodeExecutionAdapter(ea); git=GovernedGitLifecycle(str(self.r),GitCommitAuthority(allow_commit=True))
        repo=EvidenceBoundRepositoryOrchestrator(GovernedRepositoryChangeOrchestrator(ex,git))
        self.db=Path(self.lineage_temp.name)/'lineage.db'; self.graph=DecisionLineageGraph(str(self.db)); self.pre_root=build_full_lineage(self.graph,lineage_payloads()); self.runtime=LineageAwareRuntime(self.graph,repo)
    def tearDown(self):
        self.graph.close(); self.repo_temp.cleanup(); self.lineage_temp.cleanup()
    def h(self): return hashlib.sha256((self.r/'workspace'/'a.txt').read_bytes()).hexdigest()
    def change_bundle(self, content='B'):
        changes=(FileChange('workspace/a.txt',self.h(),content),); intent=EvidenceBoundChangeGate.create_intent('APEX',('K1','E1'),'W1','AUTH1',changes,'verified improvement'); approval=EvidenceBoundChangeGate.approve(intent,'owner'); return changes,intent,approval
    def actual_commit_node_id(self, sha):
        row=self.graph.db.execute("SELECT node_id FROM lineage_nodes WHERE node_type='commit' AND payload_json LIKE ?",(f'%{sha}%',)).fetchone(); self.assertIsNotNone(row); return row[0]
    def test_valid_lineage_executes_and_rebinds_actual_sha(self):
        ch,i,a=self.change_bundle(); r=self.runtime.execute(self.pre_root,i,a,ch,(), 'verified'); self.assertTrue(r.committed); self.assertTrue(r.pre_lineage_valid); self.assertTrue(r.post_lineage_valid); self.assertEqual(len(r.commit_sha),40); self.assertIn('POST_LINEAGE_VERIFIED',r.events)
    def test_broken_pre_lineage_blocks_before_mutation(self):
        kid=self.graph.db.execute("SELECT node_id FROM lineage_nodes WHERE node_type='knowledge'").fetchone()[0]; self.graph.db.execute("DELETE FROM lineage_edges WHERE child_id=?",(kid,)); self.graph.db.commit(); ch,i,a=self.change_bundle(); r=self.runtime.execute(self.pre_root,i,a,ch,(), 'bad'); self.assertFalse(r.committed); self.assertFalse(r.pre_lineage_valid); self.assertEqual((self.r/'workspace'/'a.txt').read_text(),'A')
    def test_tampered_pre_node_blocks_before_mutation(self):
        self.graph.db.execute("UPDATE lineage_nodes SET payload_json=? WHERE node_type='evidence'",('{"evidence_id":"evil"}',)); self.graph.db.commit(); ch,i,a=self.change_bundle(); r=self.runtime.execute(self.pre_root,i,a,ch,(), 'bad'); self.assertFalse(r.committed); self.assertIn('PRE_LINEAGE_INVALID',r.reason); self.assertEqual((self.r/'workspace'/'a.txt').read_text(),'A')
    def test_failed_repository_transaction_never_gets_post_verified(self):
        ch,i,a=self.change_bundle(); bad=(FileChange('workspace/a.txt',self.h(),'C'),); r=self.runtime.execute(self.pre_root,i,a,bad,(), 'bad'); self.assertFalse(r.committed); self.assertTrue(r.pre_lineage_valid); self.assertFalse(r.post_lineage_valid)
    def test_actual_commit_sha_exists_in_persistent_graph(self):
        ch,i,a=self.change_bundle(); r=self.runtime.execute(self.pre_root,i,a,ch,(), 'verified'); actual_id=self.actual_commit_node_id(r.commit_sha); actual=self.graph.get_node(actual_id); self.assertEqual(actual.payload['sha'],r.commit_sha); self.assertEqual(actual.payload['binding'],'ACTUAL_GIT_COMMIT')
    def test_persisted_actual_commit_chain_verifies_after_restart(self):
        ch,i,a=self.change_bundle(); r=self.runtime.execute(self.pre_root,i,a,ch,(), 'verified'); actual_id=self.actual_commit_node_id(r.commit_sha); self.graph.close(); self.graph=DecisionLineageGraph(str(self.db)); ok,reason,_=self.graph.verify_full_chain(actual_id); self.assertTrue(ok); self.assertEqual(reason,'VALID_FULL_LINEAGE')
    def test_post_commit_lineage_tamper_is_detectable(self):
        ch,i,a=self.change_bundle(); r=self.runtime.execute(self.pre_root,i,a,ch,(), 'verified'); actual_id=self.actual_commit_node_id(r.commit_sha); edge=self.graph.parents(actual_id)[0]; self.graph.db.execute("UPDATE lineage_edges SET edge_hash='bad' WHERE child_id=? AND parent_id=?",(edge.child_id,edge.parent_id)); self.graph.db.commit(); ok,reason,_=self.graph.verify_full_chain(actual_id); self.assertFalse(ok); self.assertEqual(reason,'EDGE_SUBSTITUTION_DETECTED')

if __name__=='__main__': unittest.main()
