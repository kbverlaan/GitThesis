"""
Early Warning Signals (EWS) module for detecting phase transitions.

This module analyzes timeseries data from simulation runs to detect critical
transitions using various statistical indicators including variance, autocorrelation,
skewness, and Binder cumulant analysis.
"""

import numpy as np
from scipy.stats import kendalltau
from scipy.ndimage import gaussian_filter1d


def rolling_stats(timeseries, window_size=10):
    """
    Compute rolling-window statistics for EWS detection.

    Detrends the timeseries using Gaussian kernel smoothing before computing
    statistics to isolate fluctuations from the underlying trend.

    Args:
        timeseries: list/array of float values (one per round)
        window_size: int, size of the rolling window (default: 10)

    Returns:
        dict with keys:
            - 'variance': list of rolling variance values
            - 'ac1': list of lag-1 autocorrelation values
            - 'skewness': list of skewness values
            - 'rounds': list of round indices (center of each window)
    """
    timeseries = np.array(timeseries, dtype=float)
    n = len(timeseries)

    # Detrend using Gaussian kernel smoothing
    sigma = window_size / 2.0
    smoothed = gaussian_filter1d(timeseries, sigma=sigma)
    detrended = timeseries - smoothed

    variances = []
    ac1_values = []
    skewness_values = []
    rounds = []

    # Compute rolling statistics
    for i in range(window_size // 2, n - window_size // 2):
        start = i - window_size // 2
        end = start + window_size
        window = detrended[start:end]

        # Variance
        var = np.var(window, ddof=1)
        variances.append(var)

        # Lag-1 autocorrelation
        if len(window) > 1:
            mean = np.mean(window)
            numerator = np.sum((window[:-1] - mean) * (window[1:] - mean))
            denominator = np.sum((window - mean) ** 2)
            ac1 = numerator / denominator if denominator != 0 else 0.0
        else:
            ac1 = 0.0
        ac1_values.append(ac1)

        # Skewness
        mean = np.mean(window)
        std = np.std(window, ddof=1)
        if std != 0:
            skew = np.mean(((window - mean) / std) ** 3)
        else:
            skew = 0.0
        skewness_values.append(skew)

        rounds.append(i)

    return {
        'variance': variances,
        'ac1': ac1_values,
        'skewness': skewness_values,
        'rounds': rounds
    }


def kendall_tau_trend(values):
    """
    Test for a significant trend in a timeseries using Kendall's rank correlation.

    Args:
        values: list/array of float values

    Returns:
        dict with:
            - 'tau': Kendall's tau correlation coefficient
            - 'p_value': two-tailed p-value
            - 'significant': bool, True if p < 0.05 and tau > 0.4
    """
    values = np.array(values, dtype=float)
    n = len(values)

    if n < 2:
        return {'tau': 0.0, 'p_value': 1.0, 'significant': False}

    # Create time indices
    time_indices = np.arange(n)

    # Compute Kendall's tau
    tau, p_value = kendalltau(time_indices, values)

    # Handle NaN cases
    if np.isnan(tau):
        tau = 0.0
    if np.isnan(p_value):
        p_value = 1.0

    # Determine significance
    significant = (p_value < 0.05) and (tau > 0.4)

    return {
        'tau': float(tau),
        'p_value': float(p_value),
        'significant': bool(significant)
    }


def binder_cumulant(fc_values):
    """
    Compute Binder cumulant from a set of f_C values.

    The Binder cumulant is defined as:
    U = 1 - <f_C^4> / (3 * <f_C^2>^2)

    At a critical point, the Binder cumulant becomes independent of system size,
    making it useful for detecting phase transitions.

    Args:
        fc_values: list/array of f_C values from multiple runs at same condition

    Returns:
        float, the Binder cumulant value
    """
    fc_values = np.array(fc_values, dtype=float)

    # Compute moments
    fc2_mean = np.mean(fc_values ** 2)
    fc4_mean = np.mean(fc_values ** 4)

    # Handle edge case
    if fc2_mean == 0:
        return 1.0  # Return the trivial case value

    # Compute Binder cumulant
    U = 1.0 - fc4_mean / (3.0 * fc2_mean ** 2)

    return float(U)


def detect_transition(sweep_values, fc_means, fc_variances):
    """
    Identify the transition region from sweep data.

    The transition is characterized by peak variance (susceptibility analog)
    and the region is bounded by where variance exceeds 50% of peak.

    Args:
        sweep_values: list of parameter values
        fc_means: list of mean f_C per parameter value
        fc_variances: list of variance of f_C per parameter value

    Returns:
        dict with:
            - 'variance_peak_idx': index of the peak variance
            - 'variance_peak_value': the parameter value at peak variance
            - 'transition_region': tuple of (low_param, high_param) bounding the transition
            - 'max_variance': the peak variance value
    """
    sweep_values = np.array(sweep_values)
    fc_variances = np.array(fc_variances)

    # Find peak variance
    variance_peak_idx = int(np.argmax(fc_variances))
    max_variance = float(fc_variances[variance_peak_idx])
    variance_peak_value = float(sweep_values[variance_peak_idx])

    # Define transition region: where variance > 50% of peak
    threshold = 0.5 * max_variance
    in_region = fc_variances >= threshold

    # Find bounds
    region_indices = np.where(in_region)[0]
    if len(region_indices) > 0:
        low_idx = int(region_indices[0])
        high_idx = int(region_indices[-1])
        transition_region = (float(sweep_values[low_idx]), float(sweep_values[high_idx]))
    else:
        # Fallback if no region found (shouldn't happen if max_variance > 0)
        transition_region = (variance_peak_value, variance_peak_value)

    return {
        'variance_peak_idx': variance_peak_idx,
        'variance_peak_value': variance_peak_value,
        'transition_region': transition_region,
        'max_variance': max_variance
    }


def compute_ews_for_run(round_metrics, metric_key='cooperation_rate', window_size=10):
    """
    Compute EWS indicators for a single run.

    Convenience function that extracts timeseries from round metrics and computes
    both rolling statistics and trend tests.

    Args:
        round_metrics: list of dicts, each containing metrics for one round
        metric_key: str, key to extract from each round dict (default: 'cooperation_rate')
        window_size: int, window size for rolling statistics (default: 10)

    Returns:
        dict with:
            - 'rolling': dict from rolling_stats()
            - 'trends': dict with Kendall tau results for 'variance', 'ac1', 'skewness'
    """
    # Extract timeseries
    timeseries = [round_data[metric_key] for round_data in round_metrics]

    # Compute rolling statistics
    rolling = rolling_stats(timeseries, window_size=window_size)

    # Compute trends for each EWS indicator
    trends = {
        'variance': kendall_tau_trend(rolling['variance']),
        'ac1': kendall_tau_trend(rolling['ac1']),
        'skewness': kendall_tau_trend(rolling['skewness'])
    }

    return {
        'rolling': rolling,
        'trends': trends
    }


def compute_ews_across_sweep(conditions_data, metric_key='cooperation_rate'):
    """
    Compute EWS indicators across a parameter sweep.

    Analyzes multiple replications at each parameter value to detect phase
    transitions using variance analysis and Binder cumulant.

    Args:
        conditions_data: dict of {condition_value: [list of run dicts]}
                        where each run dict has a 'metrics' key with list of round metrics
        metric_key: str, metric to analyze (default: 'cooperation_rate')

    Returns:
        dict with:
            - 'sweep_values': list of condition parameter values
            - 'fc_means': list of mean final f_C per condition
            - 'fc_variances': list of variance of final f_C per condition
            - 'binder_cumulants': list of Binder cumulant per condition
            - 'transition': dict from detect_transition()
    """
    # Sort conditions
    sorted_conditions = sorted(conditions_data.keys())

    sweep_values = []
    fc_means = []
    fc_variances = []
    binder_cumulants = []

    for condition_value in sorted_conditions:
        runs = conditions_data[condition_value]

        # Extract final metric value from each run
        final_fc_values = []
        for run in runs:
            if 'metrics' in run and len(run['metrics']) > 0:
                final_value = run['metrics'][-1][metric_key]
                final_fc_values.append(final_value)

        if len(final_fc_values) > 0:
            sweep_values.append(condition_value)
            fc_means.append(np.mean(final_fc_values))
            fc_variances.append(np.var(final_fc_values, ddof=1) if len(final_fc_values) > 1 else 0.0)
            binder_cumulants.append(binder_cumulant(final_fc_values))

    # Detect transition
    transition = detect_transition(sweep_values, fc_means, fc_variances)

    return {
        'sweep_values': sweep_values,
        'fc_means': fc_means,
        'fc_variances': fc_variances,
        'binder_cumulants': binder_cumulants,
        'transition': transition
    }
