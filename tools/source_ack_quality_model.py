"""Deterministic offline analysis for a prospective source ACK-quality signal.

This module only scores observations made under the existing R policy. It
neither changes simulator actions nor establishes a new routing algorithm.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import ceil, exp, expm1, fsum, isfinite, log, log1p
from random import Random
from statistics import mean
from typing import Iterable, Mapping, Any, Sequence


@dataclass(frozen=True)
class EligibleRow:
    seed: int
    flow_id: int
    initial_r_tx_id: int
    q: int
    ack_age_s: float
    one_hop: int
    prior_r_miss: int
    y_no_ack: int

    @property
    def path_type(self) -> str:
        return "direct" if self.one_hop else "multihop"


def prepare_eligible_rows(cohort: Iterable[Mapping[str, Any]]) -> list[EligibleRow]:
    """Validate raw initial-R rows and retain those with a prior local ACK."""

    prepared = []
    seen: set[tuple[int, int, int]] = set()
    seen_flows: set[tuple[int, int]] = set()
    for raw in cohort:
        seed, flow_id, tx_id = (raw[key] for key in
                                ("seed", "flow_id", "initial_r_tx_id"))
        if any(type(value) is not int or value < 0 for value in
               (seed, flow_id, tx_id)):
            raise ValueError("seed, flow ID and TX ID must be nonnegative integers")
        key = (seed, flow_id, tx_id)
        if key in seen:
            raise ValueError(f"duplicate initial R row key: {key}")
        if (seed, flow_id) in seen_flows:
            raise ValueError(f"duplicate initial R flow: {(seed, flow_id)}")
        seen.add(key)
        seen_flows.add((seed, flow_id))
        path_type, hops = raw["path_type"], raw["hop_count"]
        if not ((path_type == "direct" and hops == 1)
                or (path_type == "multihop" and type(hops) is int and hops > 1)):
            raise ValueError(f"inconsistent path type/hop count: {key}")
        prior_miss = raw["prior_r_miss"]
        acked = raw["initial_r_ack_by_guard"]
        if prior_miss not in (0, 1) or type(acked) is not bool:
            raise ValueError(f"invalid prior miss or ACK label: {key}")
        q = raw["q"]
        if q is not None and raw.get("feature_exclusion_reason") not in (None, ""):
            raise ValueError(f"excluded initial R row supplies q: {key}")
        if q is None:
            if raw["prior_ack_age_s"] is not None:
                raise ValueError(f"missing q with ACK age: {key}")
            continue
        age = raw["prior_ack_age_s"]
        if (type(q) is not int or not -126 <= q <= 126
                or age is None or not isfinite(age) or age < 0):
            raise ValueError(f"invalid ACK quality or age: {key}")
        prepared.append(EligibleRow(
            seed, flow_id, tx_id, q, float(age),
            int(path_type == "direct"), int(prior_miss), int(not acked),
        ))
    return sorted(prepared, key=lambda r: (r.seed, r.flow_id, r.initial_r_tx_id))


def _prepare_quality_rows(
    raw: list[Mapping[str, Any]], quality_field: str,
) -> list[EligibleRow]:
    """Select modeling quality only after primary-q eligibility is fixed."""

    if quality_field not in ("q", "q_clean"):
        raise ValueError("quality_field must be q or q_clean")
    eligible = prepare_eligible_rows(raw)
    if quality_field == "q":
        return eligible
    clean_by_key = {
        (row["seed"], row["flow_id"], row["initial_r_tx_id"]): row.get("q_clean")
        for row in raw
    }
    selected = []
    for row in eligible:
        key = (row.seed, row.flow_id, row.initial_r_tx_id)
        clean = clean_by_key[key]
        if type(clean) is not int or not -126 <= clean <= 126:
            raise ValueError(f"missing or invalid q_clean for eligible initial R row: {key}")
        selected.append(replace(row, q=clean))
    return selected


def _features(row: EligibleRow, include_q: bool) -> tuple[float, ...]:
    base = (1.0, float(row.one_hop), float(row.prior_r_miss),
            log1p(row.ack_age_s / 30.0))
    return base + ((row.q / 12.0,) if include_q else ())


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + exp(-z))
    ez = exp(z)
    return ez / (1.0 + ez)


def objective_derivatives(
    rows: Iterable[EligibleRow], coefficients: Sequence[float], *, include_q: bool,
) -> tuple[float, tuple[float, ...], tuple[tuple[float, ...], ...]]:
    """Return the ridge-logistic sum objective, exact gradient and Hessian."""

    data = sorted(rows, key=lambda r: (r.seed, r.flow_id, r.initial_r_tx_id))
    size = 5 if include_q else 4
    if not data or len(coefficients) != size or not all(
        isfinite(value) for value in coefficients
    ):
        raise ValueError("nonempty rows and finite coefficients of model width required")
    loss = 0.5 * sum(value * value for value in coefficients[1:])
    gradient = [0.0] + list(coefficients[1:])
    hessian = [[float(i == j and i > 0) for j in range(size)]
               for i in range(size)]
    for row in data:
        x = _features(row, include_q)
        z = sum(b * xi for b, xi in zip(coefficients, x))
        loss += max(z, 0.0) + log1p(exp(-abs(z))) - row.y_no_ack * z
        p = _sigmoid(z)
        residual = p - row.y_no_ack
        curvature = p * (1.0 - p)
        for i in range(size):
            gradient[i] += residual * x[i]
            for j in range(size):
                hessian[i][j] += curvature * x[i] * x[j]
    if not (isfinite(loss) and all(isfinite(v) for v in gradient)
            and all(isfinite(v) for line in hessian for v in line)):
        raise ValueError("nonfinite ridge-logistic objective or derivative")
    return loss, tuple(gradient), tuple(tuple(line) for line in hessian)


def _objective_difference(
    rows: list[EligibleRow], coefficients: Sequence[float],
    candidate: Sequence[float], *, include_q: bool,
) -> float:
    """Evaluate candidate-minus-current loss without subtracting total losses."""

    change = tuple(new - old for old, new in zip(coefficients, candidate))
    terms = [old * step + 0.5 * step * step
             for old, step in zip(coefficients[1:], change[1:])]
    for row in rows:
        features = _features(row, include_q)
        z = fsum(beta * value for beta, value in zip(coefficients, features))
        step_z = fsum(step * value for step, value in zip(change, features))
        sign = 1 - 2 * row.y_no_ack
        a, step_a = sign * z, sign * step_z
        if abs(step_a) <= 1.0:
            terms.append(log1p(_sigmoid(a) * expm1(step_a)))
        else:
            new_a = a + step_a
            terms.append(
                max(new_a, 0.0) + log1p(exp(-abs(new_a)))
                - max(a, 0.0) - log1p(exp(-abs(a)))
            )
    difference = fsum(terms)
    if not isfinite(difference):
        raise ModelFitError("nonfinite ridge-logistic objective difference")
    return difference


class ModelFitError(ValueError):
    """A prespecified fit cannot meet its numerical or label conditions."""


def _solve_linear(matrix: Sequence[Sequence[float]], rhs: Sequence[float]) -> list[float]:
    """Gaussian elimination with deterministic first-maximum partial pivoting."""

    n = len(rhs)
    a = [list(row) + [value] for row, value in zip(matrix, rhs)]
    for column in range(n):
        pivot = max(range(column, n), key=lambda i: abs(a[i][column]))
        if not isfinite(a[pivot][column]) or abs(a[pivot][column]) <= 1e-14:
            raise ModelFitError("nonsolvable logistic Hessian")
        a[column], a[pivot] = a[pivot], a[column]
        scale = a[column][column]
        for i in range(column + 1, n):
            factor = a[i][column] / scale
            for j in range(column + 1, n + 1):
                a[i][j] -= factor * a[column][j]
            a[i][column] = 0.0
    solution = [0.0] * n
    for i in range(n - 1, -1, -1):
        solution[i] = (a[i][n] - sum(a[i][j] * solution[j]
                                     for j in range(i + 1, n))) / a[i][i]
    if not all(isfinite(value) for value in solution):
        raise ModelFitError("nonfinite Newton direction")
    return solution


def _newton_fit(
    rows: list[EligibleRow], include_q: bool, free: tuple[int, ...],
) -> tuple[float, ...]:
    failures = sum(row.y_no_ack for row in rows)
    successes = len(rows) - failures
    coefficients = [log((failures + 0.5) / (successes + 0.5))]
    coefficients.extend([0.0] * (4 if include_q else 3))
    for iteration in range(101):
        _, gradient, hessian = objective_derivatives(
            rows, coefficients, include_q=include_q,
        )
        if max(abs(gradient[i]) for i in free) <= 1e-8:
            return tuple(coefficients)
        if iteration == 100:
            break
        direction_free = _solve_linear(
            [[hessian[i][j] for j in free] for i in free],
            [-gradient[i] for i in free],
        )
        dot = sum(gradient[i] * step for i, step in zip(free, direction_free))
        if not isfinite(dot) or dot >= 0:
            raise ModelFitError("Newton direction is not a descent direction")
        for exponent in range(31):
            step_size = 2.0 ** -exponent
            candidate = coefficients.copy()
            for i, step in zip(free, direction_free):
                candidate[i] += step_size * step
            if candidate == coefficients:
                continue
            objective_derivatives(
                rows, candidate, include_q=include_q,
            )
            if _objective_difference(
                rows, coefficients, candidate, include_q=include_q,
            ) <= 1e-4 * step_size * dot:
                coefficients = candidate
                break
        else:
            raise ModelFitError("ridge-logistic Armijo line search failed")
    raise ModelFitError("ridge-logistic Newton solver did not converge")


def fit_logistic(rows: Iterable[EligibleRow], model: str) -> tuple[float, ...]:
    """Fit M0 or constrained M1 to two-label eligible source ACK rows."""

    data = sorted(rows, key=lambda r: (r.seed, r.flow_id, r.initial_r_tx_id))
    if model not in {"M0", "M1"}:
        raise ValueError("model must be M0 or M1")
    if not data or {r.y_no_ack for r in data} != {0, 1}:
        raise ModelFitError("fit requires both ACK-outcome labels")
    include_q = model == "M1"
    size = 5 if include_q else 4
    unconstrained = _newton_fit(data, include_q, tuple(range(size)))
    if not include_q or unconstrained[-1] < 0:
        return unconstrained
    boundary = _newton_fit(data, True, (0, 1, 2, 3))
    _, gradient, _ = objective_derivatives(data, boundary, include_q=True)
    if (boundary[4] != 0 or max(abs(g) for g in gradient[:4]) > 1e-8
            or gradient[4] > 1e-8):
        raise ModelFitError("constrained M1 boundary violates KKT conditions")
    return boundary


THRESHOLD_CUTS = (-12, -6, 0, 6, 12)


def _predict(row: EligibleRow, coefficients: Sequence[float]) -> float:
    return _sigmoid(sum(b * x for b, x in zip(
        coefficients, _features(row, len(coefficients) == 5),
    )))


def _threshold_rates(rows: Iterable[EligibleRow], cut: int) -> tuple[float, float]:
    data = list(rows)
    return tuple(
        (sum(r.y_no_ack for r in data if (r.q <= cut) == lower) + 1)
        / (sum((r.q <= cut) == lower for r in data) + 2)
        for lower in (True, False)
    )


def _brier(rows: Iterable[EligibleRow], predictions: Iterable[float]) -> float:
    values = [(p - row.y_no_ack) ** 2 for row, p in zip(rows, predictions)]
    if not values:
        raise ValueError("Brier loss requires eligible rows")
    return mean(values)


def _support(rows: list[EligibleRow], *, minimum: int) -> bool:
    misses = sum(row.y_no_ack for row in rows)
    return (len(rows) >= minimum and misses >= 20
            and len(rows) - misses >= 20
            and len({row.seed for row in rows}) >= 10)


def _counts(raw: list[Mapping[str, Any]], eligible: list[EligibleRow]) -> dict[str, int]:
    misses = sum(row.y_no_ack for row in eligible)
    full_successes = sum(row["initial_r_ack_by_guard"] for row in raw)
    return {
        "initial_r": len(raw), "eligible": len(eligible),
        "missing_q": len(raw) - len(eligible),
        "r_ack_success": len(eligible) - misses, "r_ack_miss": misses,
        "full_r_ack_success": full_successes,
        "full_r_ack_miss": len(raw) - full_successes,
    }


def fit_exploration(
    cohort: Iterable[Mapping[str, Any]], seeds: Iterable[int], *,
    quality_field: str = "q",
) -> dict[str, Any]:
    """Fit frozen exploration models, LOSO diagnostics and fixed-cut T.

    A seed without eligible rows remains in coverage and seed counts but has
    neither a held-out score nor an artificial training contribution.
    """

    raw = list(cohort)
    expected = tuple(sorted(seeds))
    if not expected or len(set(expected)) != len(expected):
        raise ValueError("exploration seeds must be unique and nonempty")
    if any(row["seed"] not in expected for row in raw):
        raise ValueError("cohort contains unregistered exploration seed")
    eligible = _prepare_quality_rows(raw, quality_field)
    seed_counts: dict[int, dict[str, int]] = {}
    by_seed = {seed: [row for row in eligible if row.seed == seed]
               for seed in expected}
    for seed in expected:
        seed_counts[seed] = _counts(
            [row for row in raw if row["seed"] == seed], by_seed[seed],
        )
    if not eligible or {row.y_no_ack for row in eligible} != {0, 1}:
        raise ModelFitError("pooled exploration is empty or one-class")
    contributing = [seed for seed in expected if by_seed[seed]]
    for seed in contributing:
        training = [row for row in eligible if row.seed != seed]
        if {row.y_no_ack for row in training} != {0, 1}:
            raise ModelFitError(f"held-out seed {seed} leaves one-class training")

    loso_brier: dict[int, dict[str, float]] = {}
    cut_losses = {cut: [] for cut in THRESHOLD_CUTS}
    for seed in contributing:
        training = [row for row in eligible if row.seed != seed]
        held_out = by_seed[seed]
        m0 = fit_logistic(training, "M0")
        m1 = fit_logistic(training, "M1")
        loso_brier[seed] = {
            "M0": _brier(held_out, (_predict(row, m0) for row in held_out)),
            "M1": _brier(held_out, (_predict(row, m1) for row in held_out)),
        }
        for cut in THRESHOLD_CUTS:
            lower, upper = _threshold_rates(training, cut)
            cut_losses[cut].append(_brier(
                held_out, (lower if row.q <= cut else upper for row in held_out),
            ))
    threshold_loso_brier = {cut: mean(losses)
                            for cut, losses in cut_losses.items()}
    cut = min(THRESHOLD_CUTS,
              key=lambda candidate: (threshold_loso_brier[candidate],
                                     abs(candidate), candidate))
    path_counts = {}
    path_support = {}
    for path in ("direct", "multihop"):
        part = [row for row in eligible if row.path_type == path]
        contributing = sorted({row.seed for row in part})
        path_support[path] = _support(part, minimum=80)
        path_counts[path] = {
            **_counts([row for row in raw if row["path_type"] == path], part),
            "contributing_seeds": contributing,
            "zero_row_seeds": [seed for seed in expected
                               if seed not in contributing],
            "support": path_support[path],
        }
    coverage = len(eligible) / len(raw) if raw else 0.0
    pooled_support = coverage >= 0.75 and _support(eligible, minimum=200)
    result = {
        "seed_counts": seed_counts,
        "pooled_counts": _counts(raw, eligible),
        "path_counts": path_counts,
        "coverage": coverage,
        "loso_brier": loso_brier,
        "threshold_loso_brier": threshold_loso_brier,
        "threshold_cut": cut,
        "threshold_rates": _threshold_rates(eligible, cut),
        "m0_coefficients": fit_logistic(eligible, "M0"),
        "m1_coefficients": fit_logistic(eligible, "M1"),
        "support": {
            "pooled": pooled_support,
            "direct": path_support["direct"],
            "multihop": path_support["multihop"],
            "ready_for_validation": pooled_support and any(path_support.values()),
        },
    }
    if quality_field == "q_clean":
        result["quality_field"] = quality_field
    return result


def bootstrap_seed_indices(
    seeds: Iterable[int], stratum: str, statistic: str,
) -> tuple[tuple[int, ...], ...]:
    """Return the frozen 1000 seed-bootstrap draws, including duplicates."""

    ordered = tuple(sorted(seeds))
    if (not ordered or len(set(ordered)) != len(ordered)
            or any(type(seed) is not int for seed in ordered)):
        raise ValueError("bootstrap seed IDs must be distinct numeric integers")
    strata = {"pooled": 0, "direct": 1, "multihop": 2}
    metrics = {"Delta_0": 0, "Delta_T": 1, "q_auc": 2}
    if stratum not in strata or statistic not in metrics:
        raise ValueError("unknown bootstrap stratum or statistic")
    rng = Random(43000 + 10 * strata[stratum] + metrics[statistic])
    n = len(ordered)
    return tuple(tuple(ordered[rng.randrange(n)] for _ in range(n))
                 for _ in range(1000))


def _nearest_rank_interval(values: Iterable[float]) -> dict[str, float | int]:
    ordered = sorted(values)
    count = len(ordered)
    if count < 950 or not all(isfinite(value) for value in ordered):
        raise ValueError("bootstrap has fewer than 950 finite valid attempts")
    return {
        "valid_attempts": count,
        "lower": ordered[ceil(0.025 * count) - 1],
        "upper": ordered[ceil(0.975 * count) - 1],
    }


def bootstrap_delta_interval(
    per_seed_delta: Mapping[int, float], stratum: str, statistic: str,
) -> dict[str, float | int]:
    """Bootstrap an equal-seed paired Brier improvement."""

    if statistic not in {"Delta_0", "Delta_T"} or not per_seed_delta:
        raise ValueError("Delta bootstrap requires per-seed paired differences")
    if not all(isfinite(value) for value in per_seed_delta.values()):
        raise ValueError("nonfinite paired Brier difference")
    draws = bootstrap_seed_indices(per_seed_delta, stratum, statistic)
    estimates = [mean(per_seed_delta[seed] for seed in draw) for draw in draws]
    return {"mean": mean(per_seed_delta.values()),
            **_nearest_rank_interval(estimates)}


def rank_auc(rows: Iterable[EligibleRow]) -> float:
    """Rank AUC for the prespecified q-only failure-risk score -q."""

    data = sorted(rows, key=lambda row: -row.q)
    positives = sum(row.y_no_ack for row in data)
    negatives = len(data) - positives
    if positives == 0 or negatives == 0:
        raise ValueError("AUC requires both ACK-outcome labels")
    positive_rank_sum = 0.0
    cursor = 0
    while cursor < len(data):
        end = cursor + 1
        while end < len(data) and data[end].q == data[cursor].q:
            end += 1
        average_rank = (cursor + 1 + end) / 2.0
        positive_rank_sum += average_rank * sum(
            row.y_no_ack for row in data[cursor:end]
        )
        cursor = end
    return ((positive_rank_sum - positives * (positives + 1) / 2)
            / (positives * negatives))


def bootstrap_auc_interval(
    by_seed: Mapping[int, Sequence[EligibleRow]], stratum: str,
) -> dict[str, float | int]:
    """Bootstrap pooled rank AUC with invalid one-class draws left invalid."""

    attempts = []
    for draw in bootstrap_seed_indices(by_seed, stratum, "q_auc"):
        sampled = [row for seed in draw for row in by_seed[seed]]
        try:
            attempts.append(rank_auc(sampled))
        except ValueError as error:
            if "both ACK-outcome labels" not in str(error):
                raise
    return {"auc": rank_auc(row for part in by_seed.values() for row in part),
            **_nearest_rank_interval(attempts)}


def _score_population(
    rows: list[EligibleRow], stratum: str, frozen: Mapping[str, Any],
) -> dict[str, Any]:
    by_seed = {seed: [row for row in rows if row.seed == seed]
               for seed in sorted({row.seed for row in rows})}
    brier = {}
    cut = frozen["threshold_cut"]
    lower, upper = frozen["threshold_rates"]
    for seed, part in by_seed.items():
        brier[seed] = {
            "M0": _brier(part, (_predict(row, frozen["m0_coefficients"])
                                for row in part)),
            "M1": _brier(part, (_predict(row, frozen["m1_coefficients"])
                                for row in part)),
            "T": _brier(part, (lower if row.q <= cut else upper
                               for row in part)),
        }
    delta_0 = bootstrap_delta_interval(
        {seed: values["M0"] - values["M1"] for seed, values in brier.items()},
        stratum, "Delta_0",
    )
    delta_t = bootstrap_delta_interval(
        {seed: values["T"] - values["M1"] for seed, values in brier.items()},
        stratum, "Delta_T",
    )
    return {
        "seed_brier": brier,
        "equal_seed_brier": {model: mean(item[model] for item in brier.values())
                             for model in ("M0", "M1", "T")},
        "Delta_0": delta_0,
        "Delta_T": delta_t,
        "q_auc": bootstrap_auc_interval(by_seed, stratum),
    }


def _improvement_gate(score: Mapping[str, Any], *, path_claim: bool) -> bool:
    improvements = (score["Delta_0"], score["Delta_T"])
    return (all(delta["mean"] >= 0.005 and delta["lower"] > 0
                for delta in improvements)
            and (not path_claim or score["q_auc"]["lower"] > 0.5))


def score_validation(
    cohort: Iterable[Mapping[str, Any]], seeds: Iterable[int],
    exploration_fit: Mapping[str, Any], *, quality_field: str = "q",
) -> dict[str, Any]:
    """Score untouched validation rows with only frozen exploration models.

    Insufficient validation support returns an explicit unscored NO-GO.
    Frozen exploration support must be satisfied before this call.
    """

    if exploration_fit["support"]["ready_for_validation"] is not True:
        raise ValueError("exploration support did not authorize validation")
    if exploration_fit.get("quality_field", "q") != quality_field:
        raise ValueError("frozen exploration quality_field differs from requested quality_field")
    m0, m1 = (exploration_fit[key] for key in
              ("m0_coefficients", "m1_coefficients"))
    rates = exploration_fit["threshold_rates"]
    cut = exploration_fit["threshold_cut"]
    if (len(m0) != 4 or len(m1) != 5
            or not all(isfinite(value) for value in (*m0, *m1))
            or m1[4] > 0 or cut not in THRESHOLD_CUTS
            or len(rates) != 2 or not all(isfinite(rate) and 0 < rate < 1
                                            for rate in rates)):
        raise ValueError("invalid frozen exploration model")
    expected = tuple(sorted(seeds))
    if not expected or len(set(expected)) != len(expected):
        raise ValueError("validation seeds must be unique and nonempty")
    raw = list(cohort)
    if any(row["seed"] not in expected for row in raw):
        raise ValueError("cohort contains unregistered validation seed")
    eligible = _prepare_quality_rows(raw, quality_field)
    seed_counts = {}
    by_seed = {seed: [row for row in eligible if row.seed == seed]
               for seed in expected}
    for seed in expected:
        seed_counts[seed] = _counts(
            [row for row in raw if row["seed"] == seed], by_seed[seed],
        )
    path_counts = {}
    for path in ("direct", "multihop"):
        part = [row for row in eligible if row.path_type == path]
        contributing = sorted({row.seed for row in part})
        path_counts[path] = {
            **_counts([row for row in raw if row["path_type"] == path], part),
            "contributing_seeds": contributing,
            "zero_row_seeds": [seed for seed in expected
                               if seed not in contributing],
            "support": _support(part, minimum=80),
        }
    result: dict[str, Any] = {
        "seed_counts": seed_counts,
        "pooled_counts": _counts(raw, eligible),
        "path_counts": path_counts,
        "pooled": None, "direct": None, "multihop": None,
        "gate": {"go": False},
    }
    zero_seeds = [seed for seed in expected if not by_seed[seed]]
    if zero_seeds:
        result["gate"]["reason"] = f"zero eligible validation seed: {zero_seeds}"
        return result
    if not _support(eligible, minimum=200):
        result["gate"]["reason"] = "pooled validation support failed"
        return result
    try:
        result["pooled"] = _score_population(eligible, "pooled", exploration_fit)
    except ValueError as error:
        if "bootstrap has fewer than 950" not in str(error):
            raise
        result["gate"]["reason"] = str(error)
        return result
    bootstrap_failures = {}
    for path in ("direct", "multihop"):
        if (exploration_fit["support"].get(path) is True
                and path_counts[path]["support"]):
            part = [row for row in eligible if row.path_type == path]
            try:
                result[path] = _score_population(part, path, exploration_fit)
            except ValueError as error:
                if "bootstrap has fewer than 950" not in str(error):
                    raise
                bootstrap_failures[path] = str(error)
    pooled_gate = _improvement_gate(result["pooled"], path_claim=False)
    path_gate = {
        path: result[path] is not None
        and _improvement_gate(result[path], path_claim=True)
        for path in ("direct", "multihop")
    }
    result["gate"] = {
        "pooled": pooled_gate,
        "direct": path_gate["direct"],
        "multihop": path_gate["multihop"],
        "go": pooled_gate and any(path_gate.values()),
    }
    if bootstrap_failures:
        result["gate"]["bootstrap_failures"] = bootstrap_failures
    if not result["gate"]["go"]:
        result["gate"]["reason"] = (
            "bootstrap has fewer than 950 valid attempts"
            if bootstrap_failures else "paired-gain or path-type gate failed"
        )
    return result
