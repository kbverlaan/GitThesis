"""
Sweep analysis and validation.
Checks convergence, cross-replicate consistency, effect sizes, and statistical tests.
Now also computes run-level metrics (cooperation ratio, retaliation, coalition stability).

Usage:
    python src/validate_sweep.py <experiment_name>
    python src/validate_sweep.py baseline_replicability
"""

import sys
import json
import numpy as np
from pathlib import Path
from itertools import combinations

sys.path.insert(0, str(Path(__file__).parent))

from analysis.metrics import (
    gini_coefficient,
    cooperation_ratio,
    first_attack_round,
    retaliation_probability,
    coalition_stability,
)


def load_experiment_data(experiment_dir: Path) -> dict:
    """Load manifest, metrics files, and history files for an experiment."""
    manifest_path = experiment_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No manifest.json in {experiment_dir}")

    with open(manifest_path) as f:
        manifest = json.load(f)

    # Load metrics and history for each run
    runs_data = {}
    for run_info in manifest['runs']:
        run_id = run_info['run_id']
        metrics_path = experiment_dir / f"{run_id}_metrics.json"
        history_path = experiment_dir / f"{run_id}_history.json"

        if metrics_path.exists():
            with open(metrics_path) as f:
                metrics = json.load(f)

            # Load history if available
            history = None
            if history_path.exists():
                with open(history_path) as f:
                    history_data = json.load(f)
                    history = history_data.get('history', [])

            runs_data[run_id] = {
                'metrics': metrics,
                'history': history,
                'condition_value': run_info['condition_value'],
                'rep': run_info['rep'],
            }
        else:
            print(f"  WARNING: Missing metrics file for {run_id}")

    return manifest, runs_data


def group_by_condition(manifest: dict, runs_data: dict) -> dict:
    """Group runs by sweep condition value."""
    conditions = {}
    for run_info in manifest['runs']:
        val = run_info['condition_value']
        run_id = run_info['run_id']
        # For dict condition values (factorial), use a string key
        key = json.dumps(val, sort_keys=True) if isinstance(val, dict) else val
        if run_id in runs_data:
            conditions.setdefault(key, []).append(runs_data[run_id])
    return conditions


# --- A. Convergence Check ---

def check_convergence(runs: list, gini_threshold: float = 0.05,
                      stability_threshold: float = 0.10) -> dict:
    """
    Compare metrics in first half vs second half of rounds.
    Converged = difference < threshold.
    """
    results = []

    for run in runs:
        metrics = run['metrics']
        n_rounds = len(metrics)
        if n_rounds < 4:
            results.append({'converged_gini': False, 'converged_stability': False,
                            'reason': 'too_few_rounds'})
            continue

        mid = n_rounds // 2
        first_half = metrics[:mid]
        second_half = metrics[mid:]

        # Gini convergence
        gini_first = np.mean([m['gini'] for m in first_half])
        gini_second = np.mean([m['gini'] for m in second_half])
        gini_diff = abs(gini_second - gini_first)
        gini_converged = gini_diff < gini_threshold

        # Action stability convergence
        stab_first = [m['action_stability'] for m in first_half
                      if m['action_stability'] is not None]
        stab_second = [m['action_stability'] for m in second_half
                       if m['action_stability'] is not None]

        if stab_first and stab_second:
            stab_mean_first = np.mean(stab_first)
            stab_mean_second = np.mean(stab_second)
            stab_diff = abs(stab_mean_second - stab_mean_first)
            stab_converged = stab_diff < stability_threshold
        else:
            stab_diff = None
            stab_converged = False

        results.append({
            'gini_first_half': float(gini_first),
            'gini_second_half': float(gini_second),
            'gini_diff': float(gini_diff),
            'converged_gini': bool(gini_converged),
            'stability_first_half': float(np.mean(stab_first)) if stab_first else None,
            'stability_second_half': float(np.mean(stab_second)) if stab_second else None,
            'stability_diff': float(stab_diff) if stab_diff is not None else None,
            'converged_stability': bool(stab_converged),
        })

    # Overall: converged if majority of reps converged
    n_gini_converged = sum(1 for r in results if r['converged_gini'])
    n_stab_converged = sum(1 for r in results if r['converged_stability'])
    n = len(results)

    return {
        'per_rep': results,
        'gini_converged_count': n_gini_converged,
        'stability_converged_count': n_stab_converged,
        'total_reps': n,
        'verdict': 'CONVERGED' if n_gini_converged > n / 2 else 'NOT_CONVERGED',
    }


# --- B. Cross-replicate Consistency ---

def check_consistency(runs: list, cv_threshold: float = 0.50) -> dict:
    """
    Check standard deviation of final metrics across replicates.
    Flag if coefficient of variation > threshold.
    """
    final_ginis = []
    final_action_dists = []

    for run in runs:
        metrics = run['metrics']
        if metrics:
            final_ginis.append(metrics[-1]['gini'])
            final_action_dists.append(metrics[-1]['action_distribution'])

    if len(final_ginis) < 2:
        return {
            'final_gini_mean': float(final_ginis[0]) if final_ginis else None,
            'final_gini_std': None,
            'cv': None,
            'consistent': True,
            'note': 'only_one_rep',
        }

    gini_mean = float(np.mean(final_ginis))
    gini_std = float(np.std(final_ginis))
    cv = gini_std / gini_mean if gini_mean > 0 else 0.0

    # Action distribution consistency
    all_actions = set()
    for dist in final_action_dists:
        all_actions.update(dist.keys())

    action_cvs = {}
    for action in all_actions:
        counts = [dist.get(action, 0) for dist in final_action_dists]
        mean_count = np.mean(counts)
        std_count = np.std(counts)
        action_cvs[action] = {
            'mean': float(mean_count),
            'std': float(std_count),
            'cv': float(std_count / mean_count) if mean_count > 0 else 0.0,
        }

    return {
        'final_gini_mean': gini_mean,
        'final_gini_std': gini_std,
        'cv': float(cv),
        'consistent': cv < cv_threshold,
        'action_distributions': action_cvs,
        'individual_ginis': [float(g) for g in final_ginis],
    }


# --- Run-level Metrics ---

def compute_run_level_metrics(runs: list) -> dict:
    """
    Compute run-level metrics from history files for a set of runs.
    Returns summary statistics across replicates.
    """
    coop_ratios = []
    first_attacks = []
    retaliation_probs = []
    coalition_stabs = []

    for run in runs:
        history = run.get('history')
        if history is None:
            continue

        coop_ratios.append(cooperation_ratio(history))
        fa = first_attack_round(history)
        if fa is not None:
            first_attacks.append(fa)
        retaliation_probs.append(retaliation_probability(history))
        coalition_stabs.append(coalition_stability(history))

    result = {}

    if coop_ratios:
        result['cooperation_ratio'] = {
            'mean': float(np.mean(coop_ratios)),
            'std': float(np.std(coop_ratios)),
            'values': [float(v) for v in coop_ratios],
        }

    if first_attacks:
        result['first_attack_round'] = {
            'mean': float(np.mean(first_attacks)),
            'min': int(min(first_attacks)),
            'max': int(max(first_attacks)),
            'n_runs_with_attack': len(first_attacks),
            'n_runs_total': len(runs),
        }
    else:
        result['first_attack_round'] = {
            'n_runs_with_attack': 0,
            'n_runs_total': len(runs),
        }

    if retaliation_probs:
        result['retaliation_probability'] = {
            'mean': float(np.mean(retaliation_probs)),
            'std': float(np.std(retaliation_probs)),
        }

    if coalition_stabs:
        result['coalition_stability'] = {
            'mean': float(np.mean(coalition_stabs)),
            'std': float(np.std(coalition_stabs)),
        }

    return result


# --- C. Effect Sizes ---

def cohens_d(group1: list, group2: list) -> float:
    """Compute Cohen's d between two groups."""
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return float('nan')

    mean1, mean2 = np.mean(group1), np.mean(group2)
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)

    # Pooled standard deviation
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))

    if pooled_std == 0:
        return 0.0

    return float((mean1 - mean2) / pooled_std)


def compute_effect_sizes(conditions: dict) -> dict:
    """
    Compute effect sizes between all condition pairs.
    Uses Cohen's d on final Gini values.
    """
    condition_ginis = {}
    for val, runs in conditions.items():
        ginis = [run['metrics'][-1]['gini'] for run in runs if run['metrics']]
        condition_ginis[val] = ginis

    if len(condition_ginis) < 2:
        return {'pairwise': {}, 'has_effect': False, 'note': 'single_condition'}

    pairwise = {}
    for (v1, g1), (v2, g2) in combinations(condition_ginis.items(), 2):
        key = f"{v1}_vs_{v2}"
        d = cohens_d(g1, g2)
        pairwise[key] = {
            'cohens_d': d,
            'magnitude': _effect_magnitude(abs(d)) if not np.isnan(d) else 'undefined',
            'mean_1': float(np.mean(g1)),
            'mean_2': float(np.mean(g2)),
        }

    # Any large effect?
    has_effect = any(
        abs(p['cohens_d']) > 0.5
        for p in pairwise.values()
        if not np.isnan(p['cohens_d'])
    )

    return {
        'pairwise': pairwise,
        'has_effect': has_effect,
    }


def _effect_magnitude(d: float) -> str:
    if d < 0.2:
        return 'negligible'
    elif d < 0.5:
        return 'small'
    elif d < 0.8:
        return 'medium'
    else:
        return 'large'


# --- D. Statistical Tests ---

def mann_whitney_u(x: list, y: list) -> tuple:
    """
    Manual Mann-Whitney U test (no scipy dependency).
    Returns (U statistic, approximate p-value, rank-biserial correlation).
    """
    n1, n2 = len(x), len(y)
    if n1 == 0 or n2 == 0:
        return float('nan'), float('nan'), float('nan')

    # Combine and rank
    combined = [(val, 'x') for val in x] + [(val, 'y') for val in y]
    combined.sort(key=lambda t: t[0])

    # Assign ranks (handle ties with average rank)
    ranks = {}
    i = 0
    while i < len(combined):
        j = i
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1
        avg_rank = (i + j + 1) / 2  # 1-indexed average
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j

    # Sum ranks for group x
    r1 = sum(ranks[i] for i, (_, group) in enumerate(combined) if group == 'x')

    U1 = r1 - n1 * (n1 + 1) / 2
    U2 = n1 * n2 - U1
    U = min(U1, U2)

    # Normal approximation for p-value
    mu = n1 * n2 / 2
    sigma = np.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)

    if sigma == 0:
        return float(U), 1.0, 0.0

    z = (U - mu) / sigma
    # Two-tailed p-value using normal CDF approximation
    p = 2 * _normal_cdf(-abs(z))

    # Rank-biserial correlation
    rbc = 1 - (2 * U) / (n1 * n2)

    return float(U), float(p), float(rbc)


def _normal_cdf(z: float) -> float:
    """Approximate standard normal CDF using error function approximation."""
    return 0.5 * (1 + np.sign(z) * np.sqrt(1 - np.exp(-2 * z * z / np.pi)))


def run_statistical_tests(conditions: dict) -> dict:
    """
    Mann-Whitney U between all condition pairs with Bonferroni correction.
    """
    condition_ginis = {}
    for val, runs in conditions.items():
        ginis = [run['metrics'][-1]['gini'] for run in runs if run['metrics']]
        condition_ginis[val] = ginis

    if len(condition_ginis) < 2:
        return {'pairwise': {}, 'note': 'single_condition'}

    pairs = list(combinations(condition_ginis.items(), 2))
    n_comparisons = len(pairs)

    pairwise = {}
    for (v1, g1), (v2, g2) in pairs:
        key = f"{v1}_vs_{v2}"
        U, p, rbc = mann_whitney_u(g1, g2)

        # Bonferroni correction
        p_corrected = min(p * n_comparisons, 1.0) if not np.isnan(p) else float('nan')

        pairwise[key] = {
            'U': U,
            'p_value': p,
            'p_corrected': p_corrected,
            'rank_biserial': rbc,
            'significant_005': p_corrected < 0.05 if not np.isnan(p_corrected) else False,
            'n1': len(g1),
            'n2': len(g2),
        }

    return {
        'pairwise': pairwise,
        'n_comparisons': n_comparisons,
        'correction': 'bonferroni',
    }


# --- Plotting ---

def generate_plots(conditions: dict, manifest: dict, output_dir: Path):
    """Generate diagnostic plots. Gracefully skips if matplotlib unavailable."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not available, skipping plots")
        return

    figures_dir = output_dir / "figures"
    figures_dir.mkdir(exist_ok=True)

    sweep_param = manifest['sweep_param']
    sorted_values = sorted(conditions.keys(), key=lambda x: float(x) if isinstance(x, (int, float)) else str(x))

    # --- Plot 1: Gini trajectories per condition ---
    fig, ax = plt.subplots(figsize=(10, 6))
    for val in sorted_values:
        runs = conditions[val]
        # Collect gini trajectories
        trajectories = []
        for run in runs:
            ginis = [m['gini'] for m in run['metrics']]
            trajectories.append(ginis)

        if not trajectories:
            continue

        # Pad to same length
        max_len = max(len(t) for t in trajectories)
        padded = [t + [t[-1]] * (max_len - len(t)) for t in trajectories]
        arr = np.array(padded)

        rounds = np.arange(1, max_len + 1)
        mean = arr.mean(axis=0)
        std = arr.std(axis=0)

        label = f"{sweep_param}={val}" if not isinstance(val, str) or len(val) < 30 else val[:30]
        ax.plot(rounds, mean, label=label, linewidth=2)
        ax.fill_between(rounds, mean - std, mean + std, alpha=0.2)

    ax.set_xlabel('Round')
    ax.set_ylabel('Gini Coefficient')
    ax.set_title(f'Gini Trajectories by {sweep_param}')
    ax.legend(fontsize='small')
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(figures_dir / "gini_trajectories.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: {figures_dir / 'gini_trajectories.png'}")

    # --- Plot 2: Action distribution bars per condition ---
    fig, ax = plt.subplots(figsize=(10, 6))

    all_actions = set()
    condition_action_totals = {}
    for val in sorted_values:
        totals = {}
        for run in conditions[val]:
            for m in run['metrics']:
                for action, count in m['action_distribution'].items():
                    totals[action] = totals.get(action, 0) + count
                    all_actions.add(action)
        condition_action_totals[val] = totals

    all_actions = sorted(all_actions)
    x = np.arange(len(sorted_values))
    width = 0.8 / max(len(all_actions), 1)

    for i, action in enumerate(all_actions):
        counts = []
        for val in sorted_values:
            total = sum(condition_action_totals[val].values())
            action_count = condition_action_totals[val].get(action, 0)
            counts.append(action_count / total * 100 if total > 0 else 0)
        ax.bar(x + i * width, counts, width, label=action)

    ax.set_xlabel(sweep_param)
    ax.set_ylabel('Action Share (%)')
    ax.set_title(f'Action Distribution by {sweep_param}')
    ax.set_xticks(x + width * len(all_actions) / 2)
    ax.set_xticklabels([str(v)[:15] for v in sorted_values], rotation=45, ha='right')
    ax.legend(fontsize='small')
    ax.grid(True, alpha=0.3, axis='y')
    fig.tight_layout()
    fig.savefig(figures_dir / "action_distribution.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: {figures_dir / 'action_distribution.png'}")

    # --- Plot 3: Convergence diagnostic ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Left: per-round Gini for all runs
    for val in sorted_values:
        for run in conditions[val]:
            ginis = [m['gini'] for m in run['metrics']]
            rounds = range(1, len(ginis) + 1)
            axes[0].plot(rounds, ginis, alpha=0.4, linewidth=1,
                         label=f"{val}" if run == conditions[val][0] else None)

    axes[0].set_xlabel('Round')
    axes[0].set_ylabel('Gini')
    axes[0].set_title('Per-run Gini (all replicates)')
    axes[0].legend(title=sweep_param, fontsize='small')
    axes[0].grid(True, alpha=0.3)

    # Right: per-round stability for all runs
    for val in sorted_values:
        for run in conditions[val]:
            stabs = [m['action_stability'] for m in run['metrics']
                     if m['action_stability'] is not None]
            if stabs:
                rounds = range(2, len(stabs) + 2)
                axes[1].plot(rounds, stabs, alpha=0.4, linewidth=1,
                             label=f"{val}" if run == conditions[val][0] else None)

    axes[1].set_xlabel('Round')
    axes[1].set_ylabel('Action Stability')
    axes[1].set_title('Per-run Action Stability')
    axes[1].legend(title=sweep_param, fontsize='small')
    axes[1].grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(figures_dir / "convergence_diagnostic.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: {figures_dir / 'convergence_diagnostic.png'}")

    # --- Plot 4: Cooperation ratio per condition ---
    has_history = any(
        run.get('history') is not None
        for runs in conditions.values()
        for run in runs
    )
    if has_history:
        fig, ax = plt.subplots(figsize=(10, 6))

        coop_data = []
        labels = []
        for val in sorted_values:
            ratios = []
            for run in conditions[val]:
                if run.get('history') is not None:
                    ratios.append(cooperation_ratio(run['history']))
            if ratios:
                coop_data.append(ratios)
                labels.append(str(val)[:15])

        if coop_data:
            ax.boxplot(coop_data, labels=labels)
            ax.set_xlabel(sweep_param)
            ax.set_ylabel('Cooperation Ratio')
            ax.set_title(f'Cooperation Ratio by {sweep_param}')
            ax.grid(True, alpha=0.3, axis='y')
            if len(labels) > 5:
                ax.tick_params(axis='x', rotation=45)
            fig.tight_layout()
            fig.savefig(figures_dir / "cooperation_ratio.png", dpi=150)
            print(f"  Saved: {figures_dir / 'cooperation_ratio.png'}")

        plt.close(fig)


# --- Main Report ---

def validate_experiment(experiment_name: str):
    """Run all validation checks on an experiment."""
    project_root = Path(__file__).parent.parent
    experiment_dir = project_root / "data" / "runs" / experiment_name

    if not experiment_dir.exists():
        print(f"ERROR: Experiment directory not found: {experiment_dir}")
        sys.exit(1)

    print(f"\n{'='*70}")
    print(f"VALIDATION REPORT: {experiment_name}")
    print(f"{'='*70}\n")

    manifest, runs_data = load_experiment_data(experiment_dir)
    conditions = group_by_condition(manifest, runs_data)

    sweep_param = manifest['sweep_param']
    sorted_values = sorted(conditions.keys(), key=lambda x: float(x) if isinstance(x, (int, float)) else str(x))

    report = {
        'experiment': experiment_name,
        'sweep_param': sweep_param,
        'conditions': {},
    }

    # --- Per-condition analyses ---
    header = (f"{'Condition':<25} {'Conv':<10} {'Gini (mean±std)':<20} "
              f"{'CV':<8} {'Cons':<6} {'CoopR':<8} {'1stAtk':<8}")
    print(header)
    print("-" * len(header))

    for val in sorted_values:
        runs = conditions[val]
        label = f"{sweep_param}={val}" if len(str(val)) < 20 else str(val)[:22]

        convergence = check_convergence(runs)
        consistency = check_consistency(runs)
        run_metrics = compute_run_level_metrics(runs)

        gini_str = f"{consistency['final_gini_mean']:.3f}" if consistency['final_gini_mean'] is not None else "n/a"
        if consistency['final_gini_std'] is not None:
            gini_str += f"±{consistency['final_gini_std']:.3f}"

        cv_str = f"{consistency['cv']:.2f}" if consistency['cv'] is not None else "n/a"
        cons_str = "PASS" if consistency['consistent'] else "FAIL"

        # Run-level metric strings
        coop_str = "n/a"
        if 'cooperation_ratio' in run_metrics:
            coop_str = f"{run_metrics['cooperation_ratio']['mean']:.3f}"

        atk_str = "n/a"
        if 'first_attack_round' in run_metrics:
            fa = run_metrics['first_attack_round']
            if fa['n_runs_with_attack'] > 0:
                atk_str = f"{fa['mean']:.1f}"
            else:
                atk_str = "none"

        print(f"{label:<25} {convergence['verdict']:<10} {gini_str:<20} "
              f"{cv_str:<8} {cons_str:<6} {coop_str:<8} {atk_str:<8}")

        report['conditions'][str(val)] = {
            'convergence': convergence,
            'consistency': consistency,
            'run_level_metrics': run_metrics,
        }

    # --- Cross-condition analyses ---
    if len(conditions) > 1:
        print(f"\n--- Effect Sizes (Cohen's d on final Gini) ---")
        effect_sizes = compute_effect_sizes(conditions)
        report['effect_sizes'] = effect_sizes

        for pair, result in effect_sizes['pairwise'].items():
            d = result['cohens_d']
            mag = result['magnitude']
            d_str = f"{d:.3f}" if not np.isnan(d) else "n/a"
            print(f"  {pair}: d={d_str} ({mag}), "
                  f"means={result['mean_1']:.3f} vs {result['mean_2']:.3f}")

        print(f"\n  Parameter has detectable effect: {'YES' if effect_sizes['has_effect'] else 'NO'}")

        print(f"\n--- Statistical Tests (Mann-Whitney U, Bonferroni corrected) ---")
        stat_tests = run_statistical_tests(conditions)
        report['statistical_tests'] = stat_tests

        for pair, result in stat_tests['pairwise'].items():
            sig = "*" if result['significant_005'] else ""
            p_str = f"{result['p_corrected']:.4f}" if not np.isnan(result['p_corrected']) else "n/a"
            print(f"  {pair}: U={result['U']:.1f}, "
                  f"p={p_str}{sig}, "
                  f"r={result['rank_biserial']:.3f}")

        sig_count = sum(1 for r in stat_tests['pairwise'].values() if r['significant_005'])
        print(f"\n  Significant comparisons: {sig_count}/{stat_tests['n_comparisons']} (p<0.05, corrected)")
    else:
        report['effect_sizes'] = {'note': 'single_condition'}
        report['statistical_tests'] = {'note': 'single_condition'}

    # --- Save report ---
    report_path = experiment_dir / "validation_report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport saved to {report_path}")

    # --- Generate plots ---
    print("\nGenerating plots...")
    generate_plots(conditions, manifest, experiment_dir)

    print(f"\n{'='*70}")
    print(f"VALIDATION COMPLETE: {experiment_name}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python src/validate_sweep.py <experiment_name>")
        print("Example: python src/validate_sweep.py baseline_replicability")
        sys.exit(1)

    validate_experiment(sys.argv[1])
