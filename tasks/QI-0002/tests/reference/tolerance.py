"""Certify a continuous safe prefix without assuming monotonic fidelity."""
import math


def certify(margin, lipschitz, cfg):
    """Bracket first loss, certifying every preceding interval with a global bound.

    margin(p) is minimum casewise Favg advantage. An interior result requires
    both a failing witness and a certified safe prefix; tiny unresolved
    intervals are evaluation errors, not evidence of poor performance.
    """
    values = {}
    eps = cfg['fidelity_tolerance']

    def at(p):
        """Cache finite margins and distinguish numerical failure from poor circuits."""
        if p not in values:
            if len(values) >= cfg['max_evaluations']:
                raise ArithmeticError('continuous certificate evaluation budget exhausted')
            value = float(margin(p))
            if not math.isfinite(value):
                raise ArithmeticError('nonfinite protection margin')
            values[p] = value
        return values[p]

    first = at(0.)
    if first <= eps:
        return _result(0., 0., values, 'NO_ZERO_NOISE_ADVANTAGE', first)
    upper = cfg['p_domain_max']
    stack = [(0., upper, first, at(upper))]
    safe = 0.
    while stack:
        a, b, ga, gb = stack.pop()
        width = b-a
        if min(ga, gb) - lipschitz*width/2 > eps:
            safe = b
            continue
        if width <= cfg['p_resolution'] and gb <= eps:
            return _result(safe, b, values, 'BRACKETED_FIRST_FAILURE', first)
        if width <= cfg['minimum_interval_width']:
            raise ArithmeticError('unresolved interval has no certified failure witness')
        middle = (a+b)/2
        gm = at(middle)
        stack.append((middle, b, gm, gb))
        stack.append((a, middle, ga, gm))
    return _result(upper, upper, values, 'SAFE_THROUGH_DOMAIN', first)


def _result(lower, upper, samples, status, first):
    """Keep the science interval and raw evaluation evidence separate from score."""
    return {'tolerance': lower, 'upper': upper, 'status': status,
            'zero_error_minimum_advantage': first, 'evaluations': len(samples),
            'samples': [{'p': p, 'minimum_advantage': samples[p]} for p in sorted(samples)]}
