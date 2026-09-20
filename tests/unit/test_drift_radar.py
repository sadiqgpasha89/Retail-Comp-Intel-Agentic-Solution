"""Unit tests for MLOps Drift Radar (PSI, Wasserstein, Page-Hinkley)."""

import pytest
import numpy as np
from retail_intel.mlops.drift_radar import DriftRadar, PageHinkleyTest


@pytest.mark.unit
def test_psi_identical_distributions():
    radar = DriftRadar()
    base = np.array([10.0, 20.0, 30.0, 40.0, 50.0, 60.0])
    curr = np.array([10.0, 20.0, 30.0, 40.0, 50.0, 60.0])
    psi = radar.calculate_psi(base, curr)
    assert psi < 0.05  # Virtually zero drift


@pytest.mark.unit
def test_psi_shifted_distributions():
    radar = DriftRadar()
    base = np.array([10.0, 12.0, 15.0, 18.0, 20.0])
    curr = np.array([80.0, 85.0, 90.0, 95.0, 100.0])
    psi = radar.calculate_psi(base, curr)
    assert psi >= 0.25  # Severe distribution shift flagged


@pytest.mark.unit
def test_page_hinkley_drift_detection():
    ph = PageHinkleyTest(threshold=2.0)
    # Consecutive errors (1.0) should trigger drift
    drift = False
    for _ in range(10):
        if ph.update(1.0):
            drift = True
            break
    assert drift is True
