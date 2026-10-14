from collections.abc import Mapping
from numbers import Real

import numpy as np

DEFAULT_WEIGHTS = {
    "slope_mean": 0.30,
    "slope_std": 0.15,
    "tri_mean": 0.25,
    "tri_std": 0.15,
    "elevation_std": 0.15
}


def _finite_real(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number")
    try:
        value = float(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite real number") from exc
    if not np.isfinite(value):
        raise ValueError(f"{name} must be a finite real number")
    return value


def compute_metric_similarity(target_val, candidate_val, tolerance_scale=1.0):
    """
    Computes a normalized similarity [0, 1] between two scalar metrics using Gaussian decay.
    1.0 means exact match, approaching 0 as values diverge.
    """
    target_val = _finite_real(target_val, "target_val")
    candidate_val = _finite_real(candidate_val, "candidate_val")
    tolerance_scale = _finite_real(tolerance_scale, "tolerance_scale")

    if tolerance_scale <= 0:
        tolerance_scale = 1.0
    diff = abs(target_val - candidate_val)
    sigma = max(abs(target_val) * 0.5, tolerance_scale)
    similarity = np.exp(-0.5 * (diff / sigma) ** 2)
    return float(similarity)

def calculate_analog_compatibility_index(target_sig, candidate_sig, weights=None, environmental_boost=0.0):
    """
    Calculates the Analog Compatibility Index (ACI) on a 0-100 scale.
    Adds up to five environmental bonus points to topographical congruence.
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    if not isinstance(target_sig, Mapping) or not isinstance(candidate_sig, Mapping):
        raise ValueError("target_sig and candidate_sig must be mappings")
    if not isinstance(weights, Mapping):
        raise ValueError("weights must be a mapping")

    unknown_metrics = set(weights) - set(DEFAULT_WEIGHTS)
    if unknown_metrics:
        raise ValueError(f"unknown metric weight(s): {', '.join(map(str, sorted(unknown_metrics, key=str)))}")

    validated_weights = {}
    for metric, weight in weights.items():
        weight = _finite_real(weight, f"weight for {metric}")
        if weight < 0:
            raise ValueError(f"weight for {metric} must be nonnegative")
        validated_weights[metric] = weight

    total_weight = sum(validated_weights.values())
    if not np.isfinite(total_weight):
        raise ValueError("total weight must be finite")
    if total_weight <= 0:
        raise ValueError("total weight must be greater than zero")

    environmental_boost = _finite_real(environmental_boost, "environmental_boost")
    if environmental_boost < 0:
        raise ValueError("environmental_boost must be nonnegative")
    if environmental_boost > 5.0:
        raise ValueError("environmental_boost must not exceed five ACI points")

    scores = {}
    weighted_score = 0.0

    for metric, weight in validated_weights.items():
        if metric not in target_sig:
            raise ValueError(f"target_sig is missing required metric: {metric}")
        if metric not in candidate_sig:
            raise ValueError(f"candidate_sig is missing required metric: {metric}")

        t_val = _finite_real(target_sig[metric], f"target_sig[{metric}]")
        c_val = _finite_real(candidate_sig[metric], f"candidate_sig[{metric}]")
        if t_val < 0 or c_val < 0:
            raise ValueError(f"metric values for {metric} must be nonnegative")

        sim = compute_metric_similarity(t_val, c_val, tolerance_scale=max(t_val * 0.3, 1.0))
        scores[metric] = sim
        weighted_score += sim * weight

    base_aci = (weighted_score / total_weight) * 100.0
    perfect_match = all(
        scores[metric] == 1.0
        for metric, weight in validated_weights.items()
        if weight > 0
    )
    unbounded_aci = base_aci + environmental_boost
    rounded_unbounded_aci = round(unbounded_aci, 2)
    capped = unbounded_aci > 100.0 or (not perfect_match and rounded_unbounded_aci >= 100.0)
    final_aci = 100.0 if perfect_match else min(unbounded_aci, 99.99)
    
    return {
        "aci": round(final_aci, 2),
        "base_topographic_score": round(base_aci, 2),
        "applied_bonus": round(max(0.0, final_aci - base_aci), 2),
        "capped": capped,
        "sub_scores": {k: round(v * 100.0, 1) for k, v in scores.items()}
    }

def rank_candidates(target_sig, candidates_dict, weights=None, metadata=None):
    """
    Ranks a dictionary of candidate signatures against a target signature.
    candidates_dict: { 'site_name': candidate_sig, ... }
    metadata: optional dict with environmental attributes per site.
    """
    if metadata is not None and not isinstance(metadata, Mapping):
        raise ValueError("metadata must be a mapping")

    rankings = []
    
    for site_name, cand_sig in candidates_dict.items():
        environmental_flags = 0
        site_meta = metadata.get(site_name, {}) if metadata else {}
        if not isinstance(site_meta, Mapping):
            raise ValueError(f"metadata for {site_name} must be a mapping")

        for flag in ("is_hyper_arid", "is_basaltic", "has_lava_tubes"):
            if flag in site_meta and not isinstance(site_meta[flag], (bool, np.bool_)):
                raise ValueError(f"metadata flag {flag} for {site_name} must be boolean")

        # Environmental bonus for arid, polar, or volcanic basaltic geology
        if site_meta.get("is_hyper_arid", False):
            environmental_flags += 1
        if site_meta.get("is_basaltic", False):
            environmental_flags += 1
        if site_meta.get("has_lava_tubes", False):
            environmental_flags += 1
        environmental_bonus = round(5.0 * environmental_flags / 3.0, 2)
            
        result = calculate_analog_compatibility_index(
            target_sig, 
            cand_sig, 
            weights=weights, 
            environmental_boost=environmental_bonus
        )
        
        rankings.append({
            "site_name": site_name,
            "aci": result["aci"],
            "base_topographic_score": result["base_topographic_score"],
            "applied_bonus": result["applied_bonus"],
            "capped": result["capped"],
            "sub_scores": result["sub_scores"],
            "metadata": site_meta
        })
        
    # Sort descending by ACI
    rankings.sort(key=lambda x: (x["aci"], x["base_topographic_score"]), reverse=True)
    return rankings
