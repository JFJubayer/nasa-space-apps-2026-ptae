import os
import json
import numpy as np
import matplotlib.pyplot as plt

def plot_dem_suite(dem, slope, tri, title="Terrain Analysis", save_path=None):
    """
    Plots Elevation, Slope, and Ruggedness (TRI) side-by-side.
    """
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle(title, fontsize=15, fontweight='bold', y=0.98)
    
    # Elevation
    im0 = axes[0].imshow(dem, cmap='terrain')
    axes[0].set_title('Elevation / Topography (m)', fontsize=12)
    fig.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)
    axes[0].axis('off')
    
    # Slope
    im1 = axes[1].imshow(slope, cmap='magma', vmin=0, vmax=max(35, float(np.nanpercentile(slope, 95))))
    axes[1].set_title('Surface Slope (°)', fontsize=12)
    fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)
    axes[1].axis('off')
    
    # TRI
    im2 = axes[2].imshow(tri, cmap='inferno')
    axes[2].set_title('Terrain Ruggedness (TRI)', fontsize=12)
    fig.colorbar(im2, ax=axes[2], fraction=0.046, pad=0.04)
    axes[2].axis('off')
    
    plt.tight_layout()
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
    else:
        plt.show()

def plot_analog_leaderboard(rankings, target_name="Target", save_path=None):
    """
    Generates a horizontal bar chart ranking all candidates by Analog Compatibility Index (ACI).
    """
    names = [r["site_name"].replace("earth_", "").replace("_", " ").title() for r in rankings][::-1]
    scores = [r["aci"] for r in rankings][::-1]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(names, scores, color='#2563eb', edgecolor='#1e40af', height=0.6)
    
    # Highlight top match
    if bars:
        bars[-1].set_color('#10b981')
        bars[-1].set_edgecolor('#047857')
        
    ax.set_xlim(0, 100)
    ax.set_xlabel('Analog Compatibility Index (ACI %)', fontsize=12, fontweight='bold')
    ax.set_title(f'NASA Space Apps 2026 - Ranked Terrestrial Analogs for {target_name}', fontsize=14, fontweight='bold', pad=15)
    
    # Add data labels
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 1.5, bar.get_y() + bar.get_height()/2, f"{width:.1f}%", 
                ha='left', va='center', fontsize=11, fontweight='bold', color='#1f2937')
                
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
    else:
        plt.show()

def plot_radar_comparison(target_sig, top_candidate_sig, candidate_name="Best Analog", target_name="Target", save_path=None):
    """
    Generates a radar / spider chart comparing metrics between target and top candidate.
    """
    categories = ['Slope Mean', 'Slope Std', 'Ruggedness (TRI)', 'Roughness Max', 'Relief Variance']
    
    # Normalize values for plotting (scale relative to target)
    t_vals = [
        target_sig['slope_mean'],
        target_sig['slope_std'],
        target_sig['tri_mean'],
        target_sig['tri_max'],
        target_sig['elevation_std']
    ]
    c_vals = [
        top_candidate_sig['slope_mean'],
        top_candidate_sig['slope_std'],
        top_candidate_sig['tri_mean'],
        top_candidate_sig['tri_max'],
        top_candidate_sig['elevation_std']
    ]
    
    # Normalize each axis to max of both
    norm_t = []
    norm_c = []
    for tv, cv in zip(t_vals, c_vals):
        denom = max(tv, cv, 1e-4)
        norm_t.append(tv / denom)
        norm_c.append(cv / denom)
        
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    norm_t += norm_t[:1]
    norm_c += norm_c[:1]
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    ax.plot(angles, norm_t, color='#dc2626', linewidth=2.5, label=target_name)
    ax.fill(angles, norm_t, color='#dc2626', alpha=0.15)
    
    ax.plot(angles, norm_c, color='#10b981', linewidth=2.5, label=candidate_name)
    ax.fill(angles, norm_c, color='#10b981', alpha=0.25)
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=11, fontweight='bold')
    ax.set_ylim(0, 1.1)
    ax.set_title(f'Quantitative Signature Alignment\n{target_name} vs. {candidate_name}', 
                 fontsize=13, fontweight='bold', pad=25)
    ax.legend(loc='upper right', bbox_to_anchor=(1.25, 1.1))
    
    plt.tight_layout()
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
    else:
        plt.show()

def export_json_summary(rankings, target_name, output_path="results/summary.json"):
    """
    Exports clean JSON summary of matching results.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    payload = {
        "target": target_name,
        "challenge": "NASA Space Apps 2026: Terrestrial Analogs for Moon and Mars",
        "rankings": rankings
    }
    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)
    return output_path
