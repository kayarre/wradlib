#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) 2011-2023, wradlib developers.
# Distributed under the MIT License. See LICENSE.txt for more info.

"""
Utility functions
^^^^^^^^^^^^^^^^^

Module util provides a set of useful helpers which are currently not
attributable to the other modules

.. autosummary::
   :nosignatures:
   :toctree: generated/

   {}
"""
__all__ = [
    "from_to",
    "filter_window_polar",
    "filter_window_cartesian",
    "find_bbox_indices",
    "get_raster_origin",
    "calculate_polynomial",
    "derivate",
    "despeckle",
    "import_optional",
    "cross_section_ppi",
    "UtilMethods",
]
__doc__ = __doc__.format("\n   ".join(__all__))

import contextlib
import datetime as dt
import importlib
import inspect
import os
import warnings
from functools import singledispatch

import numpy as np
import xarray as xr
from scipy import ndimage, signal
from scipy.spatial import KDTree

from wradlib import georef, version


class OptionalModuleStub:
    """Stub class for optional imports.

    Objects of this class are instantiated when optional modules are not
    present on the user's machine.
    This allows global imports of optional modules with the code only breaking
    when actual attributes from this module are called.
    """

    def __init__(self, name, dep=None):
        self.name = name
        self.dep = "optional"

    def __getattr__(self, name):
        link = (
            "https://docs.wradlib.org/en/stable/"
            f"installation.html#{self.dep}-dependencies"
        )
        raise AttributeError(
            f"Module '{self.name}' is not installed.\n\n"
            "You tried to access function/module/attribute "
            f"'{name}'\nfrom module '{self.name}'.\nThis module is "
            "optional right now in wradlib.\nYou need to "
            "separately install this dependency.\n"
            f"Please refer to {link}\nfor further instructions."
        )


def import_optional(module, dep=None):
    """Allowing for lazy loading of optional wradlib modules or dependencies.

    This function removes the need to satisfy all dependencies of wradlib
    before being able to work with it.

    Parameters
    ----------
    module : str
             name of the module

    Returns
    -------
    mod : object
          if module is present, returns the module object, on ImportError
          returns an instance of `OptionalModuleStub` which will raise an
          AttributeError as soon as any attribute is accessed.

    Examples
    --------
    Trying to import a module that exists makes the module available as normal.
    You can even use an alias. You cannot use the '*' notation, or import only
    select functions, but you can simulate most of the standard import syntax
    behavior.
    >>> m = import_optional('math')
    >>> m.log10(100)
    2.0

    Trying to import a module that does not exist, does not produce
    any errors. Only when some function is used, the code triggers an error
    >>> m = import_optional('nonexistentmodule')  # noqa
    >>> m.log10(100)  #doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    AttributeError: Module 'nonexistentmodule' is not installed.
    <BLANKLINE>
    You tried to access function/module/attribute 'log10'
    from module 'nonexistentmodule'.
    This module is optional right now in wradlib.
    You need to separately install this dependency.
    Please refer to https://docs.wradlib.org/en/stable/installation.html#optional-dependencies
    for further instructions.
    """
    try:
        mod = importlib.import_module(module)
    except ImportError:
        mod = OptionalModuleStub(module, dep=dep)

    return mod


def warn(message, category=None, stacklevel=3):
    """Emit user level warning"""
    warnings.warn(message, category, stacklevel=stacklevel)


def _shape_to_size(shape):
    """
    Compute the size which corresponds to a shape
    """
    out = 1
    for item in shape:
        out *= item
    return out


def from_to(tstart, tend, tdelta):
    """Return a list of timesteps from <tstart> to <tend> of length <tdelta>

    Parameters
    ----------
    tstart : str or :py:class:`datetime.datetime`
        datetime isostring (%Y%m%d %H:%M:%S), e.g. 2000-01-01 15:34:12 or datetime object
    tend : str or :py:class:`datetime.datetime`
        datetime isostring (%Y%m%d %H:%M:%S), e.g. 2000-01-01 15:34:12 or datetime object
    tdelta : int
        representing time interval in SECONDS

    Returns
    -------
    output : list
        list of datetime.datetime objects

    """
    if not isinstance(tstart, dt.datetime):
        tstart = dt.datetime.strptime(tstart, "%Y-%m-%d %H:%M:%S")
    if not isinstance(tend, dt.datetime):
        tend = dt.datetime.strptime(tend, "%Y-%m-%d %H:%M:%S")
    tdelta = dt.timedelta(seconds=tdelta)
    tsteps = [
        tstart,
    ]
    tmptime = tstart
    while True:
        tmptime = tmptime + tdelta
        if tmptime > tend:
            break
        else:
            tsteps.append(tmptime)
    return tsteps


def _idvalid(data, *, isinvalid=None, minval=None, maxval=None):
    """Identifies valid entries in an array and returns the corresponding
    indices

    Invalid values are NaN and Inf. Other invalid values can be passed using
    the isinvalid keyword argument.

    Parameters
    ----------
    data : :class:`numpy:numpy.ndarray`
    isinvalid : list
        list of what is considered an invalid value

    """
    if isinvalid is None:
        isinvalid = [-99.0, 99, -9999.0, -9999]
    ix = np.ma.masked_invalid(data).mask
    for el in isinvalid:
        ix = np.logical_or(ix, np.ma.masked_where(data == el, data).mask)
    if minval is not None:
        ix = np.logical_or(ix, np.ma.masked_less(data, minval).mask)
    if maxval is not None:
        ix = np.logical_or(ix, np.ma.masked_greater(data, maxval).mask)

    return np.where(np.logical_not(ix))[0]


def meshgrid_n(*arrs):
    """N-dimensional meshgrid

    Just pass sequences of coordinates arrays

    """
    arrs = tuple(arrs)
    lens = list(map(len, arrs))
    dim = len(arrs)

    sz = 1
    for s in lens:
        sz *= s

    ans = []
    for i, arr in enumerate(arrs):
        slc = [1] * dim
        slc[i] = lens[i]
        arr2 = np.asarray(arr).reshape(slc)
        for j, sz in enumerate(lens):
            if j != i:
                arr2 = arr2.repeat(sz, axis=j)
        ans.append(arr2)
    return tuple(ans)


def gridaspoints(*arrs):
    """Creates an N-dimensional grid form arrs and returns grid points sequence
    of point coordinate pairs
    """
    # there is a small gotcha here.
    # with the convention following the 2013-08-30 sprint in Potsdam it was
    # agreed upon that arrays should have shapes (...,z,y,x) similar to the
    # convention that polar data should be (...,time,scan,azimuth,range)
    #
    # Still coordinate tuples are given in the order (x,y,z) [and hopefully not
    # more dimensions]. Therefore, np.meshgrid must be fed the axis coordinates
    # in shape order (z,y,x) and the result needs to be reversed in order
    # for everything to work out.
    grid = tuple([dim.ravel() for dim in reversed(np.meshgrid(*arrs, indexing="ij"))])
    return np.vstack(grid).transpose()


def issequence(x):
    """Test whether x is a sequence of numbers

    Parameters
    ----------
    x : sequence
        sequence to test

    """
    out = True
    try:
        # can we get a length on the object
        len(x)
    except TypeError:
        return False
    # is the object not a string?
    out = np.all(np.isreal(x))
    return out


def trapezoid(data, x1, x2, x3, x4):
    """
    Applied the trapezoidal function described in :cite:`Vulpiani`
    to determine the degree of membership in the non-meteorological
    target class.

    Parameters
    ----------
    data : :class:`numpy:numpy.ndarray`
        Array containing the data
    x1 : float
        x-value of the first vertex of the trapezoid
    x2 : float
        x-value of the second vertex of the trapezoid
    x3 : float
        x-value of the third vertex of the trapezoid
    x4 : float
        x-value of the fourth vertex of the trapezoid

    Returns
    -------
    d : :class:`numpy:numpy.ndarray`
        Array of values describing degree of membership in
        nonmeteorological target class.

    """

    d = np.ones(np.shape(data))
    d[np.logical_or(data <= x1, data >= x4)] = 0
    d[np.logical_and(data >= x2, data <= x3)] = 1
    d[np.logical_and(data > x1, data < x2)] = (
        data[np.logical_and(data > x1, data < x2)] - x1
    ) / float(x2 - x1)
    d[np.logical_and(data > x3, data < x4)] = (
        x4 - data[np.logical_and(data > x3, data < x4)]
    ) / float(x4 - x3)

    d[np.isnan(data)] = np.nan

    return d


def filter_window_polar(img, wsize, fun, rscale, *, random=False):
    """Apply a filter of an approximated square window of half size `fsize` \
    on a given polar image `img`.

    Parameters
    ----------
    img : :class:`numpy:numpy.ndarray`
        2d array of values to which the filter is to be applied
    wsize : float
        Half size of the window centred on the pixel [m]
    fun : str
        name of the 1d filter from :mod:`scipy:scipy.ndimage`
    rscale : float
        range [m] scale of the polar grid
    random: bool
        True to use random azimuthal size to avoid long-term biases.

    Returns
    -------
    output : :class:`numpy:numpy.ndarray`
        Array with the same shape as `img`, containing the filter's results.

    """
    ascale = 2 * np.pi / img.shape[0]
    data_filtered = np.empty(img.shape, dtype=img.dtype)
    fun = getattr(ndimage, f"{fun}_filter1d")
    nbins = img.shape[-1]
    ranges = np.arange(nbins) * rscale + rscale / 2
    asize = ranges * ascale
    if random:
        na = prob_round(wsize / asize).astype(int)
    else:
        na = np.fix(wsize / asize + 0.5).astype(int)
    # Maximum of adjacent azimuths (higher close to the origin) to
    # increase performance
    na[na > 20] = 20
    sr = np.fix(wsize / rscale + 0.5).astype(int)
    for sa in np.unique(na):
        imax = np.where(na >= sa)[0][-1] + 1
        imin = np.where(na <= sa)[0][0]
        if sa == 0:
            data_filtered[:, imin:imax] = img[:, imin:imax]
        imin2 = max(imin - sr, 0)
        imax2 = min(imax + sr, nbins)
        temp = img[:, imin2:imax2]
        temp = fun(temp, size=2 * sa + 1, mode="wrap", axis=0)
        temp = fun(temp, size=2 * sr + 1, axis=1)
        imin3 = imin - imin2
        imax3 = imin3 + imax - imin
        data_filtered[:, imin:imax] = temp[:, imin3:imax3]
    return data_filtered


def prob_round(x, *, prec=0):
    """Round the float number `x` to the lower or higher integer randomly
    following a binomial distribution

    Parameters
    ----------
    x : float
    prec : int
        precision
    """
    fixup = np.sign(x) * 10**prec
    x *= fixup
    intx = x.astype(int)
    round_func = intx + np.random.binomial(1, x - intx)
    return round_func / fixup


def filter_window_cartesian(img, wsize, fun, scale, **kwargs):
    """Apply a filter of square window size `fsize` on a given \
    cartesian image `img`.

    Parameters
    ----------
    img : :class:`numpy:numpy.ndarray`
        2d array of values to which the filter is to be applied
    wsize : float
        Half size of the window centred on the pixel [m]
    fun : str
        name of the 2d filter from :mod:`scipy:scipy.ndimage`
    scale : tuple
        tuple of 2 floats
        x and y scale of the cartesian grid [m]

    Returns
    -------
    output : :class:`numpy:numpy.ndarray`
        Array with the same shape as `img`, containing the filter's results.

    """
    fun = getattr(ndimage, f"{fun}_filter")
    size = np.fix(wsize / scale + 0.5).astype(int)
    data_filtered = fun(img, size, **kwargs)
    return data_filtered


def roll2d_polar(img, shift=1, axis=0):
    """Roll a 2D polar array [azimuth,range] by a given `shift` for \
    the given `axis`

    Parameters
    ----------
    img : :class:`numpy:numpy.ndarray`
        2d data array
    shift : int
        shift to apply to the array
    axis : int
        axis which will be shifted
    Returns
    -------
    out: :class:`numpy:numpy.ndarray`
        new array with shifted values
    """
    if shift == 0:
        return img
    else:
        out = np.empty(img.shape)
    n = img.shape[axis]
    if axis == 0:
        if shift > 0:
            out[shift:, :] = img[:-shift, :]
            out[:shift, :] = img[n - shift :, :]
        else:
            out[:shift, :] = img[-shift:, :]
            out[n + shift :, :] = img[:-shift:, :]
    else:
        if shift > 0:
            out[:, shift:] = img[:, :-shift]
            out[:, :shift] = np.nan
        else:
            out[:, :shift] = img[:, -shift:]
            out[:, n + shift :] = np.nan
    return out


class UTC(dt.tzinfo):
    """UTC implementation for tzinfo.

    Replaces pytz.utc
    """

    def __repr__(self):
        return "<UTC>"

    def utcoffset(self, dtime):
        return dt.timedelta(0)

    def tzname(self, dtime):
        return "UTC"

    def dst(self, dtime):
        return dt.timedelta(0)


def half_power_radius(r, bwhalf):
    """
    Half-power radius.

    ported from PyRadarMet

    Battan (1973),

    Parameters
    ----------
    r : float | :class:`numpy:numpy.ndarray`
        Range from radar [m]
    bwhalf : float
        Half-power beam width [degrees]

    Returns
    -------
    Rhalf : float | :class:`numpy:numpy.ndarray`
        Half-power radius [m]

    Examples
    --------
    rhalf = half_power_radius(r,bwhalf)
    """

    rhalf = (r * np.deg2rad(bwhalf)) / 2.0

    return rhalf


def get_raster_origin(coords):
    """Return raster origin

    Parameters
    ----------
    coords : :class:`numpy:numpy.ndarray`
        3-dimensional array (rows, cols, 2) of xy-coordinates

    Returns
    -------
    out : str
        'lower' or 'upper'

    """
    return "lower" if (coords[1, 1] - coords[0, 0])[1] > 0 else "upper"


def find_bbox_indices(coords, bbox):
    """Find min/max-indices for NxMx2 array coords using bbox-values.

    The bounding box is defined by two points (llx,lly and urx,ury)
    It finds the first indices before llx,lly and the first indices
    after urx,ury. If no index is found 0 and N/M is returned.

    Parameters
    ----------
    coords : :class:`numpy:numpy.ndarray`
        3-dimensional array (ny, nx, lon/lat) of floats
    bbox : :class:`numpy:numpy.ndarray` | list | tuple
         4-element (llx,lly,urx,ury)

    Returns
    -------
    bbind : tuple
        4-element tuple of int (llx,lly,urx,ury)
    """

    # sort arrays
    x_sort = np.argsort(coords[0, :, 0])
    y_sort = np.argsort(coords[:, 0, 1])

    # find indices in sorted arrays
    llx = np.searchsorted(coords[0, :, 0], bbox[0], side="left", sorter=x_sort)
    urx = np.searchsorted(coords[0, :, 0], bbox[2], side="right", sorter=x_sort)
    lly = np.searchsorted(coords[:, 0, 1], bbox[1], side="left", sorter=y_sort)
    ury = np.searchsorted(coords[:, 0, 1], bbox[3], side="right", sorter=y_sort)

    # get indices in original array
    if llx < len(x_sort):
        llx = x_sort[llx]
    if urx < len(x_sort):
        urx = x_sort[urx]
    if lly < len(y_sort):
        lly = y_sort[lly]
    if ury < len(y_sort):
        ury = y_sort[ury]

    # check at boundaries
    if llx:
        llx -= 1
    if get_raster_origin(coords) == "lower":
        if lly:
            lly -= 1
    else:
        if lly < coords.shape[0]:
            lly += 1

    bbind = (llx, min(lly, ury), urx, max(lly, ury))

    return bbind


def has_geos():
    gdal = import_optional("osgeo.gdal")
    ogr = import_optional("osgeo.ogr")
    pnt1 = ogr.CreateGeometryFromWkt("POINT(10 20)")
    pnt2 = ogr.CreateGeometryFromWkt("POINT(30 20)")
    ogrex = ogr.GetUseExceptions()
    gdalex = gdal.GetUseExceptions()
    gdal.DontUseExceptions()
    ogr.DontUseExceptions()
    hasgeos = pnt1.Union(pnt2) is not None
    if ogrex:
        ogr.UseExceptions()
    if gdalex:
        gdal.UseExceptions()
    return hasgeos


def _get_wradlib_data_path():
    wradlib_data = import_optional("wradlib_data", dep="development")
    has_pooch_data = has_import(wradlib_data)
    wrl_data_path = os.environ.get("WRADLIB_DATA", None)
    if wrl_data_path is None:
        if not has_pooch_data:
            raise OSError(
                "`WRADLIB_DATA` environment variable not set.\n"
                "Please set `WRADLIB_DATA` environment variable pointing to a writable "
                "folder on the filesystem."
            )
        else:
            wrl_data_path = wradlib_data.DATASETS.abspath
    if not os.path.isdir(wrl_data_path):
        raise OSError(f"`WRADLIB_DATA` path {wrl_data_path!r} does not exist.")
    return wrl_data_path


def get_wradlib_data_path():
    warn(
        "Function get_wradlib_data_path is not part of public API,\n"
        "it's use is deprecated and it will be removed in a future version.\n"
        "Please see wradlib-data package for more information.",
        DeprecationWarning,
    )
    return _get_wradlib_data_path()


def _get_wradlib_data_file(relfile):
    wradlib_data = import_optional("wradlib_data", dep="development")
    return wradlib_data.DATASETS.fetch(relfile)


def get_wradlib_data_file(relfile):
    warn(
        "Function get_wradlib_data_file is not part of public API,\n"
        "it's use is deprecated and it will be removed in a future version.\n"
        "Please see wradlib-data package for more information.",
        DeprecationWarning,
    )
    return _get_wradlib_data_file(relfile)


def calculate_polynomial(data, w):
    """Calculate Polynomial

    The function calculate the following polynomial:

    .. math::

       P = \\sum_{n=0}^{N} w(n) \\cdot data^{n}

    Parameters
    ----------
    data : :class:`numpy:numpy.ndarray`
        Flat array of data values.
    w : :class:`numpy:numpy.ndarray`
        Array of shape (N) containing weights.

    Returns
    -------
    poly : :class:`numpy:numpy.ndarray`
        Flat array of processed data.
    """
    poly = np.zeros_like(data)
    for i, c in enumerate(w):
        poly += c * data**i
    return poly


def medfilt_along_axis(x, n, *, axis=-1):
    """Applies median filter smoothing on one axis of an N-dimensional array."""
    kernel_size = np.array(x.shape)
    kernel_size[:] = 1
    kernel_size[axis] = n
    return signal.medfilt(x, kernel_size)


def gradient_along_axis(x, *, axis=-1):
    """Computes gradient along last axis of an N-dimensional array"""
    newshape = np.array(x.shape)
    newshape[axis] = 1
    diff_begin = (x[..., 1] - x[..., 0]).reshape(newshape)
    diff_end = (x[..., -1] - x[..., -2]).reshape(newshape)
    diffs = (x - np.roll(x, 2, axis)) / 2.0
    diffs = np.append(diffs[..., 2:], diff_end, axis=axis)
    return np.insert(diffs, [0], diff_begin, axis=axis)


def gradient_from_smoothed(x, *, n=5, axis=-1):
    """Computes gradient of smoothed data along final axis of an array"""
    return gradient_along_axis(medfilt_along_axis(x, n=5, axis=axis)).astype("f4")


def center_to_edge(centers):
    delta = centers[1] - centers[0]
    edges = np.insert(centers + delta / 2, 0, centers[0] - delta / 2)

    return edges


def _pad_array(data, pad, *, mode="reflect", **kwargs):
    """Returns array with padding added along last dimension."""
    pad_width = [(0,)] * (data.ndim - 1) + [(pad,)]
    if mode in ["maximum", "mean", "median", "minimum"]:
        kwargs["stat_length"] = kwargs.pop("stat_length", pad)
    data = np.pad(data, pad_width, mode=mode, **kwargs)
    return data


def _rolling_dim(data, window):
    """Return array with rolling dimension of window-length added at the end."""
    shape = data.shape[:-1] + (data.shape[-1] - window + 1, window)
    strides = data.strides + (data.strides[-1],)
    return np.lib.stride_tricks.as_strided(data, shape=shape, strides=strides)


def _linregress_1d(rhs, *, method="lstsq"):
    """Calculates slope by means of linear regression on last dimension of rhs.

    Calculates lhs from size of last dimension of rhs.
    Methods 'lstsq', 'cov', 'matrix_inv' and 'cov_nan' are multidimensional.
    The other two nan-methods only work on a single system. Hence, the
    apply_along_axis.
    """
    shape = rhs.shape

    rhs = rhs.reshape((-1, rhs.shape[-1]))

    if "cov" in method:
        lhs = np.arange(rhs.shape[-1])
        if "nan" in method:
            idx = np.argsort(rhs, axis=-1)
            rhs = np.sort(rhs, axis=-1)
            lhs = lhs[idx]

            # special treatment for wradlib, use fast method by slicing NaN's
            if "iter" in method:
                nan = np.argmax(np.isnan(rhs), axis=-1)
                unique = np.unique(nan)
                if len(unique) == 1:
                    rhs = rhs[..., : unique[0]]
                    lhs = lhs[..., : unique[0]]
                    method = "cov"
        else:
            lhs = np.broadcast_to(lhs, (rhs.shape))
        lhs = lhs.T
    else:
        lhs = np.vander(np.arange(shape[-1], dtype=rhs.dtype), 2)

    rhs = rhs.T

    if method == "lstsq":
        out = np.linalg.lstsq(lhs, rhs, rcond=None)[0][0]
    elif method == "lstsq_nan":
        out = np.apply_along_axis(_nan_lstsq, 0, rhs, lhs)
    elif method == "cov":
        out = _cov(lhs, rhs)
    elif "cov_nan" in method:
        out = _nan_cov(lhs, rhs)
    elif method == "matrix_inv":
        out = _matrix_inv(lhs, rhs)
    elif method == "matrix_inv_nan":
        out = np.apply_along_axis(_nan_matrix_inv, 0, rhs, lhs)
    else:
        raise ValueError(f"Unknown method {method!r}.")

    return out.reshape(shape[:-1])


def _nan_lstsq(y, x):
    """Calculate slope by lstsq considering NaN."""
    mask = np.isnan(y)
    out, _, _, _ = np.linalg.lstsq(x[~mask, :], y[~mask], rcond=None)
    return out[0]


def _nan_matrix_inv(y, x):
    """Calculate slope by matrix inversion considering NaN."""
    mask = np.isnan(y)
    x = x[~mask]
    out = np.dot(np.linalg.inv(np.dot(x.T, x)), np.dot(x.T, y[~mask]))
    return out[0]


def _matrix_inv(x, y):
    """Calculate slope by matrix inversion considering NaN."""
    out = np.dot(np.linalg.inv(np.dot(x.T, x)), np.dot(x.T, y))
    return out[0]


def _nan_cov(x, y):
    """Calculate slope using covariances considering NaN."""
    y = np.ma.masked_invalid(y)
    x = np.ma.masked_array(x, mask=np.ma.getmask(y))

    # calculate covariances
    cov = np.ma.sum((x - x.mean(axis=0)) * (y - y.mean(axis=0)), axis=0) / y.count(
        axis=0
    )
    # calculate slope
    out = cov / (x.std(axis=0) ** 2)
    return out


def _cov(x, y):
    """Calculate slope using covariances."""
    # calculate covariances
    cov = np.sum((x - x.mean(axis=0)) * (y - y.mean(axis=0)), axis=0) / y.shape[0]
    # calculate slope
    out = cov / (x.std(axis=0) ** 2)
    return out


def _lanczos_differentiator(winlen):
    """Returns Lanczos Differentiator."""
    m = (winlen - 1) / 2
    denom = m * (m + 1.0) * (2 * m + 1.0)
    k = np.arange(1, m + 1)
    f = 3 * k / denom
    return np.r_[f[::-1], [0], -f]


@singledispatch
def derivate(data, *, winlen=7, method="lanczos_conv", skipna=False, **kwargs):
    """Calculates derivative of data using window of length winlen.

    In normal operation the method ('lanczos_conv') uses convolution
    to estimate the derivative using Low-noise Lanczos differentiators.
    The equivalent method ('lanczos_dot') uses dot-vector sum product.

    For further reading please see `Differentiation by integration using \
    orthogonal polynomials, a survey <https://arxiv.org/pdf/1102.5219>`_ \
    and `Low-noise Lanczos differentiators \
    <http://www.holoborodko.com/pavel/numerical-methods/numerical-derivative/\
lanczos-low-noise-differentiators/>`_.

    The results are very similar to the moving window linear
    regression methods (`cov`, `matrix_inv` and `lstsq`), which are slower than
    the former (in order of appearance).

    All methods will return NaNs in case at least one value in the moving
    window is NaN.

    If `skipna=True` the locations of NaN results are treated by using local
    linear regression by method2 (default to `cov_nan`) where enough valid
    neighbouring data is available.

    Before applying the actual derivation calculation the data is padded with
    `mode='reflect'` by default along the derivation dimension. Padding can be
    parametrized using kwargs.

    Parameters
    ----------
    data : :class:`numpy:numpy.ndarray`
        multidimensional array, note that the derivation dimension must be the
        last dimension of the input array.
    winlen : int
        Width of the derivation window .
    method : str
        Defaults to 'lanczos_conv'. Can take one of 'lanczos_dot', 'lstsq',
        'cov', 'cov_nan', 'matrix_inv'.
    skipna : bool
        Defaults to False. If True, treat NaN results by applying method2.

    Keyword Arguments
    -----------------
    method2 : str
        Defaults to '_nan' methods.
    min_periods : int
        Minimum number of valid values in moving window for linear regression.
        Defaults to winlen // 2 + 1.
    pad_mode : str
        Defaults to `reflect`. See :func:`numpy:numpy.pad`.
    pad_kwargs : dict
        Keyword arguments for padding, see :func:`numpy:numpy.pad`

    Returns
    -------
    out : :class:`numpy:numpy.ndarray`
        array of derivates with the same shape as data
    """
    if (winlen % 2) != 1:
        raise ValueError(f"`winlen` must be an odd number, but {winlen} given.")
    # Make really sure winlen is an integer
    winlen = int(winlen)

    shape = data.shape
    data = data.reshape((-1, shape[-1]))

    # pad data using pad_mode on derivation dimension
    pad = winlen // 2
    pad_kwargs = kwargs.pop("pad_kwargs", {})
    pad_kwargs["mode"] = kwargs.pop("pad_mode", "reflect")
    data_pad = _pad_array(data, pad, **pad_kwargs)
    data_roll = None

    # calculate derivative
    if method == "lanczos_conv":
        # we use constant nan padding here,
        # more sophisticated padding was already done
        out = ndimage.convolve1d(
            data_pad, _lanczos_differentiator(winlen), axis=-1, mode="constant"
        )
        # strip padding for convolution method
        out = out[..., pad:-pad]
    elif method == "finite_difference_vulpiani":
        out = (data_pad[..., winlen - 1 :] - data_pad[..., : shape[-1]]) / winlen
    else:
        data_roll = _rolling_dim(data_pad, winlen)
        if method == "lanczos_dot":
            out = np.dot(data_roll, _lanczos_differentiator(winlen) * -1)
        elif method in ["lstsq", "cov", "cov_nan", "matrix_inv"]:
            out = _linregress_1d(data_roll, method=method)
        else:
            raise ValueError(f"Unknown method {method!r}")

    # NaN treatment
    if skipna:
        # find remaining NaN values with valid neighbours
        invalid = np.isnan(out)
        if np.any(invalid):
            min_periods = kwargs.pop("min_periods", winlen // 2 + 1)
            if min_periods < 2:
                raise ValueError("`min_periods` need to be >= 2.")
            # automatically select method2 if not given
            if method in ["lstsq", "matrix_inv"]:
                m2 = method + "_nan"
            else:
                m2 = "cov_nan"
            method2 = kwargs.pop("method2", m2)

            # bring data into needed shape
            data_roll = (
                _rolling_dim(data_pad, winlen) if data_roll is None else data_roll
            )
            data_roll = data_roll.reshape((-1, data_roll.shape[-1]))

            # internal speed up by iterating over same NaN counts and using
            # faster calculation method
            # ToDo: this doesn't seem to speed up anything, rechecking needed
            if method2 == "cov_nan_iter":
                for n in range(min_periods, winlen):
                    valid = np.count_nonzero(~np.isnan(data_roll), axis=-1) == n
                    recalc = valid & invalid.reshape(-1)
                    if np.any(recalc):
                        out.flat[recalc] = _linregress_1d(
                            data_roll[recalc], method=method2
                        )
            else:
                valid = np.count_nonzero(~np.isnan(data_roll), axis=-1) >= min_periods
                recalc = valid & invalid.reshape(-1)
                # and interpolate using _linregress_1d -> method2
                if np.any(recalc):
                    out.flat[recalc] = _linregress_1d(data_roll[recalc], method=method2)

    return out.reshape(shape)


@derivate.register(xr.DataArray)
def _derivate_xarray(obj, **kwargs):
    """Calculates derivative of data using window of length winlen.

    In normal operation the method ('lanczos_conv') uses convolution
    to estimate the derivative using Low-noise Lanczos differentiators.
    The equivalent method ('lanczos_dot') uses dot-vector sum product.

    For further reading please see `Differentiation by integration using \
    orthogonal polynomials, a survey <https://arxiv.org/pdf/1102.5219>`_ \
    and `Low-noise Lanczos differentiators \
    <http://www.holoborodko.com/pavel/numerical-methods/numerical-derivative/\
lanczos-low-noise-differentiators/>`_.

    The results are very similar to the moving window linear
    regression methods (`cov`, `matrix_inv` and `lstsq`), which are slower than
    the former (in order of appearance).

    All methods will return NaNs in case at least one value in the moving
    window is NaN.

    If `skipna=True` the locations of NaN results are treated by using local
    linear regression by method2 (default to `cov_nan`) where enough valid
    neighbouring data is available.

    Before applying the actual derivation calculation the data is padded with
    `mode='reflect'` by default along the derivation dimension. Padding can be
    parametrized using kwargs.

    Parameters
    ----------
    obj : :py:class:`xarray:xarray.DataArray`
        input array

    Keyword Arguments
    -----------------
    winlen : int
        Width of the derivation window .
    method : str
        Defaults to 'lanczos_conv'. Can take one of 'lanczos_dot', 'lstsq',
        'cov', 'cov_nan', 'matrix_inv'.
    skipna : bool
        Defaults to False. If True, treat NaN results by applying method2.
    method2 : str
        Defaults to '_nan' methods.
    min_periods : int
        Minimum number of valid values in moving window for linear regression.
        Defaults to winlen // 2 + 1.
    pad_mode : str
        Defaults to `reflect`. See :func:`numpy:numpy.pad`.
    pad_kwargs : dict
        Keyword arguments for padding, see :func:`numpy:numpy.pad`

    Returns
    -------
    out : :py:class:`xarray:xarray.DataArray`
        array of derivates
    """
    dim0 = obj.wrl.util.dim0()
    out = xr.apply_ufunc(
        derivate,
        obj,
        input_core_dims=[[dim0, "range"]],
        output_core_dims=[[dim0, "range"]],
        dask="parallelized",
        dask_gufunc_kwargs=dict(allow_rechunk=True),
    )
    out.attrs = obj.attrs
    return out


@singledispatch
def despeckle(data, *, n=3, copy=False):
    """Remove floating pixels in between NaNs in a multidimensional array.

    Warning
    -------
    This function changes the original input array if argument copy is set to
    False (default).

    Parameters
    ----------
    data : :class:`numpy:numpy.ndarray`
        Note that the range dimension must be the last dimension of the
        input array.
    n : int
        (must be either 3 or 5, 3 by default),
        Width of the window in which we check for speckle
    copy : bool
        If True, the input array will remain unchanged.

    """
    if n not in (3, 5):
        raise ValueError("Window size n for function despeckle must be 3 or 5.")
    if copy:
        data = data.copy()

    pad = n // 2

    # pad with NaN
    data0 = _pad_array(data, pad, mode="constant")
    # append n count last dimension
    data0 = _rolling_dim(data0, data.shape[-1])
    # count NaN's and find speckle
    nans = np.count_nonzero(np.isnan(data0), axis=-2) == (n - 1)
    # set speckle to NaN
    data[nans] = np.nan

    return data


@despeckle.register(xr.DataArray)
def _despeckle_xarray(obj, **kwargs):
    """Remove floating pixels in between NaNs in a multidimensional array.

    Parameters
    ----------
    obj : :py:class:`xarray:xarray.DataArray`
        input array

    Keyword Arguments
    -----------------
    n : int
        (must be either 3 or 5, 3 by default),
        Width of the window in which we check for speckle

    Returns
    -------
    out : :py:class:`xarray:xarray.DataArray`
        output array
    """
    dim0 = obj.wrl.util.dim0()
    out = xr.apply_ufunc(
        despeckle,
        obj,
        input_core_dims=[[dim0, "range"]],
        output_core_dims=[[dim0, "range"]],
        kwargs=kwargs,
        dask="parallelized",
        dask_gufunc_kwargs=dict(allow_rechunk=True),
    )
    out.attrs = obj.attrs
    return out


def show_versions(file=None):
    import sys

    import xarray as xr

    if file is None:
        file = sys.stdout
    xr.show_versions(file)
    print("", file=file)
    print(f"wradlib: {version.version}")


@contextlib.contextmanager
def _open_file(name):
    # Check if string has been passed
    if isinstance(name, str):
        with open(name, "rb") as fid:
            yield fid
    else:
        # otherwise assume file-like object and pass
        yield name


def has_import(module):
    return not isinstance(module, OptionalModuleStub)


def cross_section_ppi(
    obj,
    azimuth,
    **kwargs,
):
    """Cut a cross-section from PPI volume scans

        .. versionadded:: 1.18

    This function extracts cross-sections from a PPI volume scan along one or more azimuth angles,
    or along a line connecting two given points.
    Similar to PyArt's cross_section_ppi function.

    Parameters
    ----------
    obj : :py:class:`xarray:xarray.Dataset` - Dataset containing PPI sweeps
        from which azimuthal cross-sections will be extracted.
    azimuth : int, float, slice, tuple or list
        Value of azimuth to extract the cross-section. It can be multiple values
        in the form of a slice, or a tuple or list of values.
        Alternatively, it can be given a tuple or list containing coordinates of two
        arbitrary points in the x,y space of the georeferenced object: [ (x1, y1), (x2,y2) ].
        In case two points are given, a cross-section along the line connecting
        the points will be generated by selecting the nearest-neighbor values of data.
        No interpolation of data is performed. If more than two points are given, only
        the first two are used. The resulting dataset has dimensions xyi (which is just
        an index along the line connecting the points) and elevation, and
        coordinates xy (distance along the line from p1) and z. The xy and z coordinates
        should be used for plotting.

    Keyword Arguments
    -----------------
    method : {None, "nearest", "pad", "ffill", "backfill", "bfill"}, optional
        Method for inexact matches for selecting azimuth values, from :py:class:`xarray:xarray.Dataset.sel`.
        Defaults to None (only exact matches).
    tolerance : float, optional
        Maximum distance between original and new labels for inexact matches
        from :py:class:`xarray:xarray.Dataset.sel`.
    bw : float, optional
        Beam width in degrees (defaults to None).
        Option meant for plotting beams with their true beamwidth instead of filling the
        empty space by stretching the beams (because of how matplotlib pcolormesh works).
        Defaults to None, which returns a Dataset of cross-sections in the specified azimuth(s).
        If set to a certain beamwidth, it will return the same Dataset with additional
        "fake" empty beams (extra elevations) so that when plotting with matplotlib pcolormesh
        the beamwidths are correctly represented according to their width.
    crs : :py:class:`gdal:osgeo.osr.SpatialReference`, :py:class:`cartopy.crs.CRS`, optional
        Projection to use with :py:class:`wradlib.georef.xarray.georeference`.
        If GDAL OSR SRS, output is in this projection, defaults to AEQD.
    npl : int, optional
        Number of points to make up the line between p1 and p2, in case the user gives two arbitrary points
        instead of an azimuth value. npl should be high enough to accomodate more points along the line that
        points of data available (i.e., higher that the resolution of the data). The default value 1000
        should be enough for most cases, but in case the result looks low resolution try increasing npl.

    Returns
    ----------
    obj : :py:class:`xarray:xarray.Dataset` or :py:class:`xarray:xarray.DataArray`
        Dataset of cross-section(s) in the specified azimuth(s) or along the line
        connecting the given points.
    """
    bw = kwargs.get("bw", None)
    npl = kwargs.get("npl", 1000)
    crs = kwargs.get("crs", "None")
    method = kwargs.get("method", None)
    tolerance = kwargs.get("tolerance", None)

    if bw is not None:
        # Matplotlib's pcolormesh fills the grid by coloring around each of the gridpoints
        # up until halfway to the nearest gridpoints.
        # Then, we need to create fake rays of nan and/or duplicated data so the filling
        # only extends the shading to cover the beamwidth and no more.

        # Sort array of elevation angles
        sorted_elevs = np.sort(obj.sweep_fixed_angle.data)

        # Calculate midpoints between elevation angles
        sorted_elevs_midpoints = (sorted_elevs[1:] + sorted_elevs[:-1]) / 2

        # Identify spaces in between beams > bw
        spaces = sorted_elevs[1:] - sorted_elevs[:-1]
        separation_needed = spaces > bw

        # Beams separated by exactly 2*bw need only a nan ray at the midpoint
        two_bw = np.delete(
            sorted_elevs_midpoints, ~(separation_needed * spaces == (2 * bw))
        )

        # Beams separated by more than 2*bw need two fake nan rays in between
        over_two_bw = np.concatenate(
            (
                np.delete(
                    sorted_elevs[:-1] + bw, ~(separation_needed * spaces > (2 * bw))
                ),
                np.delete(
                    sorted_elevs[1:] - bw, ~(separation_needed * spaces > (2 * bw))
                ),
            )
        )

        # Beams separated between bw and 2*bw need a fake nan ray at midpoint and two duplicated data rays over and below
        condition = separation_needed * (spaces < (2 * bw))
        under_two_bw_nan = np.delete(sorted_elevs_midpoints, ~condition)

        nan_space = np.delete(spaces - bw, ~condition)
        under_two_bw_dup_data = np.concatenate(
            (
                under_two_bw_nan - nan_space,
                under_two_bw_nan + nan_space,
            )
        )

        # If the first (lowest) real ray falls in this last case
        # we also need to add a nan ray below
        if condition[0]:
            under_two_bw_nan = np.concatenate(
                (np.array(sorted_elevs[0] - bw, ndmin=1), under_two_bw_nan)
            )

        # Join all fake ray elevations for nan or duplicated data
        nan_fake_elevs = np.sort(
            np.concatenate((two_bw, over_two_bw, under_two_bw_nan))
        )

        data_fake_elevs = np.sort(under_two_bw_dup_data)

        # Sort volume in ascending order of elevation
        obj = obj.sortby("sweep_fixed_angle")

        # Generate fake rays array
        all_fake_elevs = np.sort(np.concatenate((nan_fake_elevs, data_fake_elevs)))
        obj_fake = obj.interp(sweep_fixed_angle=all_fake_elevs, method="nearest")
        obj_fake = obj_fake.where(
            ~obj_fake.sweep_fixed_angle.isin(nan_fake_elevs)
        )  # fill with nan on corresponding elevations

        # set elevation coord correctly because georeferencing is based on this coord
        obj_fake.coords["elevation"] = obj_fake["sweep_fixed_angle"]

    ds = obj.copy()
    if bw is not None:
        ds = xr.concat([ds, obj_fake], dim="sweep_fixed_angle")
        ds = ds.sortby("sweep_fixed_angle")

    # Reduce "sweep_mode" to 1D to be able to georeference
    ds["sweep_mode"] = ds["sweep_mode"].min()

    # Georeference the data
    ds = ds.pipe(georef.georeference, crs=crs)

    try:
        return ds.sel(azimuth=azimuth, method=method, tolerance=tolerance)

    except (TypeError, ValueError, KeyError):
        # Is the user providing two points for arbitrary cut?
        try:
            p1 = azimuth[0]
            p2 = azimuth[1]
            # this is just for checking that the points are valid:
            x1 = p1[0]
            y1 = p1[1]
            x2 = p2[0]
            y2 = p2[1]

            # if some of the points is outside the radar volume area raise an exception
            test = np.array(
                [
                    ~(ds.x.min() < x1 < ds.x.max()),
                    ~(ds.x.min() < x2 < ds.x.max()),
                    ~(ds.y.min() < y1 < ds.y.max()),
                    ~(ds.y.min() < y2 < ds.y.max()),
                ]
            )

            if test.any():
                raise ValueError(
                    "At least one of the points given is outside of the radar volume area"
                )

        except TypeError as err:
            # `azimuth` is not a list of azimuths nor a couple of points
            raise TypeError(
                "Not azimuth values nor points was provided to `azimuth`"
            ) from err

        # Check that the two points given are not the same
        try:
            if (p1 == p2).all():
                raise ValueError(
                    "p1=p2. The two points given are the same. Please give different points."
                )
        except AttributeError as err:
            if p1 == p2:
                raise ValueError(
                    "p1=p2. The two points given are the same. Please give different points."
                ) from err

        # number of points to make the line between p1 and p2 (should be greater
        # than the resolution of the volume)
        nn = npl
        # List to collect dataset for every elevation
        selection = list()

        for el in ds.sweep_fixed_angle:
            # For every elevation, select the array of x and y coordinates
            x = ds.sel(sweep_fixed_angle=el.data.tolist()).x.to_numpy()
            y = ds.sel(sweep_fixed_angle=el.data.tolist()).y.to_numpy()

            # Create a KDTree class to look for the nearest neighbors
            tree = KDTree(np.c_[x.ravel(), y.ravel()])

            # Create a line of nn points between the selected p1 and p2
            pline = np.linspace(p1, p2, nn)

            # Search for the nearest neighbors of pline in the x-y array
            dd, ii = tree.query(pline)

            # Eliminate repeated selections and unravel into original dimensions
            ii = np.unique(ii)

            # Stack the azimuth and range coordinates and select the points
            sel = (
                ds.sel(sweep_fixed_angle=(el.data.tolist()))
                .stack(xyi=("azimuth", "range"))
                .isel({"xyi": ii})
            )

            # create values for a new coordinate xy that is the distance to p1 along the line
            xy = np.sqrt((sel.x - p1[0]) ** 2 + (sel.y - p1[1]) ** 2)

            # Add new coordinates
            z_coord = sel.z.to_numpy()
            sel2 = sel.drop_vars({"xyi", "range", "azimuth"}).assign_coords(
                {"xyi": np.arange(len(xy))}
            )
            sel2.coords["xy"] = ("xyi", xy.data)
            sel2.coords["z"] = ("xyi", z_coord)

            selection.append(sel2.expand_dims("sweep_fixed_angle"))

        # Reindex the datasets along the "xyi" dimension
        selection_reindexed = list()
        for ll in range(len(selection)):
            # Since the selection of data for each elevation does not necessarily have the
            # same amount of xyi points, we reindex the xyi dimension expanding to its
            # max length to accomodate all data
            xyi_maxlen = np.array([len(ss.xyi) for ss in selection]).max()
            selection_reindexed.append(
                selection[ll].reindex({"xyi": np.arange(xyi_maxlen)})
            )

        # Combine into a single dataset
        merged = xr.concat(selection_reindexed, dim="sweep_fixed_angle").transpose(
            "sweep_fixed_angle", ...
        )
        # We cannot have coordinates with NaN for plotting, so we fill any NaN by propagating values
        merged["xy"] = merged["xy"].ffill("xyi")
        merged["z"] = merged["z"].ffill("xyi")

        return merged


def docstring(func):
    """Apply docstring and signature to decorated function"""

    def wrapper(decorated):
        decorated.__doc__ = func.__doc__
        decorated.__signature__ = inspect.signature(func)
        return decorated

    return wrapper


def dim0(obj):
    """Return major dimension (azimuth/elevation) of xarray object."""
    if dim0 := set(obj.dims) & {"azimuth", "elevation"}:
        return dim0.pop()
    elif "time" in obj.dims:
        return "time"
    else:
        raise ValueError(
            f"No CfRadial2/FM301 compliant dimension found in {obj.dims!r}. "
            "Expected one of 'azimuth', 'elevation' or 'time'."
        )


def get_apply_ufunc_variables(obj, dim):
    dims = {dim, "range"}
    keep = xr.Dataset(
        {k: v for k, v in obj.data_vars.items() if set(v.dims) & dims != dims}
    )
    obj = xr.Dataset(
        {k: v for k, v in obj.data_vars.items() if set(v.dims) & dims == dims}
    )
    return obj, keep


def get_dataarray(obj, arr):
    if isinstance(arr, str):
        arr = obj[arr]
    assert isinstance(arr, xr.DataArray)
    return arr


class XarrayMethods:
    """BaseClass to bind xarray methods to wradlib SubAccessor

    This wraps xarray.DataArray or xarray.Dataset objects and overrides
    `__repr__`, `_repr_html_`, `__getitem__` and `__getattr__` of those.

    Parameter
    ---------
    obj : xarray.Dataset | xarray.DataArray
    """

    def __init__(self, obj):
        self._obj = obj

    def __repr__(self):
        name = self._obj.__class__.__name__
        cname = self.__class__.__module__
        search = f"xarray.{name}"
        replace = f"{cname}(xarray.{name})"
        out = self._obj.__repr__()
        out = out.replace(search, replace)
        return out

    def _repr_html_(self):
        name = self._obj.__class__.__name__
        cname = self.__class__.__module__
        search = f"xarray.{name}"
        replace = f"{cname}(xarray.{name})"
        out = self._obj._repr_html_()
        out = out.replace(search, replace)
        return out

    def __getitem__(self, item):
        if (
            isinstance(self._obj, xr.DataArray)
            or item not in self._obj.data_vars
            or not self._obj[item].dims
        ):
            return self._obj[item]
        return self.__class__(self._obj[item])

    def __getattr__(self, item):
        if (
            isinstance(self._obj, xr.DataArray)
            or item not in self._obj.data_vars
            or not self._obj[item].dims
        ):
            return getattr(self._obj, item)
        return self.__class__(getattr(self._obj, item))


class UtilMethods(XarrayMethods):
    """wradlib xarray SubAccessor methods for Util."""

    @docstring(_despeckle_xarray)
    def despeckle(self, *args, **kwargs):
        if not isinstance(self, UtilMethods):
            return despeckle(self, *args, **kwargs)
        else:
            return despeckle(self._obj, *args, **kwargs)

    @docstring(_derivate_xarray)
    def derivate(self, *args, **kwargs):
        if not isinstance(self, UtilMethods):
            return derivate(self, *args, **kwargs)
        else:
            return derivate(self._obj, *args, **kwargs)

    @docstring(dim0)
    def dim0(self, *args, **kwargs):
        if not isinstance(self, UtilMethods):
            return dim0(self, *args, **kwargs)
        else:
            return dim0(self._obj, *args, **kwargs)


if __name__ == "__main__":
    print("wradlib: Calling module <util> as main...")
