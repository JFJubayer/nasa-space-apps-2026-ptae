"""Multi-dimensional analog scoring: terrain (measured), environment (measured), geology (curated)."""

import math

import numpy as np

DEFAULT_DIMENSION_WEIGHTS = {"terrain": 0.5, "environment": 0.25, "geology": 0.25}
TERRAIN_SIGMA_MEDIAN = 0.55  # ln units: a factor of ~1.7 in median slope gives similarity ~0.61
TERRAIN_SIGMA_HETEROGENEITY = 0.45  # ln units on the p90/median slope ratio
ENVIRONMENT_FEATURES = ("t_mean_c", "t_daily_range_c", "precip_mm_yr", "rel_humidity_pct", "surface_pressure_kpa")
FEATURE_LABELS = {
    "t_mean_c": "mean annual air temperature (C)",
    "t_daily_range_c": "mean daily temperature range (C)",
    "precip_mm_yr": "precipitation (mm/yr)",
    "rel_humidity_pct": "relative humidity (%)",
    "surface_pressure_kpa": "surface pressure (kPa)",
}


def _common_baselines(target_sig, candidate_sig):
    shared = [b for b in target_sig["baselines_m"] if b in candidate_sig["baselines_m"]]
    if not shared:
        raise ValueError("signatures share no baselines")
    return shared


def _profile(sig, baselines):
    index = {b: i for i, b in enumerate(sig["baselines_m"])}
    median = np.array([max(sig["median_slope_deg"][index[b]], 1e-3) for b in baselines])
    p90 = np.array([max(sig["p90_slope_deg"][index[b]], 1e-3) for b in baselines])
    return np.log(median), np.log(p90 / median)


def terrain_similarity(target_sig, candidate_sig, valid_baselines=None, sigma_scale=1.0):
    """Gaussian similarity of log-median-slope and slope-heterogeneity profiles over shared baselines."""
    baselines = _common_baselines(target_sig, candidate_sig)
    if valid_baselines is not None:
        baselines = [b for b in baselines if b in valid_baselines]
        if not baselines:
            raise ValueError("no valid baselines remain")
    t_med, t_het = _profile(target_sig, baselines)
    c_med, c_het = _profile(candidate_sig, baselines)
    d_med = math.sqrt(float(np.mean((c_med - t_med) ** 2)))
    d_het = math.sqrt(float(np.mean((c_het - t_het) ** 2)))
    s_med = TERRAIN_SIGMA_MEDIAN * sigma_scale
    s_het = TERRAIN_SIGMA_HETEROGENEITY * sigma_scale
    return float(math.exp(-0.5 * ((d_med / s_med) ** 2 + (d_het / s_het) ** 2)))


def clipped_environment_target(earth_floor):
    return {k: float(earth_floor[k]) for k in ENVIRONMENT_FEATURES}


def environment_similarity(site_climate, env_target, sigma, sigma_scale=1.0):
    """Mean Gaussian similarity to the Earth-achievable environmental target; returns (score, per-feature)."""
    per_feature = {}
    for name in ENVIRONMENT_FEATURES:
        diff = float(site_climate[name]) - env_target[name]
        per_feature[name] = float(math.exp(-0.5 * (diff / (sigma[name] * sigma_scale)) ** 2))
    return float(np.mean(list(per_feature.values()))), per_feature


def geology_similarity(site_tags, target_tags):
    """Weighted recall: how much of what the target needs does the site offer (tag values 0, 0.5, 1)."""
    total = sum(target_tags.values())
    if total <= 0:
        return 0.0
    return float(sum(weight * float(site_tags.get(tag, 0.0)) for tag, weight in target_tags.items()) / total)


SCORE_FLOOR = 0.02


def composite_aci(terrain, environment, geology, weights=None, aggregation="geometric"):
    """Combine the three dimensions into a 0-100 index.

    'geometric' (default) is non-compensatory: a site must be adequate on every dimension, so a steep, wet
    alpine valley cannot win on slope statistics alone. 'additive' is the compensatory weighted mean.
    """
    weights = weights or DEFAULT_DIMENSION_WEIGHTS
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("weights must sum to a positive value")
    scores = {"terrain": terrain, "environment": environment, "geology": geology}
    if aggregation == "additive":
        return float(100.0 * sum(weights[k] * scores[k] for k in scores) / total)
    if aggregation != "geometric":
        raise ValueError("aggregation must be 'geometric' or 'additive'")
    log_sum = sum(weights[k] * math.log(max(scores[k], SCORE_FLOOR)) for k in scores)
    return float(100.0 * math.exp(log_sum / total))


def describe_gaps(target_sig, candidate_sig, site_climate, env_target, valid_baselines, env_sigma, limit=4):
    """Rank the largest, human-readable mismatches between a site and its target."""
    gaps = []
    baselines = [b for b in _common_baselines(target_sig, candidate_sig) if b in valid_baselines]
    if baselines:
        t_med, _ = _profile(target_sig, baselines)
        c_med, _ = _profile(candidate_sig, baselines)
        index = len(baselines) // 2
        ratio = math.exp(c_med[index] - t_med[index])
        gaps.append((
            abs(math.log(ratio)) / TERRAIN_SIGMA_MEDIAN,
            f"Median slope over {baselines[index]} m is {math.exp(c_med[index]):.2f} deg vs "
            f"{math.exp(t_med[index]):.2f} deg on the target ({ratio:.1f}x).",
        ))
    for name in ENVIRONMENT_FEATURES:
        value = float(site_climate[name])
        diff = value - env_target[name]
        gaps.append((
            abs(diff) / env_sigma[name],
            f"{FEATURE_LABELS[name][0].upper() + FEATURE_LABELS[name][1:]} is {value:.1f} vs the Earth-achievable target {env_target[name]:.1f}.",
        ))
    gaps.sort(key=lambda item: item[0], reverse=True)
    return [text for score, text in gaps[:limit] if score > 0.75]


def robust_rank_statistics(components, weights_default=None, draws=1000, seed=7):
    """Rank distribution under random dimension weights and terrain tolerance-scale perturbation.

    components: site_id -> {'terrain_by_scale': scores at sigma scales (0.5, 1, 2), 'environment', 'geology'}.
    """
    rng = np.random.default_rng(seed)
    site_ids = list(components)
    scales = (0.5, 1.0, 2.0)
    base = np.array(list((weights_default or DEFAULT_DIMENSION_WEIGHTS).values()))
    ranks = np.zeros((draws, len(site_ids)), dtype=int)
    for draw in range(draws):
        weights = rng.dirichlet(base * 8.0)
        scale_index = rng.integers(len(scales))
        scores = np.array([
            composite_aci(
                components[s]["terrain_by_scale"][scale_index],
                components[s]["environment"],
                components[s]["geology"],
                dict(zip(("terrain", "environment", "geology"), weights)),
            )
            for s in site_ids
        ])
        order = np.argsort(-scores, kind="stable")
        ranks[draw, order] = np.arange(1, len(site_ids) + 1)
    stats = {}
    for column, site_id in enumerate(site_ids):
        values = ranks[:, column]
        stats[site_id] = {
            "rank_p10": int(np.percentile(values, 10)),
            "rank_median": int(np.median(values)),
            "rank_p90": int(np.percentile(values, 90)),
            "prob_top1": float(np.mean(values == 1)),
            "prob_top3": float(np.mean(values <= 3)),
            "prob_top5": float(np.mean(values <= 5)),
        }
    return stats


def auc_separation(scores_positive, scores_negative):
    """P(random positive outranks random negative); ties count one half."""
    pos = np.asarray(scores_positive, dtype=float)
    neg = np.asarray(scores_negative, dtype=float)
    if pos.size == 0 or neg.size == 0:
        return float("nan")
    greater = (pos[:, None] > neg[None, :]).sum()
    ties = (pos[:, None] == neg[None, :]).sum()
    return float((greater + 0.5 * ties) / (pos.size * neg.size))
