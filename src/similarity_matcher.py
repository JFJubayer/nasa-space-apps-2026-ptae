import numpy as np

DEFAULT_WEIGHTS = {
    "slope_mean": 0.30,
    "slope_std": 0.15,
    "tri_mean": 0.25,
    "tri_std": 0.15,
    "elevation_std": 0.15
}

def compute_metric_similarity(target_val, candidate_val, tolerance_scale=1.0):
    """
    Computes a normalized similarity [0, 1] between two scalar metrics using Gaussian decay.
    1.0 means exact match, approaching 0 as values diverge.
    """
    if tolerance_scale <= 0:
        tolerance_scale = 1.0
    diff = abs(target_val - candidate_val)
    sigma = max(abs(target_val) * 0.5, tolerance_scale)
    similarity = np.exp(-0.5 * (diff / sigma) ** 2)
    return float(similarity)

def calculate_analog_compatibility_index(target_sig, candidate_sig, weights=None, environmental_boost=0.0):
    """
    Calculates the Analog Compatibility Index (ACI) on a 0-100 scale.
    Combines topographical congruence with optional environmental priors (aridity, basalt geology).
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS
        
    scores = {}
    total_weight = 0.0
    weighted_score = 0.0
    
    for metric, weight in weights.items():
        t_val = target_sig.get(metric, 0.0)
        c_val = candidate_sig.get(metric, 0.0)
        sim = compute_metric_similarity(t_val, c_val, tolerance_scale=max(t_val * 0.3, 1.0))
        scores[metric] = sim
        weighted_score += sim * weight
        total_weight += weight
        
    base_aci = (weighted_score / total_weight) * 100.0 if total_weight > 0 else 0.0
    
    # Optional environmental bonus (e.g., hyper-arid or polar conditions)
    final_aci = min(100.0, base_aci * (1.0 + environmental_boost))
    
    return {
        "aci": round(final_aci, 2),
        "base_topographic_score": round(base_aci, 2),
        "sub_scores": {k: round(v * 100.0, 1) for k, v in scores.items()}
    }

def rank_candidates(target_sig, candidates_dict, weights=None, metadata=None):
    """
    Ranks a dictionary of candidate signatures against a target signature.
    candidates_dict: { 'site_name': candidate_sig, ... }
    metadata: optional dict with environmental attributes per site.
    """
    rankings = []
    
    for site_name, cand_sig in candidates_dict.items():
        env_boost = 0.0
        site_meta = metadata.get(site_name, {}) if metadata else {}
        
        # Environmental bonus for arid, polar, or volcanic basaltic geology
        if site_meta.get("is_hyper_arid", False):
            env_boost += 0.05
        if site_meta.get("is_basaltic", False):
            env_boost += 0.05
        if site_meta.get("has_lava_tubes", False):
            env_boost += 0.05
            
        result = calculate_analog_compatibility_index(
            target_sig, 
            cand_sig, 
            weights=weights, 
            environmental_boost=env_boost
        )
        
        rankings.append({
            "site_name": site_name,
            "aci": result["aci"],
            "base_topographic_score": result["base_topographic_score"],
            "sub_scores": result["sub_scores"],
            "metadata": site_meta
        })
        
    # Sort descending by ACI
    rankings.sort(key=lambda x: x["aci"], reverse=True)
    return rankings
