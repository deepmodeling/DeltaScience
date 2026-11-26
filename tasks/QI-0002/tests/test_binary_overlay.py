"""Binary threshold, original performance and infrastructure failure checks."""
import json,math,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import grade

class BinaryScoring(unittest.TestCase):
    def invoke(self, value, status='GRADED', fault=False):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td); out=path/'result.json';(path/'reward.txt').write_text('stale')
            result={'reward':value,'performance_score':value,'status':status,'evaluation_complete':True,'candidate':{'witness':42}}
            with patch.object(sys,'argv',['grade.py','--submission',td,'--output',str(out)]), patch.object(grade,'run',side_effect=RuntimeError('fault') if fault else None,return_value=result):
                code=grade.main()
            info=json.loads(out.read_text()); reward=(path/'reward.txt').read_text().strip() if (path/'reward.txt').exists() else None
            return code, info, reward
    def test_unrounded_threshold_and_metrics(self):
        for value,expected in [(math.nextafter(.4,0),'0.0'),(.4,'1.0'),(math.nextafter(.4,1),'1.0'),(.31873493325657537,'0.0'),(1.0,'1.0')]:
            with self.subTest(value=value):
                code,d,reward=self.invoke(value)
                self.assertEqual((code,reward),(0,expected));self.assertEqual(d['continuous_score'],value)
                self.assertEqual(d['performance_score'],value);self.assertEqual(d['candidate']['witness'],42)
    def test_invalid_submission(self):
        code,d,reward=self.invoke(0.,'INVALID_SUBMISSION');self.assertEqual((code,reward,d['status']),(0,'0.0','INVALID_SUBMISSION'))
    def test_fault_clears_stale_reward(self):
        code,d,reward=self.invoke(None,fault=True);self.assertEqual((code,reward,d['status']),(2,None,'VERIFIER_FAILURE'))
    def test_bad_continuous_is_fault(self):
        for value in [float('nan'),float('inf'),-0.1,1.1,True]:
            code,d,reward=self.invoke(value);self.assertEqual((code,reward,d['status']),(2,None,'VERIFIER_FAILURE'))
    def test_continuous_mapping_preserved(self):
        b=1.51824951171875e-5
        self.assertAlmostEqual(grade.score_value(b,b,.0001),.2)
        self.assertAlmostEqual(grade.score_value(b+.25*(.0001-b),b,.0001),.4)
        self.assertAlmostEqual(grade.score_value(.0001,b,.0001),1.)

if __name__=='__main__':unittest.main()
