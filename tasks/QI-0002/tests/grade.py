"""One-file circuit scoring; reports and claims never affect verified performance."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import stat
import sys

sys.path.insert(0, str(Path(__file__).parent / 'reference'))
from model import Evaluator, load_config, validate_pair
from tolerance import certify

SCORING_VERSION = 'noise-adapted-qec-tolerance-v5'
BINARY_THRESHOLD = 0.40
BINARY_SCORING_VERSION = 'binary-v1'
TRUSTED = Path(__file__).parent / 'reference'


class InvalidSubmission(ValueError):
    """The submitted result cannot meet the published circuit-file contract."""


def read_json(path, limit=2_000_000):
    """Read bounded UTF-8 regular-file JSON, rejecting links and nonfinite literals."""
    try:
        info = path.lstat()
    except FileNotFoundError as error:
        raise ValueError('missing file: ' + path.name) from error
    if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
        raise ValueError('nonregular, linked or oversized file: ' + path.name)

    def reject(value):
        """Reject non-standard JSON numeric literals."""
        raise ValueError('non-standard JSON number: ' + value)

    with path.open('rb') as stream:
        raw = stream.read(limit+1)
    if len(raw) > limit:
        raise ValueError('file grew beyond the size limit')
    return json.loads(raw.decode('utf-8'), parse_constant=reject)


def submission(root, cfg):
    """Accept only the new single-pair result schema; ignore optional root metadata."""
    if root.is_symlink():
        raise InvalidSubmission('linked submission directory')
    try:
        data = read_json(root / 'submission.json')
        if not isinstance(data, dict) or type(data.get('schema_version')) is not int or data['schema_version'] != 2:
            raise ValueError('schema_version must be integer 2')
        pair = {key: data.get(key) for key in ('encoder', 'decoder')}
        validate_pair(pair, cfg)
        return pair
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        raise InvalidSubmission(str(error)) from error


def score_value(value, baseline, target):
    """Separate tolerance measurement from the baseline-anchored numeric mapping."""
    if baseline <= 0 or target <= baseline:
        raise ArithmeticError('invalid trusted score anchors')
    if value <= baseline:
        return .2 * max(0., value) / baseline
    return .2 + .8 * min(1., (value-baseline)/(target-baseline))


def measure(pair, cfg):
    """Evaluate the scientific metric and retain the raw model evidence."""
    evaluator = Evaluator(pair, cfg)
    certificate = certify(evaluator.margin, evaluator.lipschitz, cfg)
    return {'certificate': certificate, 'resources': evaluator.resources,
            'zero_error_fidelities': evaluator.vector(0.).tolist(),
            'bare_fidelities': evaluator.bare.tolist(), 'lipschitz_bound': evaluator.lipschitz}


def _same_circuits(a, b):
    """Reuse an identical public submission to guarantee stable baseline equality."""
    return all(a[key] == b[key] for key in ('encoder', 'decoder'))


def run(root):
    """Use trusted private assets and only the supplied result circuit."""
    cfg = load_config(TRUSTED / 'config.json')
    try:
        pair = submission(root, cfg)
    except InvalidSubmission as error:
        return {'reward': 0., 'performance_score': 0., 'status': 'INVALID_SUBMISSION',
                'evaluation_complete': True, 'error': str(error), 'scoring_version': SCORING_VERSION}
    reference = read_json(TRUSTED / 'reference.json')
    baseline = measure(reference, cfg)
    actual = baseline if _same_circuits(pair, reference) else measure(pair, cfg)
    policy = read_json(Path(__file__).with_name('scoring.json'))
    b, value = [x['certificate']['tolerance'] for x in (baseline, actual)]
    reward = score_value(value, b, policy['full_score_tolerance'])
    return {'reward': reward, 'performance_score': reward, 'status': 'GRADED',
            'evaluation_complete': True, 'candidate': actual, 'baseline': baseline,
            'raw_relative_improvement': (value-b)/b,
            'scientific_version': cfg['scientific_version'], 'scoring_version': SCORING_VERSION,
            'reference_sha256': hashlib.sha256((TRUSTED / 'reference.json').read_bytes()).hexdigest(),
            'trace_assessment': 'separate_not_used_for_numeric_score'}


def main():
    """Print one score on success; evaluator failures never produce a stale score."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    reward_path = target.parent / 'reward.txt'
    reward_path.unlink(missing_ok=True)
    try:
        result = run(Path(args.submission))
    except Exception as error:
        result = {'reward': None, 'performance_score': None, 'evaluation_complete': False,
                  'status': 'VERIFIER_FAILURE', 'error': f'{type(error).__name__}: {error}',
                  'scoring_version': SCORING_VERSION}
    result['legacy_binary_scoring_version'] = BINARY_SCORING_VERSION
    result['binary_threshold'] = BINARY_THRESHOLD
    continuous = result.get('performance_score')
    if continuous is not None:
        if (not isinstance(continuous, (int, float)) or isinstance(continuous, bool)
                or not math.isfinite(continuous) or not 0 <= continuous <= 1):
            result.update(reward=None, performance_score=None, evaluation_complete=False,
                          status='VERIFIER_FAILURE', error='invalid continuous score')
            continuous = None
        else:
            result['continuous_score'] = continuous
            result['reward'] = continuous
    if continuous is None:
        result['continuous_score'] = None
    target.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    if result['performance_score'] is None:
        print('VERIFIER_FAILURE: see result.json', file=sys.stderr)
        return 2
    reward_path.write_text(str(result['reward']) + '\n')
    print(result['reward'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
