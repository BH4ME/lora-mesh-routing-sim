"""Frozen, synthetic checks for the source-local ACK quality screen."""

import json
from math import isclose

import pytest

from tools.source_ack_quality_model import (
    bootstrap_delta_interval, bootstrap_seed_indices, fit_exploration,
    fit_logistic, objective_derivatives, prepare_eligible_rows, rank_auc,
    score_validation,
)


def _row(seed, flow_id, tx_id, q, acked, *, path_type="direct", age=3.0):
    return {
        "seed": seed,
        "flow_id": flow_id,
        "initial_r_tx_id": tx_id,
        "q": q,
        "prior_ack_age_s": age if q is not None else None,
        "path_type": path_type,
        "hop_count": 1 if path_type == "direct" else 2,
        "prior_r_miss": 0,
        "initial_r_ack_by_guard": acked,
    }


def test_prepare_eligible_rows_preserves_only_source_observable_q():
    rows = prepare_eligible_rows([
        _row(43001, 8, 3, -12, False),
        _row(43001, 9, 4, None, True),
        _row(43002, 10, 5, 6, True, path_type="multihop"),
    ])

    assert [(r.seed, r.flow_id, r.initial_r_tx_id, r.q, r.y_no_ack,
             r.one_hop, r.prior_r_miss) for r in rows] == [
        (43001, 8, 3, -12, 1, 1, 0),
        (43002, 10, 5, 6, 0, 0, 0),
    ]
    assert rows[0].ack_age_s == 3.0


def test_duplicate_initial_r_flow_or_excluded_quality_is_rejected():
    with pytest.raises(ValueError, match="duplicate initial R"):
        prepare_eligible_rows([
            _row(43001, 1, 1, -12, False),
            _row(43001, 1, 2, -12, False),
        ])
    excluded = _row(43001, 1, 1, -12, False)
    excluded["feature_exclusion_reason"] = "old_route_generation"
    with pytest.raises(ValueError, match="excluded.*q"):
        prepare_eligible_rows([excluded])


def test_ridge_logistic_derivatives_match_independent_finite_differences():
    rows = prepare_eligible_rows([
        _row(43001, 1, 2, -12, False, age=2.0),
        _row(43002, 2, 3, 12, True, path_type="multihop", age=55.0),
        _row(43003, 3, 4, 3, False, age=130.0),
    ])
    beta = (0.2, -0.3, 0.4, -0.5, -0.6)
    loss, gradient, hessian = objective_derivatives(rows, beta, include_q=True)
    eps = 1e-5
    for j in range(len(beta)):
        plus = list(beta)
        minus = list(beta)
        plus[j] += eps
        minus[j] -= eps
        loss_plus, grad_plus, _ = objective_derivatives(rows, plus, include_q=True)
        loss_minus, grad_minus, _ = objective_derivatives(rows, minus, include_q=True)
        assert isclose(gradient[j], (loss_plus - loss_minus) / (2 * eps), abs_tol=1e-8)
        for k in range(len(beta)):
            assert isclose(hessian[k][j], (grad_plus[k] - grad_minus[k]) / (2 * eps), abs_tol=1e-8)
    assert loss > 0


def test_m1_coefficient_matches_independent_symmetric_fixture():
    rows = prepare_eligible_rows([
        _row(43001, 1, 2, -12, False, age=0.0),
        _row(43002, 2, 3, 12, True, age=0.0),
    ])

    beta = fit_logistic(rows, "M1")

    assert beta[:4] == pytest.approx((0, 0, 0, 0), abs=1e-8)
    # Independent root of b + 2*sigmoid(b) = 0 for q/12 = +/-1.
    assert beta[4] == pytest.approx(-0.6748316143423994, abs=1e-8)


def test_positive_unconstrained_q_slope_refits_at_kkt_boundary():
    rows = prepare_eligible_rows([
        _row(43001, 1, 2, -12, True, age=0.0),
        _row(43002, 2, 3, 12, False, age=0.0),
    ])

    beta = fit_logistic(rows, "M1")
    _, gradient, _ = objective_derivatives(rows, beta, include_q=True)

    assert beta == pytest.approx((0, 0, 0, 0, 0), abs=1e-8)
    assert max(abs(g) for g in gradient[:4]) <= 1e-8
    assert gradient[4] <= 1e-8


def test_m0_reaches_stationarity_when_total_loss_change_is_sub_ulp():
    raw = [
        _row(1, 1, 1, 0, False, path_type="multihop", age=300.0),
        _row(1, 2, 2, 0, True, path_type="multihop", age=3.0),
        _row(1, 3, 3, 0, True, path_type="multihop", age=300.0),
        _row(1, 4, 4, 0, False, path_type="multihop", age=0.0),
    ]
    raw[2]["prior_r_miss"] = 1
    rows = prepare_eligible_rows(raw)

    coefficients = fit_logistic(rows, "M0")
    _, gradient, _ = objective_derivatives(rows, coefficients, include_q=False)

    assert max(abs(value) for value in gradient) <= 1e-8
    assert coefficients == pytest.approx(
        (0.0669226139864802, 0.0, -0.42947071671167436,
         0.03275254162149471), abs=1e-8,
    )


def test_exploration_omits_zero_eligible_seed_from_folds_not_coverage():
    cohort = [
        _row(43001, 1, 1, 0, False),
        _row(43001, 2, 2, 0, True),
        _row(43002, 3, 3, 0, False),
        _row(43002, 4, 4, 0, True),
        _row(43003, 5, 5, None, True),
    ]

    fit = fit_exploration(cohort, seeds=(43001, 43002, 43003))

    assert fit["seed_counts"][43003] == {
        "initial_r": 1, "eligible": 0, "missing_q": 1,
        "r_ack_success": 0, "r_ack_miss": 0,
        "full_r_ack_success": 1, "full_r_ack_miss": 0,
    }
    assert set(fit["loso_brier"]) == {43001, 43002}
    assert fit["threshold_cut"] == 0
    assert fit["threshold_rates"] == pytest.approx((0.5, 0.5))
    assert fit["coverage"] == pytest.approx(4 / 5)
    assert fit["pooled_counts"]["missing_q"] == 1
    assert fit["path_counts"]["direct"]["initial_r"] == 5
    assert fit["path_counts"]["direct"]["missing_q"] == 1
    assert fit["support"]["ready_for_validation"] is False


def test_exploration_rejects_one_class_training_fold():
    cohort = [
        _row(43001, 1, 1, -12, False),
        _row(43002, 2, 2, 12, True),
    ]

    with pytest.raises(ValueError, match="one-class|two-label"):
        fit_exploration(cohort, seeds=(43001, 43002))


def test_bootstrap_draw_sequence_and_nearest_rank_fixture():
    draws = bootstrap_seed_indices((9, 1, 3), "pooled", "Delta_0")

    assert draws[:5] == (
        (1, 9, 9), (1, 1, 3), (9, 3, 9), (1, 9, 1), (3, 3, 3),
    )
    interval = bootstrap_delta_interval({1: 0.0, 3: 1.0, 9: 2.0},
                                        "pooled", "Delta_0")
    assert interval["valid_attempts"] == 1000
    assert interval["mean"] == pytest.approx(1.0)
    assert interval["lower"] == pytest.approx(0.0)
    assert interval["upper"] == pytest.approx(2.0)
    # A frozen independent 7-seed fixture distinguishes rank 974 from 975.
    distinct = bootstrap_delta_interval(
        {seed: float(10 ** (seed - 1)) for seed in range(1, 8)},
        "pooled", "Delta_0",
    )
    assert distinct["lower"] == pytest.approx(1590.142857142857)
    assert distinct["upper"] == pytest.approx(444442.85714285716)


def test_rank_auc_counts_equal_q_scores_as_half():
    rows = prepare_eligible_rows([
        _row(43001, 1, 1, -12, False),
        _row(43001, 2, 2, 0, False),
        _row(43002, 3, 3, 0, True),
        _row(43002, 4, 4, 12, True),
    ])

    assert rank_auc(rows) == pytest.approx(0.875)


def test_q_only_auc_orientation_is_failure_risk_of_negative_q():
    perfect = prepare_eligible_rows([
        _row(43001, 1, 1, -10, False),
        _row(43002, 2, 2, 10, True),
    ])
    reversed_signal = prepare_eligible_rows([
        _row(43001, 1, 1, 10, False),
        _row(43002, 2, 2, -10, True),
    ])

    assert rank_auc(perfect) == 1.0
    assert rank_auc(reversed_signal) == 0.0


def _strong_validation_cohort():
    return [
        _row(seed, seed * 100 + i, seed * 1000 + i,
             -12 if i < 10 else 12, i >= 10)
        for seed in range(43101, 43111) for i in range(20)
    ]


def _dual_quality_cohort(first_seed):
    rows = [
        _row(seed, seed * 100 + i, seed * 1000 + i,
             -12 if i < 10 else 12, i >= 10)
        for seed in range(first_seed, first_seed + 10) for i in range(20)
    ]
    for row in rows:
        row["q_clean"] = -6 if row["q"] == -12 else -12
    return rows


def test_clean_quality_exploration_changes_m1_and_threshold_on_same_rows():
    rows = _dual_quality_cohort(43001)
    rows.append(_row(43001, 999999, 999999, None, True))
    seeds = tuple(range(43001, 43011))

    primary = fit_exploration(rows, seeds)
    clean = fit_exploration(rows, seeds, quality_field="q_clean")

    assert "quality_field" not in primary
    assert clean["quality_field"] == "q_clean"
    assert clean["seed_counts"] == primary["seed_counts"]
    assert clean["pooled_counts"] == primary["pooled_counts"]
    assert clean["pooled_counts"]["initial_r"] == 201
    assert clean["pooled_counts"]["eligible"] == 200
    assert clean["pooled_counts"]["missing_q"] == 1
    assert clean["path_counts"] == primary["path_counts"]
    assert clean["m0_coefficients"] == primary["m0_coefficients"]
    assert all(clean["loso_brier"][seed]["M0"] == primary["loso_brier"][seed]["M0"]
               for seed in seeds)
    assert primary["m1_coefficients"][4] < 0
    assert clean["m1_coefficients"][4] == pytest.approx(0, abs=1e-8)
    assert primary["threshold_cut"] == 0
    assert clean["threshold_cut"] == -12
    assert primary["threshold_rates"][0] > primary["threshold_rates"][1]
    assert clean["threshold_rates"][0] < clean["threshold_rates"][1]
    assert all(clean["loso_brier"][seed]["M1"] > primary["loso_brier"][seed]["M1"]
               for seed in seeds)


def test_clean_quality_validation_scores_frozen_fit_on_same_denominator():
    exploration = _dual_quality_cohort(43001)
    validation = _dual_quality_cohort(43101)
    explore_seeds = tuple(range(43001, 43011))
    validate_seeds = tuple(range(43101, 43111))
    primary_fit = fit_exploration(exploration, explore_seeds)
    clean_fit = fit_exploration(exploration, explore_seeds, quality_field="q_clean")

    primary = score_validation(validation, validate_seeds, primary_fit)
    clean = score_validation(validation, validate_seeds, clean_fit,
                             quality_field="q_clean")

    assert clean["pooled_counts"] == primary["pooled_counts"]
    assert clean["seed_counts"] == primary["seed_counts"]
    assert clean["path_counts"] == primary["path_counts"]
    assert clean["pooled"]["equal_seed_brier"]["M0"] == primary["pooled"]["equal_seed_brier"]["M0"]
    assert clean["pooled"]["equal_seed_brier"]["M1"] > primary["pooled"]["equal_seed_brier"]["M1"]
    assert primary["direct"]["q_auc"]["auc"] == 1.0
    assert clean["direct"]["q_auc"]["auc"] == 0.0
    assert clean["pooled"]["Delta_T"]["valid_attempts"] == 1000


@pytest.mark.parametrize("bad_clean", [None, True, 127, -127])
def test_clean_quality_missing_or_invalid_on_eligible_row_fails_closed(bad_clean):
    exploration = _dual_quality_cohort(43001)
    validation = _dual_quality_cohort(43101)
    clean_fit = fit_exploration(exploration, tuple(range(43001, 43011)),
                                quality_field="q_clean")
    exploration[0]["q_clean"] = bad_clean
    validation[0]["q_clean"] = bad_clean

    with pytest.raises(ValueError, match="q_clean.*eligible"):
        fit_exploration(exploration, tuple(range(43001, 43011)),
                        quality_field="q_clean")
    with pytest.raises(ValueError, match="q_clean.*eligible"):
        score_validation(validation, tuple(range(43101, 43111)), clean_fit,
                         quality_field="q_clean")


def test_validation_rejects_mismatched_frozen_quality_feature():
    exploration = _dual_quality_cohort(43001)
    validation = _dual_quality_cohort(43101)
    explore_seeds = tuple(range(43001, 43011))
    validate_seeds = tuple(range(43101, 43111))
    primary_fit = fit_exploration(exploration, explore_seeds)
    clean_fit = fit_exploration(exploration, explore_seeds, quality_field="q_clean")

    with pytest.raises(ValueError, match="quality_field"):
        score_validation(validation, validate_seeds, primary_fit,
                         quality_field="q_clean")
    with pytest.raises(ValueError, match="quality_field"):
        score_validation(validation, validate_seeds, clean_fit)


def _frozen_synthetic_fit(rates=(0.5, 0.5)):
    return {
        "support": {"ready_for_validation": True, "pooled": True,
                    "direct": True, "multihop": False},
        "m0_coefficients": (0.0, 0.0, 0.0, 0.0),
        "m1_coefficients": (0.0, 0.0, 0.0, 0.0, -2.0),
        "threshold_cut": 0,
        "threshold_rates": rates,
    }


def test_validation_requires_gain_over_both_m0_and_simple_threshold():
    rows = _strong_validation_cohort()
    seeds = tuple(range(43101, 43111))

    passing = score_validation(rows, seeds, _frozen_synthetic_fit())
    dominated = score_validation(rows, seeds, _frozen_synthetic_fit((0.99, 0.01)))

    assert passing["gate"]["go"] is True
    assert passing["direct"]["q_auc"]["lower"] == 1.0
    assert passing["direct"]["Delta_0"]["valid_attempts"] == 1000
    assert passing["multihop"] is None
    assert dominated["pooled"]["Delta_0"]["mean"] > 0
    assert dominated["pooled"]["Delta_T"]["mean"] < 0
    assert dominated["gate"]["go"] is False


def test_zero_eligible_validation_seed_is_no_go_before_scoring():
    rows = _strong_validation_cohort()
    rows.append(_row(43111, 1, 1, None, True))

    result = score_validation(rows, tuple(range(43101, 43112)),
                              _frozen_synthetic_fit())

    assert result["pooled"] is None
    assert result["gate"]["go"] is False
    assert "zero eligible" in result["gate"]["reason"]
    assert result["seed_counts"][43111]["initial_r"] == 1
    assert result["path_counts"]["direct"]["missing_q"] == 1


def test_one_class_auc_bootstraps_are_not_redrawn_or_rescued():
    rows = [
        _row(seed, seed * 100 + i, seed * 1000 + i,
             12 if seed == 43110 else -12, seed == 43110)
        for seed in range(43101, 43111) for i in range(20)
    ]

    result = score_validation(rows, tuple(range(43101, 43111)),
                              _frozen_synthetic_fit())

    assert result["gate"]["go"] is False
    assert "950" in result["gate"]["reason"]


def test_frozen_exploration_model_survives_json_round_trip():
    exploration_rows = [
        _row(seed, seed * 100 + i, seed * 1000 + i,
             -12 if i < 10 else 12, i >= 10)
        for seed in range(43001, 43011) for i in range(20)
    ]
    fit = fit_exploration(exploration_rows, tuple(range(43001, 43011)))
    frozen = json.loads(json.dumps(fit))

    result = score_validation(_strong_validation_cohort(),
                              tuple(range(43101, 43111)), frozen)

    assert fit["support"]["ready_for_validation"] is True
    assert frozen["m1_coefficients"][4] < 0
    assert result["pooled"] is not None
    assert result["pooled_counts"]["initial_r"] == 200
