#!/usr/bin/env python
# Copyright (c) 2011-2023, wradlib developers.
# Distributed under the MIT License. See LICENSE.txt for more info.

"""
Miscellaneous Data I/O
^^^^^^^^^^^^^^^^^^^^^^
.. autosummary::
   :nosignatures:
   :toctree: generated/

   {}
"""
__all__ = [
    "write_polygon_to_text",
    "to_pickle",
    "from_pickle",
    "get_radiosonde",
    "radiosonde_to_xarray",
    "get_membership_functions",
]
__doc__ = __doc__.format("\n   ".join(__all__))

import datetime as dt
import io
import pickle
import urllib
import warnings

import numpy as np
import xarray as xr

from wradlib import util


def _write_polygon_to_txt(f, idx, vertices):
    f.write(f"{idx[0]} {idx[1]}\n")
    for i, v in enumerate(vertices):
        f.write(f"{i} ")
        f.write(f"{v[0]:f} {v[1]:f} {v[2]:f} {v[3]:f}\n")


def write_polygon_to_text(fname, polygons):
    """Writes Polygons to a Text file which can be interpreted by ESRI \
    ArcGIS's "Create Features from Text File (Samples)" tool.

    This is (yet) only a convenience function with limited functionality.
    E.g. interior rings are not yet supported.

    Parameters
    ----------
    fname : str
        name of the file to save the vertex data to
    polygons : list
        list of lists of polygon vertices.
        Each vertex itself is a list of 3 coordinate values and an
        additional value. The third coordinate and the fourth value may be nan.

    Returns
    -------
    None

    Note
    ----
    As Polygons are closed shapes, the first and the last vertex of each
    polygon **must** be the same!

    Examples
    --------
    Writes two triangle Polygons to a text file::
        poly1 = [[0.,0.,0.,0.],[0.,1.,0.,1.],[1.,1.,0.,2.],[0.,0.,0.,0.]]
        poly2 = [[0.,0.,0.,0.],[0.,1.,0.,1.],[1.,1.,0.,2.],[0.,0.,0.,0.]]
        polygons = [poly1, poly2]
        write_polygon_to_text('polygons.txt', polygons)
    The resulting text file will look like this::
        Polygon
        0 0
        0 0.000000 0.000000 0.000000 0.000000
        1 0.000000 1.000000 0.000000 1.000000
        2 1.000000 1.000000 0.000000 2.000000
        3 0.000000 0.000000 0.000000 0.000000
        1 0
        0 0.000000 0.000000 0.000000 0.000000
        1 0.000000 1.000000 0.000000 1.000000
        2 1.000000 1.000000 0.000000 2.000000
        3 0.000000 0.000000 0.000000 0.000000
        END
    """
    with open(fname, "w") as f:
        f.write("Polygon\n")
        count = 0
        for vertices in polygons:
            _write_polygon_to_txt(f, (count, 0), vertices)
            count += 1
        f.write("END\n")


def to_pickle(fpath, obj):
    """Pickle object <obj> to file <fpath>"""
    output = open(fpath, "wb")
    pickle.dump(obj, output)
    output.close()


def from_pickle(fpath):
    """Return pickled object from file <fpath>"""
    pkl_file = open(fpath, "rb")
    obj = pickle.load(pkl_file)
    pkl_file.close()
    return obj


def get_radiosonde(wmoid, date, *, cols=None, xarray=False, **kwargs):
    """Download radiosonde data from internet.

    Based on http://weather.uwyo.edu/upperair/sounding.html.

    Parameters
    ----------
    wmoid : int
        WMO radiosonde ID
    date : :py:class:`datetime.datetime`
        Date and Time

    Keyword Arguments
    -----------------
    cols : tuple, optional
        tuple of int or strings describing the columns to consider,
        defaults to None (all columns)
    xarray : bool
        Defaults to False. If True return :class:`xarray:xarray.Dataset`.
    max_height : float
        Passed to :func:`~wradlib.io.misc.radiosonde_to_xarray` if xarray=True.
        Maximum height of output DataArray in m. Defaults to 30.000.0 m.
    res : float
        Passed to :func:`~wradlib.io.misc.radiosonde_to_xarray` if xarray=True.
        Resolution to which output DataArray is linearly interpolated in m.
        Defaults to 1.0 m.

    Returns
    -------
    data : :py:class:`numpy:numpy.ndarray`
        Structured array of radiosonde data
    meta : dict
        radiosonde metadata
    ds : :class:`xarray:xarray.Dataset`
        Only if xarray=True.
        Dataset with vertical radiosonde profile.


    """
    year = date.strftime("%Y")
    month = date.strftime("%m")
    day = date.strftime("%d")
    hour = date.strftime("%H")

    # Radiosondes are only at noon and midnight
    hour = "12" if (6 < int(hour) < 18) else "00"

    # url
    url_str = (
        "http://weather.uwyo.edu/cgi-bin/sounding?"
        "TYPE=TEXT%3ALIST&"
        f"YEAR={year}&MONTH={month}&"
        f"FROM={day}{hour}&TO={day}{hour}&STNM={wmoid}&"
        "ICE=1"
    )

    # html request
    with urllib.request.urlopen(url_str) as url_request:
        response = url_request.read()

    # decode string
    url_text = response.decode("utf-8")

    # first line (eg errormessage)
    if url_text.find("<H2>") == -1:
        err = url_text.split("\n", 1)[1].split("\n", 1)[0]
        raise ValueError(err)

    # extract relevant information
    url_data = url_text.split("<PRE>")[1].split("</PRE>")[0]
    url_meta = url_text.split("<PRE>")[2].split("</PRE>")[0]

    # extract empty lines, names, units and data
    _, _, names, units, _, url_data = url_data.split("\n", 5)

    names = names.split()
    units = units.split()

    unitdict = {name: unit for (name, unit) in zip(names, units)}

    # read data
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        data = np.genfromtxt(
            io.StringIO(url_data),
            names=names,
            dtype=float,
            usecols=cols,
            autostrip=True,
            invalid_raise=False,
        )

    # read metadata
    meta = {}
    for i, row in enumerate(io.StringIO(url_meta)):
        if i == 0:
            continue
        k, v = row.split(":")
        k = k.strip()
        v = v.strip()
        if k == "Station number":
            v = int(v)
        elif k == "Observation time":
            v = dt.datetime.strptime(v, "%y%m%d/%H%M")
        elif i > 2:
            v = float(v)
        meta[k] = v

    meta["quantity"] = {item: unitdict[item] for item in data.dtype.names}

    if xarray:
        return radiosonde_to_xarray(data, meta=meta, **kwargs)

    return data, meta


def radiosonde_to_xarray(data, *, max_height=None, res=None, meta=None):
    """Convert Radiosonde Data to :class:`xarray:xarray.Dataset.

    This converts dictionary returned by :func:`~wradlib.io.misc.get_radiosonde` into
    a :class:`xarray:xarray.Dataset`.

    Parameters
    ----------
    data : dict
        Dictionary returned from :func:`~wradlib.io.misc.get_radiosonde`.

    Keyword Arguments
    -----------------
    max_height : float
        Maximum height of output DataArray in m.
        Defaults to None (no height restriction).
    res : float
        Resolution to which output DataArray is linearly interpolated in m.
        Defaults to None (no interpolation).
    meta : dict, optional
        Dictionay of meta attributes :func:`~wradlib.io.misc.get_radiosonde`.

    Returns
    -------
    ds : :class:`xarray:xarray.Dataset`
        Dataset with vertical radiosonde profile.

    """
    data_dict = {name: (["dim"], data[name]) for name in data.dtype.names}
    height = data_dict.pop("HGHT")
    ds = xr.Dataset(data_dict, coords={"HGHT": height}).swap_dims(dim="HGHT")
    # remove nans
    ds = ds.dropna(dim="HGHT", how="any")

    # default to max height of data
    if max_height is None:
        max_height = ds.HGHT.max()

    if res is None:
        ds = ds.where(ds.HGHT <= max_height).dropna(dim="HGHT", how="any")
    else:
        ht = np.arange(0.0, max_height + res, res)
        ds = ds.interp({"HGHT": ht})
        ds = ds.bfill(dim="HGHT")

    if meta is not None:
        ds.attrs = meta
    return ds


def get_membership_functions(filename):
    """Reads membership function parameters from wradlib-data file.

    Parameters
    ----------
    filename : str
        Filename of wradlib-data file

    Returns
    -------
    msf : :py:class:`numpy:numpy.ndarray`
        Array of membership funcions with shape (hm-classes, observables,
        indep-ranges, 5)
    """
    gzip = util.import_optional("gzip")

    with gzip.open(filename, "rb") as f:
        nclass = int(f.readline().decode().split(":")[1].strip())
        nobs = int(f.readline().decode().split(":")[1].strip())
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning)
            data = np.genfromtxt(f, skip_header=10, autostrip=True, invalid_raise=False)

    data = np.reshape(data, (nobs, int(data.shape[0] / nobs), data.shape[1]))
    msf = np.reshape(
        data, (data.shape[0], nclass, int(data.shape[1] / nclass), data.shape[2])
    )
    msf = np.swapaxes(msf, 0, 1)

    return msf
