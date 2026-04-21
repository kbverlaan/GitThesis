"""
Statistical analysis module for experiment results.

This module provides statistical tests for factorial experimental designs
comparing agent architectures and prompt framings.
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.integrate import quad
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.regression.mixed_linear_model import MixedLM
from itertools import combinations, chain
from typing import Dict, List, Any, Tuple


def two_way_anova(
    data: List[Dict[str, Any]],
    factor1_col: str,
    factor2_col: str,
    value_col: str
) -> Dict[str, Any]:
    """
    Perform two-way ANOVA with interaction.

    Args:
        data: List of dicts, each dict is one observation with keys for factors and value
        factor1_col: Name of first factor column
        factor2_col: Name of second factor column
        value_col: Name of dependent variable column

    Returns:
        Dict with F-statistics, p-values, degrees of freedom, sum of squares,
        partial eta squared for each factor and interaction, and model R²
    """
    df = pd.DataFrame(data)

    # Fit the model with interaction
    formula = f'{value_col} ~ C({factor1_col}) * C({factor2_col})'
    model = smf.ols(formula, data=df).fit()
    anova_table = sm.stats.anova_lm(model, typ=2)

    # Extract results
    results = {}
    ss_residual = anova_table.loc['Residual', 'sum_sq']

    for effect in [f'C({factor1_col})', f'C({factor2_col})',
                   f'C({factor1_col}):C({factor2_col})']:
        if effect in anova_table.index:
            row = anova_table.loc[effect]
            ss_effect = row['sum_sq']

            # Compute partial eta squared
            partial_eta_sq = ss_effect / (ss_effect + ss_residual)

            # Clean effect name for output
            clean_name = effect.replace('C(', '').replace(')', '').replace(':', '_x_')

            results[clean_name] = {
                'F': float(row['F']),
                'p_value': float(row['PR(>F)']),
                'df': int(row['df']),
                'sum_sq': float(ss_effect),
                'partial_eta_sq': float(partial_eta_sq)
            }

    results['model_r_squared'] = float(model.rsquared)

    return results


def compute_icc(
    data: List[Dict[str, Any]],
    group_col: str,
    value_col: str
) -> Dict[str, float]:
    """
    Compute Intraclass Correlation Coefficient (ICC1).

    ICC(1) measures the proportion of variance at the group level.

    Args:
        data: List of dicts with group and value columns
        group_col: Name of grouping variable column
        value_col: Name of value column

    Returns:
        Dict with ICC, MSB (between-group mean square),
        MSW (within-group mean square), and k (average group size)
    """
    df = pd.DataFrame(data)

    # Group statistics
    group_means = df.groupby(group_col)[value_col].mean()
    group_sizes = df.groupby(group_col)[value_col].count()
    grand_mean = df[value_col].mean()

    # Between-group sum of squares
    ss_between = sum(group_sizes * (group_means - grand_mean) ** 2)

    # Within-group sum of squares
    ss_within = sum(
        df.groupby(group_col)[value_col].apply(
            lambda x: sum((x - x.mean()) ** 2)
        )
    )

    # Degrees of freedom
    n_groups = len(group_means)
    n_total = len(df)
    df_between = n_groups - 1
    df_within = n_total - n_groups

    # Mean squares
    msb = ss_between / df_between
    msw = ss_within / df_within

    # Average group size
    k = n_total / n_groups

    # ICC(1) formula
    icc = (msb - msw) / (msb + (k - 1) * msw)

    return {
        'icc': float(icc),
        'msb': float(msb),
        'msw': float(msw),
        'k': float(k)
    }


def bayes_factor_ttest(
    group1: List[float],
    group2: List[float],
    r: float = 0.707
) -> Dict[str, Any]:
    """
    Compute Bayes factor for independent samples t-test using JZS prior.

    Uses the Rouder et al. (2009) approach with Cauchy prior on effect size.

    Args:
        group1: First group of values
        group2: Second group of values
        r: Scale parameter for Cauchy prior (default sqrt(2)/2)

    Returns:
        Dict with BF10 (evidence for H1), BF01 (evidence for H0),
        and interpretation string
    """
    n1 = len(group1)
    n2 = len(group2)

    # Compute t-statistic
    t_stat, _ = stats.ttest_ind(group1, group2)
    df = n1 + n2 - 2

    # Effective sample size
    neff = (n1 * n2) / (n1 + n2)

    # Integral for BF calculation
    def integrand(g):
        term1 = (1 + neff * g) ** (-0.5)
        term2 = (1 + (t_stat ** 2) / ((1 + neff * g) * df)) ** (-(df + 1) / 2)
        term3 = (2 * np.pi) ** (-0.5) * g ** (-1.5) * np.exp(-1 / (2 * g * r ** 2))
        return term1 * term2 * term3

    # Numerical integration
    integral, _ = quad(integrand, 0, np.inf)

    # Null hypothesis term
    null_term = (1 + t_stat ** 2 / df) ** (-(df + 1) / 2)

    # Bayes factor
    bf10 = integral / null_term
    bf01 = 1 / bf10

    # Interpretation based on Jeffreys scale
    if bf10 < 1/3:
        interpretation = "moderate evidence for H0"
    elif bf10 < 1:
        interpretation = "anecdotal evidence for H0"
    elif bf10 < 3:
        interpretation = "anecdotal evidence for H1"
    elif bf10 < 10:
        interpretation = "moderate evidence for H1"
    elif bf10 < 30:
        interpretation = "strong evidence for H1"
    elif bf10 < 100:
        interpretation = "very strong evidence for H1"
    else:
        interpretation = "decisive evidence for H1"

    return {
        'bf10': float(bf10),
        'bf01': float(bf01),
        'interpretation': interpretation
    }


def dominance_analysis(
    data: List[Dict[str, Any]],
    factor_cols: List[str],
    value_col: str
) -> Dict[str, Dict[str, Any]]:
    """
    Perform dominance analysis to decompose R² across predictors.

    Computes general dominance (average marginal R² contribution) for each factor.

    Args:
        data: List of dicts with factor and value columns
        factor_cols: List of predictor column names
        value_col: Name of dependent variable column

    Returns:
        Dict with per factor: general_dominance (average R² contribution) and rank
    """
    df = pd.DataFrame(data)
    n_factors = len(factor_cols)

    # Store R² for all possible models
    model_r2 = {}

    # Generate all subsets of factors (excluding empty set)
    def powerset(iterable):
        s = list(iterable)
        return chain.from_iterable(combinations(s, r) for r in range(1, len(s) + 1))

    # Fit models for all subsets
    for subset in powerset(factor_cols):
        formula = f"{value_col} ~ " + " + ".join([f"C({col})" for col in subset])
        model = smf.ols(formula, data=df).fit()
        model_r2[subset] = model.rsquared

    # Compute general dominance for each factor
    dominance = {}

    for factor in factor_cols:
        marginal_contributions = []

        # For each subset size k (0 to n-1)
        for k in range(n_factors):
            # Get all subsets of size k that don't include the factor
            other_factors = [f for f in factor_cols if f != factor]

            if k <= len(other_factors):
                for subset in combinations(other_factors, k):
                    subset_tuple = tuple(sorted(subset))
                    subset_with_factor = tuple(sorted(subset + (factor,)))

                    # Marginal contribution = R² with factor - R² without factor
                    r2_without = model_r2.get(subset_tuple, 0.0) if subset_tuple else 0.0
                    r2_with = model_r2[subset_with_factor]

                    marginal_contributions.append(r2_with - r2_without)

        # General dominance is the average marginal contribution
        dominance[factor] = np.mean(marginal_contributions)

    # Rank factors by dominance
    ranked = sorted(dominance.items(), key=lambda x: x[1], reverse=True)

    results = {}
    for rank, (factor, dom_value) in enumerate(ranked, 1):
        results[factor] = {
            'general_dominance': float(dom_value),
            'rank': rank
        }

    return results


def mixed_effects_model(
    data: List[Dict[str, Any]],
    formula: str,
    random_formula: str = '1|run_id'
) -> Dict[str, Any]:
    """
    Fit a linear mixed-effects model.

    Args:
        data: List of dicts with observations
        formula: Fixed effects formula (e.g., "cooperation_ratio ~ C(model) * C(framing)")
        random_formula: Random effects specification (default "1|run_id")

    Returns:
        Dict with fixed effects estimates, random effects variance, ICC,
        AIC, BIC, number of observations, and number of groups
    """
    df = pd.DataFrame(data)

    # Parse random effects formula to extract grouping variable
    if '|' in random_formula:
        groups_col = random_formula.split('|')[1].strip()
    else:
        raise ValueError("Random formula must contain '|' to specify grouping variable")

    # Parse fixed effects formula
    parts = formula.split('~')
    if len(parts) != 2:
        raise ValueError("Formula must be in format: 'outcome ~ predictors'")

    outcome = parts[0].strip()
    predictors = parts[1].strip()

    # Create design matrix for fixed effects
    fixed_formula = f"{outcome} ~ {predictors}"

    # Fit mixed effects model
    model = smf.mixedlm(fixed_formula, df, groups=df[groups_col])
    result = model.fit(reml=True)

    # Extract fixed effects
    fixed_effects = {}
    for name, coef in result.fe_params.items():
        fixed_effects[name] = {
            'estimate': float(coef),
            'std_error': float(result.bse[name]),
            'z_value': float(result.tvalues[name]),
            'p_value': float(result.pvalues[name])
        }

    # Random effects variance
    random_variance = float(result.cov_re.iloc[0, 0])
    residual_variance = float(result.scale)

    # ICC from mixed model
    icc = random_variance / (random_variance + residual_variance)

    # Number of groups
    n_groups = df[groups_col].nunique()

    return {
        'fixed_effects': fixed_effects,
        'random_effects_variance': random_variance,
        'residual_variance': residual_variance,
        'icc': float(icc),
        'aic': float(result.aic),
        'bic': float(result.bic),
        'n_observations': int(result.nobs),
        'n_groups': n_groups
    }


def pairwise_comparisons(
    data: List[Dict[str, Any]],
    group_col: str,
    value_col: str,
    method: str = 'bonferroni'
) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """
    Perform all pairwise comparisons between groups with multiple testing correction.

    Args:
        data: List of dicts with group and value columns
        group_col: Name of grouping variable column
        value_col: Name of value column
        method: Correction method ('bonferroni' or 'holm')

    Returns:
        Dict mapping (group1, group2) tuples to comparison results including
        Cohen's d, p-value, corrected p-value, BF10, and significance flag
    """
    df = pd.DataFrame(data)
    groups = df[group_col].unique()

    results = {}
    p_values = []
    pairs = []

    # Compute all pairwise comparisons
    for group1, group2 in combinations(sorted(groups), 2):
        data1 = df[df[group_col] == group1][value_col].values
        data2 = df[df[group_col] == group2][value_col].values

        # Cohen's d
        pooled_std = np.sqrt(
            ((len(data1) - 1) * np.var(data1, ddof=1) +
             (len(data2) - 1) * np.var(data2, ddof=1)) /
            (len(data1) + len(data2) - 2)
        )
        cohens_d = (np.mean(data1) - np.mean(data2)) / pooled_std

        # T-test
        _, p_value = stats.ttest_ind(data1, data2)

        # Bayes factor
        bf_result = bayes_factor_ttest(list(data1), list(data2))

        pairs.append((group1, group2))
        p_values.append(p_value)

        results[(group1, group2)] = {
            'cohens_d': float(cohens_d),
            'p_value': float(p_value),
            'bf10': bf_result['bf10'],
            'mean_diff': float(np.mean(data1) - np.mean(data2))
        }

    # Apply multiple testing correction
    p_values = np.array(p_values)
    n_comparisons = len(p_values)

    if method == 'bonferroni':
        p_corrected = np.minimum(p_values * n_comparisons, 1.0)
    elif method == 'holm':
        # Holm-Bonferroni method
        sorted_indices = np.argsort(p_values)
        p_corrected = np.zeros(n_comparisons)

        for i, idx in enumerate(sorted_indices):
            p_corrected[idx] = min(p_values[idx] * (n_comparisons - i), 1.0)
            if i > 0:
                p_corrected[idx] = max(p_corrected[idx],
                                      p_corrected[sorted_indices[i-1]])
    else:
        raise ValueError(f"Unknown correction method: {method}")

    # Add corrected p-values and significance flags
    for i, pair in enumerate(pairs):
        results[pair]['p_corrected'] = float(p_corrected[i])
        results[pair]['significant'] = p_corrected[i] < 0.05

    return results


def power_analysis(
    pilot_data: List[Dict[str, Any]],
    group_col: str,
    value_col: str,
    target_power: float = 0.80,
    alpha: float = 0.05
) -> Dict[str, Any]:
    """
    Perform simulation-based power analysis.

    Estimates required sample size to achieve target power based on pilot data.

    Args:
        pilot_data: List of dicts with pilot observations
        group_col: Name of grouping variable column
        value_col: Name of value column
        target_power: Target statistical power (default 0.80)
        alpha: Significance level (default 0.05)

    Returns:
        Dict with effect size estimate, recommended sample size,
        and power curve (sample size -> achieved power)
    """
    df = pd.DataFrame(pilot_data)
    groups = df[group_col].unique()

    if len(groups) != 2:
        raise ValueError("Power analysis currently supports only two groups")

    group1_data = df[df[group_col] == groups[0]][value_col].values
    group2_data = df[df[group_col] == groups[1]][value_col].values

    # Estimate effect size (Cohen's d)
    pooled_std = np.sqrt(
        ((len(group1_data) - 1) * np.var(group1_data, ddof=1) +
         (len(group2_data) - 1) * np.var(group2_data, ddof=1)) /
        (len(group1_data) + len(group2_data) - 2)
    )
    effect_size = abs(np.mean(group1_data) - np.mean(group2_data)) / pooled_std

    # Sample sizes to test
    sample_sizes = [5, 10, 15, 20, 30, 50]
    power_curve = {}

    n_simulations = 1000

    for n in sample_sizes:
        significant_count = 0

        for _ in range(n_simulations):
            # Bootstrap samples
            sample1 = np.random.choice(group1_data, size=n, replace=True)
            sample2 = np.random.choice(group2_data, size=n, replace=True)

            # T-test
            _, p_value = stats.ttest_ind(sample1, sample2)

            if p_value < alpha:
                significant_count += 1

        power = significant_count / n_simulations
        power_curve[n] = power

    # Find recommended sample size
    recommended_n = None
    for n in sorted(sample_sizes):
        if power_curve[n] >= target_power:
            recommended_n = n
            break

    if recommended_n is None:
        recommended_n = f">50 (max tested: {max(sample_sizes)})"

    return {
        'effect_size_estimate': float(effect_size),
        'pooled_std': float(pooled_std),
        'recommended_n': recommended_n,
        'power_curve': {int(k): float(v) for k, v in power_curve.items()},
        'target_power': target_power,
        'alpha': alpha
    }
