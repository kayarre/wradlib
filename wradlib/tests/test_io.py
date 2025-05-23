#!/usr/bin/env python
# Copyright (c) 2011-2023, wradlib developers.
# Distributed under the MIT License. See LICENSE.txt for more info.

import datetime
import gzip
import io as sio
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass

import numpy as np
import pytest
import xarray as xr

from wradlib import georef, io, util, zonalstats

from . import (
    get_wradlib_data_file,
    get_wradlib_data_file_or_filelike,
    requires_dask,
    requires_data_folder,
    requires_gdal,
    requires_geos,
    requires_h5py,
    requires_netcdf,
    requires_requests,
    requires_secrets,
    requires_xmltodict,
)

wradlib_data = util.import_optional("wradlib_data", dep="development")


@pytest.fixture(params=["file", "filelike"])
def file_or_filelike(request):
    return request.param


# testing functions related to read_dx
def test__get_timestamp_from_filename():
    filename = "raa00-dx_10488-200608050000-drs---bin"
    assert io.radolan._get_timestamp_from_filename(filename) == datetime.datetime(
        2006, 8, 5, 0
    )
    filename = "raa00-dx_10488-0608050000-drs---bin"
    assert io.radolan._get_timestamp_from_filename(filename) == datetime.datetime(
        2006, 8, 5, 0
    )


def test_get_dx_timestamp():
    filename = "raa00-dx_10488-200608050000-drs---bin"
    assert (
        io.radolan.get_dx_timestamp(filename).__str__() == "2006-08-05 00:00:00+00:00"
    )
    filename = "raa00-dx_10488-0608050000-drs---bin"
    assert (
        io.radolan.get_dx_timestamp(filename).__str__() == "2006-08-05 00:00:00+00:00"
    )


def test_parse_dx_header():
    header = (
        b"DX021655109080608BY54213VS 2CO0CD2CS0EP0.30.30.40.50."
        b"50.40.40.4MS999~ 54( 120,  46) 43-31 44 44 50 50 54 52 "
        b"52 42 39 36  ~ 53(  77,  39) 34-31 32 44 39 48 53 44 45 "
        b"35 28 28  ~ 53(  98,  88)-31-31-31 53 53 52 53 53 53 32-31"
        b" 18  ~ 57(  53,  25)-31-31 41 52 57 54 52 45 42 34 20 20  "
        b"~ 55(  37,  38)-31-31 55 48 43 39 50 51 42 15 15  5  ~ "
        b"56( 124,  19)-31 56 56 56 52 53 50 50 41 44 27 28  ~ "
        b"47(  62,  40)-31-31 46 42 43 40 47 41 34 27 16 10  ~ "
        b"46( 112,  62)-31-31 30 33 44 46 46 46 46 33 38 23  ~ "
        b"44( 100, -54)-31-31 41 41 38 44 43 43 28 35 30  6  ~ "
        b"47( 104,  75)-31-31 45 47 38 41 41 30 30 15 15  8  ^ "
        b"58( 104, -56) 58 58 58 58 53 37 37  9 15-31-31-31  ^ "
        b"58( 123,  16) 56-31 58 58 46 52 49 35 44 14 32  0  ^ "
        b"57(  39,  38)-31 55 53 57 55 27 29 18 11  1  1-31  ^ "
        b"54( 100,  85)-31-31 54 54 46 50-31-31 17-31-31-31  ^ "
        b"53(  71,  39)-31-31 46 53 52 34 34 40 32 32 23  0  ^ "
        b"53( 118,  49)-31-31 51 51 53 52 48 42 39 29 24-31  ` "
        b"28(  90,  43)-31-31 27 27 28 27 27 19 24 19  9  9  ` "
        b"42( 114,  53)-31-31 36 36 40 42 40 40 34 34 37 30  ` "
        b"54(  51,  27)-31-31 49 49 54 51 45 39 40 34.."
    )
    head = ""
    for c in sio.BytesIO(header):
        head += str(c.decode())
    io.radolan.parse_dx_header(head)


def test_parse_old_dx_header():
    header = b"DX010000109080100BY 4173VS 1CO2CD2CS0MS***XXXXXXXX"
    head = ""
    for c in sio.BytesIO(header):
        head += str(c.decode())
    io.radolan.parse_dx_header(head)


def test_unpack_dx():
    pass


def test_read_dx(file_or_filelike):
    filename = "dx/raa00-dx_10908-0806021655-fbg---bin.gz"
    with get_wradlib_data_file_or_filelike(filename, file_or_filelike) as dxfile:
        data, attrs = io.radolan.read_dx(dxfile)


def test_write_polygon_to_text():
    poly1 = [
        [0.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 1.0],
        [1.0, 1.0, 0.0, 2.0],
        [0.0, 0.0, 0.0, 0.0],
    ]
    poly2 = [
        [0.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 1.0],
        [1.0, 1.0, 0.0, 2.0],
        [0.0, 0.0, 0.0, 0.0],
    ]
    polygons = [poly1, poly2]
    res = [
        "Polygon\n",
        "0 0\n",
        "0 0.000000 0.000000 0.000000 0.000000\n",
        "1 0.000000 1.000000 0.000000 1.000000\n",
        "2 1.000000 1.000000 0.000000 2.000000\n",
        "3 0.000000 0.000000 0.000000 0.000000\n",
        "1 0\n",
        "0 0.000000 0.000000 0.000000 0.000000\n",
        "1 0.000000 1.000000 0.000000 1.000000\n",
        "2 1.000000 1.000000 0.000000 2.000000\n",
        "3 0.000000 0.000000 0.000000 0.000000\n",
        "END\n",
    ]
    tmp = tempfile.NamedTemporaryFile()
    name = tmp.name
    tmp.close()
    io.misc.write_polygon_to_text(name, polygons)
    assert open(name).readlines() == res


def test_pickle():
    arr = np.zeros((124, 248), dtype=np.int16)
    tmp = tempfile.NamedTemporaryFile()
    name = tmp.name
    tmp.close()
    io.misc.to_pickle(name, arr)
    res = io.misc.from_pickle(name)
    np.testing.assert_allclose(arr, res)


@pytest.fixture
def radiosonde():
    @dataclass(init=False, repr=False, eq=False)
    class TestRadiosonde:
        date = datetime.datetime(2013, 7, 1, 15, 30)
        res1 = np.array(
            [
                (
                    1000.0,
                    147.0,
                    17.4,
                    13.5,
                    13.5,
                    78.0,
                    78.0,
                    9.81,
                    200.0,
                    6.0,
                    290.6,
                    318.5,
                    292.3,
                )
            ],
            dtype=[
                ("PRES", "<f8"),
                ("HGHT", "<f8"),
                ("TEMP", "<f8"),
                ("DWPT", "<f8"),
                ("FRPT", "<f8"),
                ("RELH", "<f8"),
                ("RELI", "<f8"),
                ("MIXR", "<f8"),
                ("DRCT", "<f8"),
                ("SKNT", "<f8"),
                ("THTA", "<f8"),
                ("THTE", "<f8"),
                ("THTV", "<f8"),
            ],
        )

        res2 = {
            "Station identifier": "EDZE",
            "Station number": 10410,
            "Observation time": datetime.datetime(2013, 7, 1, 12, 0),
            "Station latitude": 51.4,
            "Station longitude": 6.97,
            "Station elevation": 147.0,
            "Showalter index": 6.1,
            "Lifted index": 0.57,
            "LIFT computed using virtual temperature": 0.51,
            "SWEAT index": 77.7,
            "K index": 11.7,
            "Cross totals index": 13.7,
            "Vertical totals index": 28.7,
            "Totals totals index": 42.4,
            "Convective Available Potential Energy": 7.03,
            "CAPE using virtual temperature": 18.0,
            "Convective Inhibition": 0.0,
            "CINS using virtual temperature": 0.0,
            "Equilibrum Level": 597.47,
            "Equilibrum Level using virtual temperature": 589.23,
            "Equivalent potential temp [K] of the LCL": 315.07,
            "Level of Free Convection": 931.56,
            "LFCT using virtual temperature": 934.17,
            "Bulk Richardson Number": 0.24,
            "Bulk Richardson Number using CAPV": 0.62,
            "Temp [K] of the Lifted Condensation Level": 284.17,
            "Pres [hPa] of the Lifted Condensation Level": 934.17,
            "Mean mixed layer potential temperature": 289.76,
            "Mean mixed layer mixing ratio": 8.92,
            "1000 hPa to 500 hPa thickness": 5543.0,
            "Precipitable water [mm] for entire sounding": 19.02,
        }

        res3 = {
            "PRES": "hPa",
            "HGHT": "m",
            "TEMP": "C",
            "DWPT": "C",
            "FRPT": "C",
            "RELH": "%",
            "RELI": "%",
            "MIXR": "g/kg",
            "DRCT": "deg",
            "SKNT": "knot",
            "THTA": "K",
            "THTE": "K",
            "THTV": "K",
        }

    yield TestRadiosonde


@requires_requests
def test_get_radiosonde(radiosonde):
    import urllib

    try:
        with pytest.raises(ValueError):
            data, meta = io.misc.get_radiosonde(10412, radiosonde.date)
        data, meta = io.misc.get_radiosonde(10410, radiosonde.date)
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        print(e)
        print("Test skipped!")
    else:
        assert data[0] == radiosonde.res1[0]
        quant = meta.pop("quantity")
        assert meta == radiosonde.res2
        assert quant == radiosonde.res3


@pytest.mark.parametrize("res", [None, 1.0])
def test_radiosonde_to_xarray(res):
    filename1 = get_wradlib_data_file("misc/radiosonde_10410_20140610_1200.h5")
    filename2 = get_wradlib_data_file("misc/radiosonde_10410_20140610_1200.json")
    rs_data, _ = io.from_hdf5(filename1)
    with open(filename2) as infile:
        rs_meta = json.load(infile)

    ds = io.misc.radiosonde_to_xarray(
        rs_data, meta=rs_meta, max_height=30000.0, res=res
    )
    assert ds.HGHT.max() == 29743.0 if res is None else 30000.0
    assert ds.sizes["HGHT"] == 92 if res is None else 30000
    for k, v in ds.data_vars.items():
        idx = 0 if res is None else 153
        assert v[idx] == rs_data[0][k]
    assert ds.attrs == rs_meta


def test_get_membership_functions():
    filename = get_wradlib_data_file("misc/msf_xband.gz")
    msf = io.misc.get_membership_functions(filename)
    res = np.array(
        [
            [6.000e00, 5.000e00, 1.000e01, 3.500e01, 4.000e01],
            [6.000e00, -7.458e-01, -4.457e-01, 5.523e-01, 8.523e-01],
            [6.000e00, 7.489e-01, 7.689e-01, 9.236e-01, 9.436e-01],
            [6.000e00, -5.037e-01, -1.491e-01, -1.876e-01, 1.673e-01],
            [6.000e00, -5.000e00, 0.000e00, 4.000e01, 2.000e03],
        ]
    )
    assert msf.shape == (11, 5, 55, 5)
    print(msf[0, :, 8, :])
    np.testing.assert_array_equal(msf[0, :, 8, :], res)


@requires_h5py
def test_read_generic_hdf5(file_or_filelike):
    filename = "hdf5/IDR66_20141206_094829.vol.h5"
    with get_wradlib_data_file_or_filelike(filename, file_or_filelike) as f:
        io.hdf.read_generic_hdf5(f)


@requires_h5py
def test_read_opera_hdf5(file_or_filelike):
    filename = "hdf5/IDR66_20141206_094829.vol.h5"
    with get_wradlib_data_file_or_filelike(filename, file_or_filelike) as f:
        io.hdf.read_opera_hdf5(f)


@requires_h5py
def test_read_gamic_hdf5(file_or_filelike):
    ppi = "hdf5/2014-08-10--182000.ppi.mvol"
    rhi = "hdf5/2014-06-09--185000.rhi.mvol"
    filename = (
        "gpm/2A-CS-151E24S154E30S.GPM.Ku.V7-20170308.20141206-"
        "S095002-E095137.004383.V05A.HDF5"
    )

    with get_wradlib_data_file_or_filelike(ppi, file_or_filelike) as f:
        io.hdf.read_gamic_hdf5(f)
    with get_wradlib_data_file_or_filelike(rhi, file_or_filelike) as f:
        io.hdf.read_gamic_hdf5(f)
    with pytest.raises(IOError):
        with get_wradlib_data_file_or_filelike(filename, file_or_filelike) as f:
            io.hdf.read_gamic_hdf5(f)


@requires_h5py
def test_to_hdf5():
    arr = np.zeros((124, 248), dtype=np.int16)
    metadata = {"test": 12.0}
    tmp = tempfile.NamedTemporaryFile()
    name = tmp.name
    tmp.close()
    io.hdf.to_hdf5(name, arr, metadata=metadata)
    res, resmeta = io.hdf.from_hdf5(name)
    np.testing.assert_allclose(arr, res)
    assert metadata == resmeta

    with pytest.raises(KeyError):
        io.hdf.from_hdf5(name, dataset="NotAvailable")


@requires_gdal
def test_read_safnwc():
    filename = "hdf5/SAFNWC_MSG3_CT___201304290415_BEL_________.h5"
    safnwcfile = get_wradlib_data_file(filename)
    io.gdal.read_safnwc(safnwcfile)


@requires_netcdf
@requires_gdal
def test_read_gpm():
    filename1 = (
        "gpm/2A-CS-151E24S154E30S.GPM.Ku.V7-20170308.20141206-"
        "S095002-E095137.004383.V05A.HDF5"
    )
    gpm_file = get_wradlib_data_file(filename1)
    filename2 = "hdf5/IDR66_20141206_094829.vol.h5"
    gr2gpm_file = get_wradlib_data_file(filename2)
    gr_data = io.netcdf.read_generic_netcdf(gr2gpm_file)
    dset = gr_data["dataset2"]
    nray_gr = dset["where"]["nrays"]
    ngate_gr = dset["where"]["nbins"].astype("i4")
    elev_gr = dset["where"]["elangle"]
    dr_gr = dset["where"]["rscale"]
    lon0_gr = gr_data["where"]["lon"]
    lat0_gr = gr_data["where"]["lat"]
    alt0_gr = gr_data["where"]["height"]
    coord = georef.sweep_centroids(nray_gr, dr_gr, ngate_gr, elev_gr)
    coords = georef.spherical_to_proj(
        coord[..., 0], coord[..., 1], coord[..., 2], (lon0_gr, lat0_gr, alt0_gr)
    )
    lon = coords[..., 0]
    lat = coords[..., 1]
    bbox = zonalstats.get_bbox(lon, lat)
    io.hdf.read_gpm(gpm_file, bbox=bbox)


@requires_h5py
@requires_netcdf
@requires_gdal
def test_read_trmm():
    # define TRMM data sets
    trmm_2a23_file = get_wradlib_data_file(
        "trmm/2A-CS-151E24S154E30S.TRMM.PR.2A23.20100206-"
        "S111425-E111526.069662.7.HDF"
    )
    trmm_2a25_file = get_wradlib_data_file(
        "trmm/2A-CS-151E24S154E30S.TRMM.PR.2A25.20100206-"
        "S111425-E111526.069662.7.HDF"
    )

    filename2 = "hdf5/IDR66_20141206_094829.vol.h5"
    gr2gpm_file = get_wradlib_data_file(filename2)
    gr_data = io.netcdf.read_generic_netcdf(gr2gpm_file)
    dset = gr_data["dataset2"]
    nray_gr = dset["where"]["nrays"]
    ngate_gr = dset["where"]["nbins"].astype("i4")
    elev_gr = dset["where"]["elangle"]
    dr_gr = dset["where"]["rscale"]
    lon0_gr = gr_data["where"]["lon"]
    lat0_gr = gr_data["where"]["lat"]
    alt0_gr = gr_data["where"]["height"]
    coord = georef.sweep_centroids(nray_gr, dr_gr, ngate_gr, elev_gr)
    coords = georef.spherical_to_proj(
        coord[..., 0], coord[..., 1], coord[..., 2], (lon0_gr, lat0_gr, alt0_gr)
    )
    lon = coords[..., 0]
    lat = coords[..., 1]
    bbox = zonalstats.get_bbox(lon, lat)

    io.hdf.read_trmm(trmm_2a23_file, trmm_2a25_file, bbox=bbox)


def radolan_files():
    return [
        "radolan/misc/raa00-pc_10015-1408030905-dwd---bin.gz",
        "radolan/misc/raa01-%j_10000-2108010550-dwd---bin.gz",
        "radolan/misc/raa01-%m_10000-2108010550-dwd---bin.gz",
        "radolan/misc/raa01-%y_10000-2108010550-dwd---bin.gz",
        "radolan/misc/raa01-ex_10000-1408102050-dwd---bin.gz",
        "radolan/misc/raa01-rw_10000-1408030950-dwd---bin.gz",
        "radolan/misc/raa01-rw_10000-1408102050-dwd---bin.gz",
        "radolan/misc/raa01-rx_10000-1408102050-dwd---bin.gz",
        "radolan/misc/raa01-sf_10000-1305270050-dwd---bin.gz",
        "radolan/misc/raa01-sf_10000-1305280050-dwd---bin.gz",
        "radolan/misc/raa01-sf_10000-1406100050-dwd---bin.gz",
        "radolan/misc/raa01-sf_10000-1408102050-dwd---bin.gz",
    ]


def test_get_radolan_header_token():
    keylist = [
        "BY",
        "VS",
        "SW",
        "PR",
        "INT",
        "GP",
        "MS",
        "LV",
        "CS",
        "MX",
        "BG",
        "ST",
        "VV",
        "MF",
        "QN",
        "VR",
        "U",
    ]
    head = io.radolan.get_radolan_header_token()
    for key in keylist:
        assert head[key] is None


def test_get_radolan_header_token_pos():
    header = (
        "RW030950100000814BY1620130VS 3SW   2.13.1PR E-01"
        "INT  60GP 900x 900MS 58<boo,ros,emd,hnr,pro,ess,"
        "asd,neu,nhb,oft,tur,isn,fbg,mem>"
    )

    test_head = io.radolan.get_radolan_header_token()
    test_head["PR"] = (43, 48)
    test_head["GP"] = (57, 66)
    test_head["INT"] = (51, 55)
    test_head["SW"] = (32, 41)
    test_head["VS"] = (28, 30)
    test_head["MS"] = (68, 128)
    test_head["BY"] = (19, 26)

    head = io.radolan.get_radolan_header_token_pos(header)
    assert head == test_head

    header = (
        "RQ210945100000517BY1620162VS 2SW 1.7.2PR E-01"
        "INT 60GP 900x 900VV 0MF 00000002QN 001"
        "MS 67<bln,drs,eis,emd,ess,fbg,fld,fra,ham,han,muc,"
        "neu,nhb,ros,tur,umd>"
    )
    test_head = {
        "BY": (19, 26),
        "VS": (28, 30),
        "SW": (32, 38),
        "PR": (40, 45),
        "INT": (48, 51),
        "GP": (53, 62),
        "MS": (85, 153),
        "LV": None,
        "CS": None,
        "MX": None,
        "BG": None,
        "ST": None,
        "VV": (64, 66),
        "MF": (68, 77),
        "QN": (79, 83),
        "VR": None,
        "U": None,
    }
    head = io.radolan.get_radolan_header_token_pos(header)
    assert head == test_head


def test_decode_radolan_runlength_line():
    # fmt: off
    testarr = [0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.,
               0., 0., 0.,
               0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.,
               0., 0., 0.,
               0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.,
               0., 0., 0.,
               0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.,
               0., 0., 0.,
               0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.,
               0., 0., 0.,
               0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.,
               0., 0., 0.,
               0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.,
               0., 0., 0.,
               0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 9., 9., 9., 9., 9.,
               9., 9., 9.,
               9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9.,
               9., 9., 9.,
               9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9.,
               9., 9., 9.,
               9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9.,
               9., 9., 9.,
               9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9.,
               9., 9., 9.,
               9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9.,
               9., 9., 9.,
               9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9.,
               9., 9., 9.,
               9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9.,
               9., 9., 9.,
               9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9.,
               9., 9., 9.,
               9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9.,
               9., 9., 9.,
               9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9.,
               9., 9., 9.,
               9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9.,
               9., 9., 9.,
               9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9.,
               9., 9., 9.,
               9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9.,
               9., 9., 9.,
               9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9.,
               9., 9., 9.,
               9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9., 9.,
               9., 9., 9.,
               9., 9., 9., 9., 9., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.,
               0., 0., 0.,
               0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.,
               0., 0., 0.,
               0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]
    # fmt: on
    testline = (
        b"\x10\x98\xf9\xf9\xf9\xf9\xf9\xf9\xf9\xf9\xf9\xf9\xf9\xf9"
        b"\xf9\xf9\xf9\xf9\xf9\xf9\xd9\n"
    )
    testline1 = b"\x10\n"
    testattrs = {"ncol": 460, "nodataflag": 0}
    arr = np.frombuffer(testline, np.uint8).astype(np.uint8)
    line = io.radolan.decode_radolan_runlength_line(arr, testattrs)
    np.testing.assert_allclose(line, testarr)
    arr = np.frombuffer(testline1, np.uint8).astype(np.uint8)
    line = io.radolan.decode_radolan_runlength_line(arr, testattrs)
    np.testing.assert_allclose(line, [0] * 460)


def test_read_radolan_runlength_line():
    testline = (
        b"\x10\x98\xf9\xf9\xf9\xf9\xf9\xf9\xf9\xf9\xf9\xf9\xf9\xf9"
        b"\xf9\xf9\xf9\xf9\xf9\xf9\xd9\n"
    )
    testarr = np.frombuffer(testline, np.uint8).astype(np.uint8)
    fid, temp_path = tempfile.mkstemp()
    tmp_id = open(temp_path, "wb")
    tmp_id.write(testline)
    tmp_id.close()
    tmp_id = open(temp_path, "rb")
    line = io.radolan.read_radolan_runlength_line(tmp_id)
    tmp_id.close()
    os.close(fid)
    os.remove(temp_path)
    np.testing.assert_allclose(line, testarr)


def test_decode_radolan_runlength_array():
    filename = "radolan/misc/raa00-pc_10015-1408030905-dwd---bin.gz"
    pg_file = get_wradlib_data_file(filename)
    with io.get_radolan_filehandle(pg_file) as pg_fid:
        header = io.radolan.read_radolan_header(pg_fid)
        attrs = io.radolan.parse_dwd_composite_header(header)
        data = io.radolan.read_radolan_binary_array(pg_fid, attrs["datasize"])
    attrs["nodataflag"] = 255
    arr = io.radolan.decode_radolan_runlength_array(data, attrs)
    assert arr.shape == (460, 460)


def test_read_radolan_binary_array():
    filename = "radolan/misc/raa01-rw_10000-1408030950-dwd---bin.gz"
    rw_file = get_wradlib_data_file(filename)
    with io.radolan.get_radolan_filehandle(rw_file) as rw_fid:
        header = io.radolan.read_radolan_header(rw_fid)
        attrs = io.radolan.parse_dwd_composite_header(header)
        data = io.radolan.read_radolan_binary_array(rw_fid, attrs["datasize"])
    assert len(data) == attrs["datasize"]

    with io.radolan.get_radolan_filehandle(rw_file) as rw_fid:
        header = io.radolan.read_radolan_header(rw_fid)
        attrs = io.radolan.parse_dwd_composite_header(header)
        with pytest.raises(IOError):
            io.radolan.read_radolan_binary_array(rw_fid, attrs["datasize"] + 10)


@pytest.mark.skipif(sys.platform.startswith("win"), reason="no gunzip on windows")
def test_get_radolan_filehandle():
    filename = "radolan/misc/raa01-rw_10000-1408030950-dwd---bin.gz"
    rw_file = get_wradlib_data_file(filename)
    with io.radolan.get_radolan_filehandle(rw_file) as rw_fid:
        assert rw_file == rw_fid.name
    rw_fid = io.radolan.get_radolan_filehandle(rw_file)
    assert rw_file == rw_fid.name
    rw_fid.close()

    command = f"gunzip -k -f {rw_file}"
    subprocess.check_call(command, shell=True)

    with io.radolan.get_radolan_filehandle(rw_file[:-3]) as rw_fid:
        assert rw_file[:-3] == rw_fid.name

    rw_fid = io.radolan.get_radolan_filehandle(rw_file[:-3])
    assert rw_file[:-3] == rw_fid.name
    rw_fid.close()


def test_read_radolan_header():
    rx_header = (
        b"RW030950100000814BY1620130VS 3SW   2.13.1PR E-01"
        b"INT  60GP 900x 900MS 58<boo,ros,emd,hnr,pro,ess,"
        b"asd,neu,nhb,oft,tur,isn,fbg,mem>"
    )

    buf = sio.BytesIO(rx_header)
    with pytest.raises(EOFError):
        io.radolan.read_radolan_header(buf)

    buf = sio.BytesIO(rx_header + b"\x03")
    header = io.radolan.read_radolan_header(buf)
    assert header == rx_header.decode()


def test_parse_dwd_composite_header():
    rx_header = (
        "RW030950100000814BY1620130VS 3SW   2.13.1PR E-01INT  60"
        "GP 900x 900MS 58<boo,ros,emd,hnr,pro,ess,asd,neu,nhb,"
        "oft,tur,isn,fbg,mem>"
    )
    test_rx = {
        "maxrange": "150 km",
        "formatversion": 3,
        "radarlocations": [
            "boo",
            "ros",
            "emd",
            "hnr",
            "pro",
            "ess",
            "asd",
            "neu",
            "nhb",
            "oft",
            "tur",
            "isn",
            "fbg",
            "mem",
        ],
        "nrow": 900,
        "intervalseconds": 3600,
        "precision": 0.1,
        "datetime": datetime.datetime(2014, 8, 3, 9, 50),
        "ncol": 900,
        "radolanversion": "2.13.1",
        "producttype": "RW",
        "radarid": "10000",
        "datasize": 1620001,
    }

    pg_header = (
        "PG030905100000814BY20042LV 6  1.0 19.0 28.0 37.0 46.0 "
        "55.0CS0MX 0MS 82<boo,ros,emd,hnr,pro,ess,asd,neu,nhb,"
        "oft,tur,isn,fbg,mem,czbrd> are used, BG460460"
    )
    test_pg = {
        "radarlocations": [
            "boo",
            "ros",
            "emd",
            "hnr",
            "pro",
            "ess",
            "asd",
            "neu",
            "nhb",
            "oft",
            "tur",
            "isn",
            "fbg",
            "mem",
            "czbrd",
        ],
        "nrow": 460,
        "level": [1.0, 19.0, 28.0, 37.0, 46.0, 55.0],
        "datetime": datetime.datetime(2014, 8, 3, 9, 5),
        "ncol": 460,
        "producttype": "PG",
        "radarid": "10000",
        "nlevel": 6,
        "indicator": "near ground level",
        "imagecount": 0,
        "datasize": 19889,
    }

    rq_header = (
        "RQ210945100000517BY1620162VS 2SW 1.7.2PR E-01"
        "INT 60GP 900x 900VV 0MF 00000002QN 001"
        "MS 67<bln,drs,eis,emd,ess,fbg,fld,fra,ham,han,muc,"
        "neu,nhb,ros,tur,umd>"
    )

    test_rq = {
        "producttype": "RQ",
        "datetime": datetime.datetime(2017, 5, 21, 9, 45),
        "radarid": "10000",
        "datasize": 1620008,
        "maxrange": "128 km",
        "formatversion": 2,
        "radolanversion": "1.7.2",
        "precision": 0.1,
        "intervalseconds": 3600,
        "nrow": 900,
        "ncol": 900,
        "radarlocations": [
            "bln",
            "drs",
            "eis",
            "emd",
            "ess",
            "fbg",
            "fld",
            "fra",
            "ham",
            "han",
            "muc",
            "neu",
            "nhb",
            "ros",
            "tur",
            "umd",
        ],
        "predictiontime": 0,
        "moduleflag": 2,
        "quantification": 1,
    }

    sq_header = (
        "SQ102050100000814BY1620231VS 3SW   2.13.1PR E-01"
        "INT 360GP 900x 900MS 62<boo,ros,emd,hnr,umd,pro,ess,"
        "asd,neu,nhb,oft,tur,isn,fbg,mem> ST 92<asd 6,boo 6,"
        "emd 6,ess 6,fbg 6,hnr 6,isn 6,mem 6,neu 6,nhb 6,oft 6,"
        "pro 6,ros 6,tur 6,umd 6>"
    )

    test_sq = {
        "producttype": "SQ",
        "datetime": datetime.datetime(2014, 8, 10, 20, 50),
        "radarid": "10000",
        "datasize": 1620001,
        "maxrange": "150 km",
        "formatversion": 3,
        "radolanversion": "2.13.1",
        "precision": 0.1,
        "intervalseconds": 21600,
        "nrow": 900,
        "ncol": 900,
        "radarlocations": [
            "boo",
            "ros",
            "emd",
            "hnr",
            "umd",
            "pro",
            "ess",
            "asd",
            "neu",
            "nhb",
            "oft",
            "tur",
            "isn",
            "fbg",
            "mem",
        ],
        "radardays": [
            "asd 6",
            "boo 6",
            "emd 6",
            "ess 6",
            "fbg 6",
            "hnr 6",
            "isn 6",
            "mem 6",
            "neu 6",
            "nhb 6",
            "oft 6",
            "pro 6",
            "ros 6",
            "tur 6",
            "umd 6",
        ],
    }

    yw_header = (
        "YW070235100001014BY1980156VS 3SW   2.18.3PR E-02"
        "INT   5U0GP1100x 900MF 00000000VR2017.002"
        "MS 61<boo,ros,emd,hnr,umd,pro,ess,asd,neu,"
        "nhb,oft,tur,isn,fbg,mem>"
    )

    test_yw = {
        "producttype": "YW",
        "datetime": datetime.datetime(2014, 10, 7, 2, 35),
        "radarid": "10000",
        "datasize": 1980000,
        "maxrange": "150 km",
        "formatversion": 3,
        "radolanversion": "2.18.3",
        "precision": 0.01,
        "intervalseconds": 300,
        "intervalunit": 0,
        "nrow": 1100,
        "ncol": 900,
        "moduleflag": 0,
        "reanalysisversion": "2017.002",
        "radarlocations": [
            "boo",
            "ros",
            "emd",
            "hnr",
            "umd",
            "pro",
            "ess",
            "asd",
            "neu",
            "nhb",
            "oft",
            "tur",
            "isn",
            "fbg",
            "mem",
        ],
    }

    pz_header = (
        "PZ220704104101123BY 4923VS 1LV 6  1.0 19.0 28.0 37.0 46.0 55.0"
        "CO0CD0CS0MH12HI-32.0CI-32.0-32.0CL 0 0FL9999MS  0"
    )

    test_pz = {
        "producttype": "PZ",
        "datetime": datetime.datetime(2023, 11, 22, 7, 4),
        "radarid": "10410",
        "nrow": 200,
        "ncol": 200,
        "datasize": 4811,
        "formatversion": 1,
        "maxrange": "100 km",
        "message": "",
        "nlevel": 6,
        "level": np.array([1.0, 19.0, 28.0, 37.0, 46.0, 55.0]),
        "statisticfilter": "0",
        "cluttermap": "0",
        "dopplerfilter": "0",
        "maxheight": 12,
        "hailwarning": "-32.0",
        "severeconvection": [-32.0, -32.0],
        "severeconvectionheights": [0, 0],
        "freezing_level": "9999",
    }

    rx = io.radolan.parse_dwd_composite_header(rx_header)
    pg = io.radolan.parse_dwd_composite_header(pg_header)
    rq = io.radolan.parse_dwd_composite_header(rq_header)
    sq = io.radolan.parse_dwd_composite_header(sq_header)
    yw = io.radolan.parse_dwd_composite_header(yw_header)
    pz = io.radolan.parse_dwd_composite_header(pz_header)

    for key, value in rx.items():
        assert value == test_rx[key]

    def _check_product(data, test):
        for key, value in data.items():
            if isinstance(value, np.ndarray):
                np.testing.assert_allclose(value, test[key])
            else:
                assert value == test[key]

    _check_product(rx, test_rx)
    _check_product(pg, test_pg)
    _check_product(rq, test_rq)
    _check_product(sq, test_sq)
    _check_product(yw, test_yw)
    _check_product(pz, test_pz)


def test_read_radolan_composite():
    filename = "radolan/misc/raa01-rw_10000-1408030950-dwd---bin.gz"
    rw_file = get_wradlib_data_file(filename)
    test_attrs = {
        "maxrange": "150 km",
        "formatversion": 3,
        "radarlocations": [
            "boo",
            "ros",
            "emd",
            "hnr",
            "pro",
            "ess",
            "asd",
            "neu",
            "nhb",
            "oft",
            "tur",
            "isn",
            "fbg",
            "mem",
        ],
        "nrow": 900,
        "intervalseconds": 3600,
        "precision": 0.1,
        "datetime": datetime.datetime(2014, 8, 3, 9, 50),
        "ncol": 900,
        "radolanversion": "2.13.1",
        "producttype": "RW",
        "nodataflag": -9999,
        "datasize": 1620000,
        "radarid": "10000",
    }

    # test for complete file
    data, attrs = io.radolan.read_radolan_composite(rw_file)
    assert data.shape == (900, 900)

    for key, value in attrs.items():
        if isinstance(value, np.ndarray):
            assert value.dtype in [np.int32, np.int64]
        else:
            assert value == test_attrs[key]

    # Do the same for the case where a file handle is passed
    # instead of a file name
    with gzip.open(rw_file) as fh:
        data, attrs = io.radolan.read_radolan_composite(fh)
        assert data.shape == (900, 900)

    for key, value in attrs.items():
        if isinstance(value, np.ndarray):
            assert value.dtype in [np.int32, np.int64]
        else:
            assert value == test_attrs[key]

    # test for loaddata=False
    data, attrs = io.radolan.read_radolan_composite(rw_file, loaddata=False)
    assert data is None
    for key, value in attrs.items():
        if isinstance(value, np.ndarray):
            assert value.dtype == np.int64
        else:
            assert value == test_attrs[key]
    with pytest.raises(KeyError):
        attrs["nodataflag"]

    filename = "radolan/misc/raa01-rx_10000-1408102050-dwd---bin.gz"
    rx_file = get_wradlib_data_file(filename)
    data, attrs = io.radolan.read_radolan_composite(rx_file)

    filename = "radolan/misc/raa00-pc_10015-1408030905-dwd---bin.gz"
    pc_file = get_wradlib_data_file(filename)
    data, attrs = io.radolan.read_radolan_composite(pc_file, missing=255)


def test_read_radolan_composit_corrupted():
    filename = "radolan/misc/raa01-rw_10000-1408030950-dwd---bin.gz"
    rw_file = get_wradlib_data_file(filename)
    # Do the same for the case where a file handle is passed
    # instead of a file name
    with gzip.open(rw_file) as fh:
        fdata = sio.BytesIO(fh.read(20001))
        data, attrs = io.radolan.read_radolan_composite(fdata, fillmissing=True)
        assert data.shape == (900, 900)
        fh.seek(0)
        fdata = sio.BytesIO(fh.read(20002))
        data, attrs = io.radolan.read_radolan_composite(fdata, fillmissing=True)
        assert data.shape == (900, 900)

    filename = "radolan/misc/raa01-ex_10000-1408102050-dwd---bin.gz"
    ex_file = get_wradlib_data_file(filename)
    # Do the same for the case where a file handle is passed
    # instead of a file name
    with gzip.open(ex_file) as fh:
        fdata = sio.BytesIO(fh.read(20001))
        data, attrs = io.radolan.read_radolan_composite(fdata, fillmissing=True)
        assert data.shape == (1500, 1400)
        fh.seek(0)
        fdata = sio.BytesIO(fh.read(20002))
        data, attrs = io.radolan.read_radolan_composite(fdata, fillmissing=True)
        assert data.shape == (1500, 1400)

    filename = "radolan/misc/raa01-rx_10000-1408102050-dwd---bin.gz"
    rx_file = get_wradlib_data_file(filename)
    # Do the same for the case where a file handle is passed
    # instead of a file name
    with gzip.open(rx_file) as fh:
        fdata = sio.BytesIO(fh.read(20001))
        data, attrs = io.radolan.read_radolan_composite(fdata, fillmissing=True)
        assert data.shape == (900, 900)
        fh.seek(0)
        fdata = sio.BytesIO(fh.read(20002))
        data, attrs = io.radolan.read_radolan_composite(fdata, fillmissing=True)
        assert data.shape == (900, 900)

    filename = "radolan/misc/raa01-sf_10000-1305270050-dwd---bin.gz"
    sf_file = get_wradlib_data_file(filename)
    # Do the same for the case where a file handle is passed
    # instead of a file name
    with gzip.open(sf_file) as fh:
        fdata = sio.BytesIO(fh.read(20001))
        data, attrs = io.radolan.read_radolan_composite(fdata, fillmissing=True)
        assert data.shape == (900, 900)
        fh.seek(0)
        fdata = sio.BytesIO(fh.read(20002))
        data, attrs = io.radolan.read_radolan_composite(fdata, fillmissing=True)
        assert data.shape == (900, 900)


def test__radolan_file(file_or_filelike):
    filename = "radolan/misc/raa01-rw_10000-1408030950-dwd---bin.gz"
    test_attrs = {
        "maxrange": "150 km",
        "formatversion": 3,
        "radarlocations": [
            "boo",
            "ros",
            "emd",
            "hnr",
            "pro",
            "ess",
            "asd",
            "neu",
            "nhb",
            "oft",
            "tur",
            "isn",
            "fbg",
            "mem",
        ],
        "nrow": 900,
        "intervalseconds": 3600,
        "precision": 0.1,
        "datetime": datetime.datetime(2014, 8, 3, 9, 50),
        "ncol": 900,
        "radolanversion": "2.13.1",
        "producttype": "RW",
        "datasize": 1620000,
        "radarid": "10000",
    }
    with get_wradlib_data_file_or_filelike(filename, file_or_filelike) as rwfile:
        radfile = io.radolan._radolan_file(rwfile)
        assert radfile.dtype == np.uint16
        assert radfile.product == "RW"
        assert radfile.attrs == test_attrs
        assert radfile.data["RW"].shape == (900, 900)


def test_open_radolan_dataset():
    filename = "radolan/misc/raa01-rw_10000-1408030950-dwd---bin.gz"
    rw_file = get_wradlib_data_file(filename)

    # test for complete file
    data = io.radolan.open_radolan_dataset(rw_file)
    assert data.RW.shape == (900, 900)

    # Do the same for the case where a file handle is passed
    # instead of a file name
    with gzip.open(rw_file) as fh:
        data = io.radolan.open_radolan_dataset(fh)
        assert data.RW.shape == (900, 900)

    filename = "radolan/misc/raa01-rx_10000-1408102050-dwd---bin.gz"
    rx_file = get_wradlib_data_file(filename)
    data = io.radolan.open_radolan_dataset(rx_file)
    assert data.RX.shape == (900, 900)
    assert data.sizes == {"x": 900, "y": 900, "time": 1}
    assert data.RX.dims == ("y", "x")
    assert data.time.values == np.datetime64("2014-08-10T20:50:00.000000000")

    filename = "radolan/misc/raa00-pc_10015-1408030905-dwd---bin.gz"
    pc_file = get_wradlib_data_file(filename)
    data = io.radolan.open_radolan_dataset(pc_file)
    assert data.PG.shape == (460, 460)


@requires_dask
def test_open_radolan_mfdataset():
    filename = "radolan/misc/raa01-rw_10000-1408030950-dwd---bin.gz"
    rw_file = get_wradlib_data_file(filename)
    data = io.radolan.open_radolan_mfdataset(rw_file)
    assert data.RW.shape == (900, 900)
    filename2 = "radolan/misc/raa01-rw_10000-1408102050-dwd---bin.gz"
    # just fetching file
    get_wradlib_data_file(filename2)
    data = io.radolan.open_radolan_mfdataset(rw_file[:-23] + "*.gz", concat_dim="time")
    assert data.RW.shape == (2, 900, 900)
    assert data.sizes == {"x": 900, "y": 900, "time": 2}
    assert data.RW.dims == ("time", "y", "x")
    assert data.time[0].values == np.datetime64("2014-08-03T09:50:00.000000000")
    assert data.time[1].values == np.datetime64("2014-08-10T20:50:00.000000000")


@pytest.mark.parametrize("radfile", radolan_files())
def test_read_radolan_data_files(radfile):
    rfile = get_wradlib_data_file(radfile)
    data = io.radolan.open_radolan_dataset(rfile)
    assert isinstance(data, xr.Dataset)
    name = list(data.variables.keys())[0]
    var = data[name]
    assert isinstance(var, xr.DataArray)
    assert isinstance(var.values, np.ndarray)


@requires_xmltodict
def test_read_rainbow(file_or_filelike):
    filename = "rainbow/2013070308340000dBuZ.azi"
    with pytest.raises(IOError):
        io.rainbow.read_rainbow("test")
    # Test reading from filename or file-like object
    with get_wradlib_data_file_or_filelike(filename, file_or_filelike) as f:
        rb_dict = io.rainbow.read_rainbow(f)
    assert rb_dict["volume"]["@datetime"] == "2013-07-03T08:33:55"


@requires_xmltodict
def test_get_rb_blob_from_file(file_or_filelike):
    filename = "rainbow/2013070308340000dBuZ.azi"
    rb_file = get_wradlib_data_file(filename)
    rbdict = io.rainbow.read_rainbow(rb_file, loaddata=False)
    rbblob = rbdict["volume"]["scan"]["slice"]["slicedata"]["rawdata"]

    # Test reading from filename or file-like object
    with get_wradlib_data_file_or_filelike(filename, file_or_filelike) as f:
        data = io.rainbow.get_rb_blob_from_file(f, rbblob)
        assert data.shape[0] == int(rbblob["@rays"])
        assert data.shape[1] == int(rbblob["@bins"])

    with pytest.raises(IOError):
        io.rainbow.get_rb_blob_from_file("rb_fh", rbblob)


def test_get_rb_file_as_string():
    filename = "rainbow/2013070308340000dBuZ.azi"
    rb_file = get_wradlib_data_file(filename)
    with open(rb_file, "rb") as rb_fh:
        rb_string = io.rainbow.get_rb_file_as_string(rb_fh)
        assert rb_string
        with pytest.raises(IOError):
            io.rainbow.get_rb_file_as_string("rb_fh")


@requires_gdal
def test_gdal_create_dataset():
    testfunc = io.gdal.gdal_create_dataset
    tmp = tempfile.NamedTemporaryFile(mode="w+b").name
    with pytest.raises(TypeError):
        testfunc("AIG", tmp)
    from osgeo import gdal

    with pytest.raises(TypeError):
        testfunc("AAIGrid", tmp, cols=10, rows=10, bands=1, gdal_type=gdal.GDT_Float32)
    testfunc("GTiff", tmp, cols=10, rows=10, bands=1, gdal_type=gdal.GDT_Float32)
    testfunc(
        "GTiff",
        tmp,
        cols=10,
        rows=10,
        bands=1,
        gdal_type=gdal.GDT_Float32,
        remove=True,
    )


@requires_gdal
def test_write_raster_dataset():
    filename = "geo/bonn_new.tif"
    geofile = get_wradlib_data_file(filename)
    ds = io.gdal.open_raster(geofile)
    io.gdal.write_raster_dataset(geofile + "asc", ds, driver="AAIGrid")
    io.gdal.write_raster_dataset(geofile + "asc", ds, driver="AAIGrid", remove=True)
    with pytest.raises(TypeError):
        io.gdal.write_raster_dataset(geofile + "asc1", ds, driver="AIG")


@requires_gdal
def test_open_raster():
    filename = "geo/bonn_new.tif"
    geofile = get_wradlib_data_file(filename)
    io.gdal.open_raster(geofile, driver="GTiff")


@requires_gdal
def test_open_vector():
    get_wradlib_data_file("shapefiles/agger/agger_merge.dbf")
    get_wradlib_data_file("shapefiles/agger/agger_merge.shx")
    filename = "shapefiles/agger/agger_merge.shp"
    geofile = get_wradlib_data_file(filename)
    io.gdal.open_vector(geofile)
    io.gdal.open_vector(geofile, driver="ESRI Shapefile")


@pytest.fixture
def data_source():
    @dataclass(init=False, repr=False, eq=False)
    class Data:
        # create synthetic box
        box0 = np.array(
            [
                [2600000.0, 5630000.0],
                [2600000.0, 5640000.0],
                [2610000.0, 5640000.0],
                [2610000.0, 5630000.0],
                [2600000.0, 5630000.0],
            ]
        )

        box1 = np.array(
            [
                [2700000.0, 5630000.0],
                [2700000.0, 5640000.0],
                [2710000.0, 5640000.0],
                [2710000.0, 5630000.0],
                [2700000.0, 5630000.0],
            ]
        )

        data = np.array([box0, box1], dtype=object)

        ds = io.VectorSource(data)

        values1 = np.array([47.11, 47.11])
        values2 = np.array([47.11, 15.08])

    yield Data


@requires_geos
@requires_gdal
def test__check_src():
    get_wradlib_data_file("shapefiles/freiberger_mulde/freiberger_mulde.dbf")
    get_wradlib_data_file("shapefiles/freiberger_mulde/freiberger_mulde.shx")
    get_wradlib_data_file("shapefiles/freiberger_mulde/freiberger_mulde.prj")
    from osgeo import osr

    proj_gk2 = osr.SpatialReference()
    proj_gk2.ImportFromEPSG(31466)
    filename = get_wradlib_data_file("shapefiles/freiberger_mulde/freiberger_mulde.shp")

    assert len(io.VectorSource(filename, trg_crs=proj_gk2).data) == 430


@requires_geos
@requires_gdal
def test_error():
    get_wradlib_data_file("shapefiles/agger/agger_merge.dbf")
    get_wradlib_data_file("shapefiles/agger/agger_merge.shx")
    with pytest.raises(ValueError):
        filename = get_wradlib_data_file("shapefiles/agger/agger_merge.shp")
        io.VectorSource(filename)
    with pytest.raises(RuntimeError):
        io.VectorSource("test_zonalstats.py")


@requires_geos
@requires_gdal
def test_data(data_source):
    np.testing.assert_almost_equal(data_source.ds.data, data_source.data)


@requires_geos
@requires_gdal
def test__get_data(data_source):
    ds = io.VectorSource(data_source.data)
    np.testing.assert_almost_equal(ds._get_data(), data_source.data)


@requires_geos
@requires_gdal
def test_get_data_by_idx(data_source):
    ds = io.VectorSource(data_source.data)
    np.testing.assert_almost_equal(ds.get_data_by_idx([0]), data_source.data[0:1])
    np.testing.assert_almost_equal(ds.get_data_by_idx([1]), data_source.data[1:2])
    np.testing.assert_almost_equal(ds.get_data_by_idx([0, 1]), data_source.data)


@requires_geos
@requires_gdal
def test_get_data_by_att(data_source):
    ds = io.VectorSource(data_source.data)
    np.testing.assert_almost_equal(
        ds.get_data_by_att("index", 0), data_source.data[0:1]
    )
    np.testing.assert_almost_equal(
        ds.get_data_by_att("index", 1), data_source.data[1:2]
    )


@requires_geos
@requires_gdal
def test_get_data_by_geom(data_source):
    ds = io.VectorSource(data_source.data)
    lyr = ds.ds.GetLayer()
    lyr.ResetReading()
    lyr.SetSpatialFilter(None)
    lyr.SetAttributeFilter(None)
    for i, feature in enumerate(lyr):
        geom = feature.GetGeometryRef()
        np.testing.assert_almost_equal(
            ds.get_data_by_geom(geom), data_source.data[i : i + 1]
        )


@requires_geos
@requires_gdal
def test_set_attribute(data_source):
    ds = io.VectorSource(data_source.data)
    ds.set_attribute("test", data_source.values1)
    assert np.allclose(ds.get_attributes(["test"]), data_source.values1)
    ds.set_attribute("test", data_source.values2)
    assert np.allclose(ds.get_attributes(["test"]), data_source.values2)


@requires_geos
@requires_gdal
def test_get_attributes(data_source):
    ds = io.VectorSource(data_source.data)
    ds.set_attribute("test", data_source.values2)
    assert ds.get_attributes(["test"], filt=("index", 0)) == data_source.values2[0]
    assert ds.get_attributes(["test"], filt=("index", 1)) == data_source.values2[1]


@requires_geos
@requires_gdal
def test_get_geom_properties():
    get_wradlib_data_file("shapefiles/freiberger_mulde/freiberger_mulde.dbf")
    get_wradlib_data_file("shapefiles/freiberger_mulde/freiberger_mulde.shx")
    get_wradlib_data_file("shapefiles/freiberger_mulde/freiberger_mulde.prj")

    filename = get_wradlib_data_file("shapefiles/freiberger_mulde/freiberger_mulde.shp")
    test = io.VectorSource(filename)
    np.testing.assert_allclose(
        [[4636921.625003308]],
        test.get_geom_properties(["Area"], filt=("FID", 1)),
        atol=5e-8,
        rtol=1e-14,
    )


@requires_geos
@requires_gdal
def test_dump_vector(data_source):
    ds = io.VectorSource(data_source.data)
    ds.dump_vector(tempfile.NamedTemporaryFile(mode="w+b").name)


@requires_geos
@requires_gdal
def test_clean_up_temporary_files(data_source):
    ds = io.VectorSource(data_source.data)
    tempdir = ds.ds.GetDescription()
    assert os.path.exists(tempdir)
    ds.close()
    assert not os.path.exists(tempdir)


@requires_geos
@requires_gdal
def test_dump_raster():
    get_wradlib_data_file("shapefiles/freiberger_mulde/freiberger_mulde.dbf")
    get_wradlib_data_file("shapefiles/freiberger_mulde/freiberger_mulde.shx")
    get_wradlib_data_file("shapefiles/freiberger_mulde/freiberger_mulde.prj")

    filename = get_wradlib_data_file("shapefiles/freiberger_mulde/freiberger_mulde.shp")
    test = io.VectorSource(filename)
    test.dump_raster(
        tempfile.NamedTemporaryFile(mode="w+b").name,
        driver="netCDF",
        pixel_size=100.0,
    )
    test.dump_raster(
        tempfile.NamedTemporaryFile(mode="w+b").name,
        driver="netCDF",
        pixel_size=100.0,
        attr="FID",
    )


def test_open_iris_cartesian_product():
    filename = "sigmet/SUR160703220000.MAX71NP.gz"
    with get_wradlib_data_file_or_filelike(filename, "filelike") as sigmetfile:
        data = io.iris.IrisCartesianProductFile(
            sigmetfile, loaddata=True, origin="lower"
        )
    assert isinstance(data.rh, io.iris.xiris.IrisRecord)
    assert isinstance(data.fh, (np.memmap, np.ndarray))


def test_read_iris(file_or_filelike):
    filename = "sigmet/cor-main131125105503.RAW2049"
    with get_wradlib_data_file_or_filelike(filename, file_or_filelike) as sigmetfile:
        data = io.iris.read_iris(
            sigmetfile, loaddata=True, rawdata=True, keep_old_sweep_data=False
        )
    data_keys = [
        "product_hdr",
        "product_type",
        "ingest_header",
        "nsweeps",
        "nrays",
        "nbins",
        "data_types",
        "data",
        "raw_product_bhdrs",
    ]
    product_hdr_keys = ["structure_header", "product_configuration", "product_end"]
    ingest_hdr_keys = [
        "structure_header",
        "ingest_configuration",
        "task_configuration",
        "spare_0",
        "gparm",
        "reserved",
    ]
    data_types = [
        "DB_DBZ",
        "DB_VEL",
        "DB_ZDR",
        "DB_KDP",
        "DB_PHIDP",
        "DB_RHOHV",
        "DB_HCLASS",
    ]
    assert list(data.keys()) == data_keys
    assert list(data["product_hdr"].keys()) == product_hdr_keys
    assert list(data["ingest_header"].keys()) == ingest_hdr_keys
    assert data["data_types"] == data_types

    data_types = ["DB_DBZ", "DB_VEL"]
    selected_data = [1, 3, 8]
    loaddata = {"moment": data_types, "sweep": selected_data}

    with get_wradlib_data_file_or_filelike(filename, file_or_filelike) as sigmetfile:
        data = io.iris.read_iris(
            sigmetfile, loaddata=loaddata, rawdata=True, keep_old_sweep_data=False
        )
    assert not set(data_types) - set(data["data"][1]["sweep_data"])
    assert set(data["data"]) == set(selected_data)


@pytest.mark.skipif(sys.platform.startswith("win"), reason="flaky windows")
@requires_netcdf
def test_read_edge_netcdf(file_or_filelike):
    filename = "netcdf/edge_netcdf.nc"
    with get_wradlib_data_file_or_filelike(filename, file_or_filelike) as f:
        data, attrs = io.netcdf.read_edge_netcdf(f)
    with get_wradlib_data_file_or_filelike(filename, file_or_filelike) as f:
        data, attrs = io.netcdf.read_edge_netcdf(f, enforce_equidist=True)

    filename = "netcdf/cfrad.20080604_002217_000_SPOL_v36_SUR.nc"
    with get_wradlib_data_file_or_filelike(filename, file_or_filelike) as f:
        with pytest.raises(AttributeError):
            io.netcdf.read_edge_netcdf(f)
    with pytest.raises(FileNotFoundError):
        io.netcdf.read_edge_netcdf("test_read_edge_netcdf.nc")


@requires_netcdf
def test_read_generic_netcdf(file_or_filelike):
    filename = "netcdf/cfrad.20080604_002217_000_SPOL_v36_SUR.nc"
    with get_wradlib_data_file_or_filelike(filename, file_or_filelike) as f:
        io.netcdf.read_generic_netcdf(f)
    with pytest.raises(IOError):
        io.netcdf.read_generic_netcdf("test")

    filename = "sigmet/cor-main131125105503.RAW2049"
    with get_wradlib_data_file_or_filelike(filename, file_or_filelike) as f:
        with pytest.raises(IOError):
            io.netcdf.read_generic_netcdf(f)

    filename = "hdf5/IDR66_20100206_111233.vol.h5"
    with get_wradlib_data_file_or_filelike(filename, file_or_filelike) as f:
        io.netcdf.read_generic_netcdf(f)

    filename = "netcdf/example_cfradial_ppi.nc"
    with get_wradlib_data_file_or_filelike(filename, file_or_filelike) as f:
        io.netcdf.read_generic_netcdf(f)


def test_get_srtm_tile_names():
    t0 = ["N51W001", "N51E000", "N51E001", "N52W001", "N52E000", "N52E001"]
    t1 = ["N38W029", "N38W028", "N39W029", "N39W028"]
    t2 = ["N38W029"]
    t3 = ["S02E015", "S02E016", "S01E015", "S01E016", "N00E015", "N00E016"]
    targets = [t0, t1, t2, t3]

    e0 = [-0.3, 1.5, 51.4, 52.5]
    e1 = [-28.5, -27.5, 38.5, 39.5]
    e2 = [-28.5, -28.2, 38.2, 38.5]
    e3 = [15.3, 16.6, -1.4, 0.4]
    extent = [e0, e1, e2, e3]
    for t, e in zip(targets, extent):
        filelist = io.dem.get_srtm_tile_names(e)
        assert t == filelist


@requires_secrets
@requires_gdal
@pytest.mark.xfail(strict=False)
def test_get_srtm(mock_wradlib_data_env):
    targets = ["N38W029", "N38W028", "N39W029", "N39W028"]
    targets = [f"{f}.SRTMGL3.hgt.zip" for f in targets]

    extent = [-28.5, -27.5, 38.5, 39.5]
    datasets = io.dem.get_srtm(extent, merge=False)
    filelist = [os.path.basename(d.GetFileList()[0]) for d in datasets]
    assert targets == filelist

    merged = io.dem.get_srtm(extent)

    xsize = (datasets[0].RasterXSize - 1) * 2 + 1
    ysize = (datasets[0].RasterXSize - 1) * 2 + 1
    assert merged.RasterXSize == xsize
    assert merged.RasterYSize == ysize

    geo = merged.GetGeoTransform()
    resolution = 3 / 3600
    ulcx = -29 - resolution / 2
    ulcy = 40 + resolution / 2
    geo_ref = [ulcx, resolution, 0, ulcy, 0, -resolution]
    np.testing.assert_array_almost_equal(geo, geo_ref)


@requires_data_folder
@requires_gdal
def test_get_srtm_offline():
    targets = ["N38W029", "N38W028", "N39W029", "N39W028"]
    targets = [f"{f}.SRTMGL3.hgt.zip" for f in targets]

    # retrieve need files for offline test
    for f in targets:
        wradlib_data.DATASETS.fetch("geo/" + f)

    extent = [-28.5, -27.5, 38.5, 39.5]
    datasets = io.dem.get_srtm(extent, merge=False)
    filelist = [os.path.basename(d.GetFileList()[0]) for d in datasets]
    assert targets == filelist

    merged = io.dem.get_srtm(extent)

    xsize = (datasets[0].RasterXSize - 1) * 2 + 1
    ysize = (datasets[0].RasterXSize - 1) * 2 + 1
    assert merged.RasterXSize == xsize
    assert merged.RasterYSize == ysize

    geo = merged.GetGeoTransform()
    resolution = 3 / 3600
    ulcx = -29 - resolution / 2
    ulcy = 40 + resolution / 2
    geo_ref = [ulcx, resolution, 0, ulcy, 0, -resolution]
    np.testing.assert_array_almost_equal(geo, geo_ref)
