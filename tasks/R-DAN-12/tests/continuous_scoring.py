"""Read the author's 1.0.17 report without changing chemistry or binary decisions."""
import argparse
import json
import math
from pathlib import Path

VERSION = 'deltascience-retro-continuous-1.0.17'


def number(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 100:
        raise ValueError('invalid native chemical score')
    return value


def map_report(report):
    if report.get('variants') != ['open'] or report.get('score_scope') != 'top5_quality_multi_current_gold':
        raise ValueError('author 1.0.17 single-open report required')
    status = report.get('scientific_validation')
    if status not in ('SCORED', 'SCORED_SUFFICIENT_PASS_EVIDENCE', 'NO_EVALUABLE_SUBMISSION'):
        raise ValueError('native evaluation incomplete: ' + str(status))
    binary = report.get('harbor_reward')
    if type(binary) is not int or binary not in (0, 1):
        raise ValueError('missing original binary decision')
    gold = number(report['gold_baseline']['score'])
    rows = report['route_scores']['open']
    if not isinstance(rows, list) or len(rows) > 5:
        raise ValueError('invalid top-five route list')
    ids = [r.get('route_id') for r in rows]
    if any(not isinstance(i, str) or not i for i in ids) or len(ids) != len(set(ids)):
        raise ValueError('invalid route identities')
    scored, unresolved, ineligible = [], [], []
    for row in rows:
        state = row.get('status')
        if state == 'SCORED' and row.get('eligible') is True:
            lower = number(row['final_chemical_score_lower'])
            upper = number(row['final_chemical_score_upper'])
            if lower > upper:
                raise ValueError('reversed native bounds')
            raw = row.get('final_chemical_score')
            if raw is not None and not (lower == number(raw) == upper):
                raise ValueError('exact score contradicts native bounds')
            scored.append((raw, lower, upper))
        elif state == 'INELIGIBLE' and row.get('eligible') is False:
            ineligible.append(row['route_id'])
        elif state in ('PENDING_EVIDENCE', 'INFRASTRUCTURE_ERROR'):
            unresolved.append(row['route_id'])
        else:
            raise ValueError('unexpected open-route scoring status')
    lower = max((r[1] for r in scored), default=0.0)
    upper = max((r[2] for r in scored), default=0.0)
    best = report['best_route_scores']['open']
    exact = all(r[0] is not None for r in scored)
    expected = max((r[0] for r in scored), default=0.0) if exact else None
    if best != expected or (best is not None and number(best) != expected):
        raise ValueError('best score does not match native route scores')
    if binary != int(bool(scored) and lower >= gold):
        raise ValueError('binary decision contradicts native evidence')
    if status == 'NO_EVALUABLE_SUBMISSION' and rows:
        raise ValueError('no-submission status contradicts route list')
    base = dict(scoring_version=VERSION, raw_score=best, raw_score_scale=[0, 100],
                gold_baseline_score=gold, legacy_binary_reward=binary,
                native_scientific_validation=status, unresolved_route_ids=unresolved,
                ineligible_route_ids=ineligible, lower_bound_raw_score=lower,
                upper_bound_raw_score=100 if unresolved else upper,
                source='score_breakdown.json:best_route_scores.open')
    if unresolved or not exact:
        if binary != 1 or status != 'SCORED_SUFFICIENT_PASS_EVIDENCE':
            raise ValueError('incomplete evaluation lacks a native passing witness')
        # A completed binary verdict can coexist with an unknown continuous maximum.
        if best != 100:
            return {**base, 'score_status': 'incomplete', 'reward': None,
                    'raw_score_is_measurement': False,
                    'reason': 'Original binary verdict retained; continuous maximum is unresolved'}
    if not scored:
        if unresolved or binary:
            raise ValueError('contradictory empty score set')
        return {**base, 'score_status': 'no_evaluable_submission', 'reward': 0.0,
                'raw_score_is_measurement': False}
    return {**base, 'score_status': 'scored', 'reward': best / 100,
            'raw_score_is_measurement': True}


def publish(logs, relay_exit=0):
    logs = Path(logs)
    logs.mkdir(parents=True, exist_ok=True)
    for name in ('reward.txt', 'reward.json', 'reward.txt.tmp', 'continuous_score.json'):
        (logs / name).unlink(missing_ok=True)
    try:
        if relay_exit:
            raise ValueError('native relay failed: ' + str(relay_exit))
        result = map_report(json.loads((logs / 'score_breakdown.json').read_text()))
    except Exception as error:
        result = dict(scoring_version=VERSION, score_status='error', reward=None, reason=str(error))
    (logs / 'continuous_score.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    if result['reward'] is None:
        return 86
    temporary = logs / 'reward.txt.tmp'
    temporary.write_text(repr(result['reward']) + '\n')
    temporary.replace(logs / 'reward.txt')
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--logs', default='/logs/verifier')
    parser.add_argument('--relay-exit', type=int, default=0)
    args = parser.parse_args()
    raise SystemExit(publish(args.logs, args.relay_exit))
