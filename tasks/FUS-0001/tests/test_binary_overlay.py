"""Exercise binary entrypoint while stubbing only physical field grading."""
import contextlib,io,json,math,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
sys.modules.setdefault('paper_geometry',types.SimpleNamespace(Separatrix=None,max_euclidean_distance=None))
sys.modules.setdefault('freegs4e',types.SimpleNamespace(critical=types.SimpleNamespace()))
import grade
class BinaryTests(unittest.TestCase):
 def invoke(self, report):
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp);(out/'reward.txt').write_text('stale')
   with patch.object(sys,'argv',['grade.py','--submission',tmp,'--output',tmp]),patch.object(grade,'grade',return_value=report),contextlib.redirect_stdout(io.StringIO()):
    status=grade.main()
   result=json.loads((out/'result.json').read_text());reward=(out/'reward.txt').read_text() if (out/'reward.txt').exists() else None
   return status,result,reward
 def test_boundary_and_diagnostics(self):
  for value,want in [(math.nextafter(.4,0),0),(.4,1),(math.nextafter(.4,1),1),(.32978,0),(.5,1)]:
   status,r,reward=self.invoke({'status':'scored','score':value,'objective_q95_m':.034,'per_case':[{'zeta_m':.02}]})
   self.assertEqual(status,0);self.assertEqual(float(reward),want);self.assertEqual(r['score'],value);self.assertEqual(r['continuous_score'],value);self.assertEqual(r['per_case'],[{'zeta_m':.02}])
 def test_failure_and_invalid_scores(self):
  for report in [{'status':'platform_failure'}, {'status':'scored','score':float('nan')}, {'status':'scored','score':True}, {'status':'scored','score':1.01}]:
   status,r,reward=self.invoke(report);self.assertEqual(status,2);self.assertEqual(r['status'],'platform_failure');self.assertIsNone(reward)
 def test_invalid_submission_is_scientific_zero(self):
  status,r,reward=self.invoke({'status':'invalid_submission','score':0.0});self.assertEqual(status,0);self.assertEqual(float(reward),0);self.assertEqual(r['continuous_score'],0)
