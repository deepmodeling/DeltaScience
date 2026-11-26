"""Check the 30 mm calibration independently of physical solver execution."""
import sys, types, unittest
sys.modules.setdefault('paper_geometry', types.SimpleNamespace(Separatrix=None, max_euclidean_distance=None))
import metric_core as m
BASE=0.035109356870013486
class ScoreCalibration(unittest.TestCase):
 def result(self, e):
  return m.numerical_result([{'case_id':str(i),'zeta_m':e,'valid_directions':360} for i in range(212)], BASE)
 def test_anchors_and_saturation(self):
  for value,want in [(0.,1.),(.029,1.),(.03,1.),((.03+BASE)/2,.6),(BASE,.2),((BASE+.05)/2,.1),(.05,0.),(.06,0.)]:
   self.assertAlmostEqual(self.result(value)['score'],want,places=12)
 def test_diagnostic_fields_and_invalid_input(self):
  result=self.result(.034);self.assertAlmostEqual(result['objective_q95_m'],.034);self.assertAlmostEqual(result['relative_improvement'],1-.034/BASE);self.assertEqual(result['full_score_q95_m'],.03)
  self.assertEqual(result['scoring_version'],'mastu-q95-30mm-v1');self.assertEqual(len(result['per_case']),212)
  for bad in (float('nan'),-1):
   with self.assertRaises(ValueError):self.result(bad)
  for bad_baseline in (.03,.029,.05,float('nan')):
   with self.assertRaises(ValueError):m.numerical_result([{'zeta_m':.035}]*212,bad_baseline)
 def test_monotonic(self):
  values=[self.result(.025+i*.0001)['score'] for i in range(301)]
  self.assertTrue(all(a>=b for a,b in zip(values,values[1:])))
