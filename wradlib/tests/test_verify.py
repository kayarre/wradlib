#!/usr/bin/env python
# Copyright (c) 2011-2025, wradlib developers.
# Distributed under the MIT License. See LICENSE.txt for more info.

from dataclasses import dataclass

import numpy as np
import pytest

from wradlib import georef, verify

from . import requires_gdal


@pytest.fixture
def pol_data():
    @dataclass(init=False, repr=False, eq=False)
    class Data:
        r = np.arange(1, 100, 10)
        az = np.arange(0, 360, 90)
        site = (9.7839, 48.5861, 0.0)
        crs = georef.epsg_to_osr(31467)
        # Coordinates of the rain gages in Gauss-Krueger 3 coordinates
        x, y = (np.array([3557880, 3557890]), np.array([5383379, 5383375]))

        np.random.seed(42)
        data = np.random.random((len(az), len(r)))

    data = Data()
    yield data
    del data


@requires_gdal
def test_PolarNeighbours__init__(pol_data):
    pn = verify.PolarNeighbours(
        pol_data.r,
        pol_data.az,
        pol_data.site,
        pol_data.crs,
        pol_data.x,
        pol_data.y,
        nnear=9,
    )
    assert isinstance(pn, verify.PolarNeighbours)


@requires_gdal
def test_extract(pol_data):
    pn = verify.PolarNeighbours(
        pol_data.r,
        pol_data.az,
        pol_data.site,
        pol_data.crs,
        pol_data.x,
        pol_data.y,
        nnear=4,
    )
    neighbours = pn.extract(pol_data.data)
    res0 = np.array([0.59241457, 0.04645041, 0.51423444, 0.19967378])
    res1 = np.array([0.04645041, 0.59241457, 0.51423444, 0.19967378])
    np.testing.assert_allclose(neighbours[0], res0)
    np.testing.assert_allclose(neighbours[1], res1)


@requires_gdal
def test_get_bincoords(pol_data):
    pn = verify.PolarNeighbours(
        pol_data.r,
        pol_data.az,
        pol_data.site,
        pol_data.crs,
        pol_data.x,
        pol_data.y,
        nnear=4,
    )
    bx, by = pn.get_bincoords()
    np.testing.assert_allclose(bx[0], 3557908.88665658, rtol=1e-6)
    np.testing.assert_allclose(by[0], 5383452.639404042, rtol=1e-6)


@requires_gdal
def test_get_bincoords_at_points(pol_data):
    pn = verify.PolarNeighbours(
        pol_data.r,
        pol_data.az,
        pol_data.site,
        pol_data.crs,
        pol_data.x,
        pol_data.y,
        nnear=4,
    )
    bx, by = pn.get_bincoords_at_points()
    resx0 = np.array(
        [3557909.62605379, 3557909.72874732, 3557909.52336013, 3557909.42066632]
    )
    resx1 = np.array(
        [3557909.72874732, 3557909.62605379, 3557909.52336013, 3557909.42066632]
    )

    resy0 = np.array(
        [5383380.64013055, 5383370.64023136, 5383390.64002972, 5383400.6399289]
    )
    resy1 = np.array(
        [5383370.64023136, 5383380.64013055, 5383390.64002972, 5383400.6399289]
    )

    np.testing.assert_allclose(bx[0], resx0, rtol=1e-6)
    np.testing.assert_allclose(bx[1], resx1, rtol=1e-6)
    np.testing.assert_allclose(by[0], resy0, rtol=1e-6)
    np.testing.assert_allclose(by[1], resy1, rtol=1e-6)


@pytest.fixture
def err_data():
    @dataclass(init=False, repr=False, eq=False)
    class Data:
        np.random.seed(42)
        obs = np.random.uniform(0, 10, 100)
        est = np.random.uniform(0, 10, 100)
        non = np.zeros(100) * np.nan

    yield Data


def test_ErrorMetrics__init__(err_data):
    err_data.metrics = verify.ErrorMetrics(err_data.obs, err_data.est)
    with pytest.raises(ValueError):
        verify.ErrorMetrics(err_data.obs, err_data.est[:10])


def test_ErrorMetrics___init__warn(err_data):
    with pytest.warns(UserWarning):
        verify.ErrorMetrics(err_data.obs, err_data.non)


def test_all_metrics(err_data):
    metrics = verify.ErrorMetrics(err_data.obs, err_data.est)
    metrics.all()


def test_pprint(err_data):
    metrics = verify.ErrorMetrics(err_data.obs, err_data.est)
    metrics.pprint()
