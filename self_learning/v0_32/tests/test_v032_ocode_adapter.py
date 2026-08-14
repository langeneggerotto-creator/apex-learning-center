import hashlib,tempfile,unittest
from pathlib import Path
from src.ocode_execution_adapter import *
class OCodeAdapterTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name);(self.root/'workspace').mkdir();(self.root/'workspace'/'a.txt').write_text('A');self.auth=ExecutionAuthority(str(self.root),('workspace',),(('python','-c','print("ok")'),));self.a=OCodeExecutionAdapter(self.auth)
 def tearDown(self):self.t.cleanup()
 def h(self,p):return hashlib.sha256(p.read_bytes()).hexdigest()
 def test_real_authorized_mutation_and_verification(self):
  p=self.root/'workspace'/'a.txt';r=self.a.apply_and_verify([FileChange('workspace/a.txt',self.h(p),'B')],[('python','-c','print("ok")')]);self.assertTrue(r.executed);self.assertEqual(p.read_text(),'B')
 def test_stale_change_fails_closed(self):
  p=self.root/'workspace'/'a.txt';r=self.a.apply_and_verify([FileChange('workspace/a.txt','0'*64,'B')],[]);self.assertFalse(r.executed);self.assertEqual(p.read_text(),'A')
 def test_path_escape_blocked(self):self.assertFalse(self.a.apply_and_verify([FileChange('../x','0'*64,'B')],[]).executed)
 def test_protected_control_plane_blocked(self):self.assertFalse(self.a.apply_and_verify([FileChange('authority/x','0'*64,'B')],[]).executed)
 def test_unapproved_command_rolls_back(self):
  p=self.root/'workspace'/'a.txt';r=self.a.apply_and_verify([FileChange('workspace/a.txt',self.h(p),'B')],[('sh','-c','true')]);self.assertFalse(r.executed);self.assertTrue(r.rolled_back);self.assertEqual(p.read_text(),'A')
 def test_failed_verification_rolls_back(self):
  a=OCodeExecutionAdapter(ExecutionAuthority(str(self.root),('workspace',),(('python','-c','raise SystemExit(1)'),)));p=self.root/'workspace'/'a.txt';r=a.apply_and_verify([FileChange('workspace/a.txt',self.h(p),'B')],[('python','-c','raise SystemExit(1)')]);self.assertFalse(r.executed);self.assertEqual(p.read_text(),'A')
