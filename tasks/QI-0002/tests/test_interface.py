"""Black-box data contract, metric mapping and failure separation."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import grade
from model import load_config


class InterfaceTests(unittest.TestCase):
    """Exercise result I/O without replacing scientific calibration with score equality."""
    def test_mapping_and_anchors(self):
        for metric, expected in [(0, 0), (1, .1), (2, .2), (3, .6), (4, 1), (5, 1)]:
            self.assertAlmostEqual(grade.score_value(metric, 2, 4), expected)
        for b, t in [(0, 4), (2, 2)]:
            with self.assertRaises(ArithmeticError): grade.score_value(2, b, t)

    def test_measure_bare_result(self):
        result = grade.measure({'encoder': [], 'decoder': []}, load_config())
        self.assertEqual(result['certificate']['tolerance'], 0)
        self.assertEqual(result['resources'], {'cx': 0, 'rotations': 0})

    def test_json_and_submission_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = {'schema_version': 2, 'encoder': [], 'decoder': [], 'report': {'unsupported_claim': True}}
            (root/'submission.json').write_text(json.dumps(data))
            self.assertEqual(grade.submission(root, load_config()), {'encoder': [], 'decoder': []})
            for raw in ['null', '[]', '{"schema_version":1}', '{"schema_version":true}', '{"x":NaN}', '{']:
                (root/'submission.json').write_text(raw)
                with self.assertRaises(grade.InvalidSubmission): grade.submission(root, load_config())
            (root/'submission.json').write_bytes(b'\xff')
            with self.assertRaises(grade.InvalidSubmission): grade.submission(root, load_config())
            (root/'submission.json').unlink()
            with self.assertRaises(grade.InvalidSubmission): grade.submission(root, load_config())
            (root/'submission.json').symlink_to(root/'missing')
            with self.assertRaises(grade.InvalidSubmission): grade.submission(root, load_config())
            (root/'link').symlink_to(root, target_is_directory=True)
            with self.assertRaises(grade.InvalidSubmission): grade.submission(root/'link', load_config())
            big = root/'big.json'; big.write_text(' '*100)
            with self.assertRaises(ValueError): grade.read_json(big, limit=10)

    def test_scoring_ignores_report_fields_and_reuses_identical_control(self):
        ref = {'schema_version': 2, 'encoder': [], 'decoder': []}
        measurement = {'certificate': {'tolerance': 1e-5}, 'zero_error_fidelities': [1]}
        with tempfile.TemporaryDirectory() as temp, patch.object(grade, 'measure', return_value=measurement) as measured:
            root = Path(temp); (root/'submission.json').write_text(json.dumps(ref))
            original = grade.read_json
            def trusted(path, limit=2_000_000):
                if path.name == 'reference.json': return ref
                if path.name == 'scoring.json': return {'full_score_tolerance': 1e-4}
                return original(path, limit)
            with patch.object(grade, 'read_json', side_effect=trusted):
                result = grade.run(root)
            self.assertEqual(result['reward'], .2)
            self.assertEqual(measured.call_count, 1)
        self.assertFalse(grade._same_circuits({'encoder': [0], 'decoder': []}, ref))

    def test_distinct_candidate_gets_its_own_metric(self):
        cfg = load_config()
        reference = {'encoder': [], 'decoder': []}
        candidate = {'schema_version': 2, 'encoder': [{'gate': 'RX', 'qubits': [0], 'theta': .1}], 'decoder': []}
        measurements = [{'certificate': {'tolerance': 1e-5}}, {'certificate': {'tolerance': 2e-5}}]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'submission.json').write_text(json.dumps(candidate))
            original = grade.read_json
            def trusted(path, limit=2_000_000):
                if path.name == 'reference.json': return reference
                if path.name == 'scoring.json': return {'full_score_tolerance': 1e-4}
                return original(path, limit)
            with patch.object(grade, 'read_json', side_effect=trusted), patch.object(grade, 'measure', side_effect=measurements):
                result = grade.run(root)
            self.assertAlmostEqual(result['raw_relative_improvement'], 1.)
            self.assertGreater(result['performance_score'], .2)

    def test_main_failure_removes_stale_reward(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); result = root/'result.json'; reward = root/'reward.txt'
            reward.write_text('1')
            args = ['grade.py', '--submission', str(root), '--output', str(result)]
            with patch.object(sys, 'argv', args), patch.object(grade, 'run', side_effect=ArithmeticError('unresolved')):
                self.assertEqual(grade.main(), 2)
            self.assertFalse(reward.exists())
            self.assertIsNone(json.loads(result.read_text())['performance_score'])
            with patch.object(sys, 'argv', args), patch.object(grade, 'run', return_value={'reward': .2, 'performance_score': .2}):
                self.assertEqual(grade.main(), 0)
            self.assertEqual(reward.read_text(), '0.0\n')
            self.assertEqual(json.loads(result.read_text())['continuous_score'], .2)

    def test_invalid_input_normal_completion(self):
        with tempfile.TemporaryDirectory() as temp:
            result = grade.run(Path(temp))
            self.assertEqual(result['performance_score'], 0)
            self.assertEqual(result['status'], 'INVALID_SUBMISSION')

    def test_unreadable_platform_file_is_not_scientific_zero(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(grade, 'read_json', side_effect=PermissionError('filesystem denied access')):
            with self.assertRaises(PermissionError): grade.run(Path(temp))


if __name__ == '__main__':
    unittest.main()
