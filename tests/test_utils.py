"""
Unit tests for the esapp.utils module.

These are **unit tests** that do NOT require PowerWorld Simulator. They test
B3D file format I/O (esapp.utils.b3d).

USAGE:
    pytest tests/test_utils.py -v
    pytest tests/test_utils.py -v --cov=esapp/utils --cov-report=term-missing
"""

import struct

import numpy as np
import pytest
from numpy.testing import assert_allclose

from esapp.utils.b3d import B3D


# =============================================================================
# B3D file format
# =============================================================================


class TestB3D:

    def test_default_construction(self):
        b = B3D()
        assert b.lat.shape == (4,)
        assert b.lon.shape == (4,)
        assert b.time.shape == (3,)
        assert b.ex.shape == (3, 4)
        assert b.ey.shape == (3, 4)

    def test_write_load_roundtrip(self, tmp_path):
        b = B3D()
        fpath = str(tmp_path / "test.b3d")
        b.write_b3d_file(fpath)

        b2 = B3D(fpath)
        assert_allclose(b2.lat, b.lat)
        assert_allclose(b2.lon, b.lon)
        assert_allclose(b2.time, b.time)
        assert_allclose(b2.ex, b.ex)
        assert_allclose(b2.ey, b.ey)
        assert b2.comment == b.comment

    def test_from_mesh_and_roundtrip(self, tmp_path):
        long = np.array([-85.0, -84.5])
        lat = np.array([30.5, 31.0])
        ex = np.ones((2, 2), dtype=np.float32) * 0.5
        ey = np.ones((2, 2), dtype=np.float32) * -0.3

        b = B3D.from_mesh(long, lat, ex, ey, comment="Test")
        assert b.comment == "Test"
        assert b.grid_dim == [2, 2]

        fpath = str(tmp_path / "mesh.b3d")
        b.write_b3d_file(fpath)
        b2 = B3D(fpath)
        assert_allclose(b2.ex, b.ex, atol=1e-6)
        assert_allclose(b2.ey, b.ey, atol=1e-6)

    def test_write_validation_lat_lon_mismatch(self, tmp_path):
        b = B3D()
        b.lon = np.array([1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="lat and lon must have the same length"):
            b.write_b3d_file(str(tmp_path / "bad.b3d"))

    def test_write_validation_bad_lat_dtype(self, tmp_path):
        b = B3D()
        b.lat = b.lat.astype(np.float32)
        with pytest.raises(ValueError, match="lat must be a float64"):
            b.write_b3d_file(str(tmp_path / "bad.b3d"))

    def test_write_validation_bad_lon_dtype(self, tmp_path):
        b = B3D()
        b.lon = b.lon.astype(np.float32)
        with pytest.raises(ValueError, match="lon must be a float64"):
            b.write_b3d_file(str(tmp_path / "bad.b3d"))

    def test_write_validation_bad_time_dtype(self, tmp_path):
        b = B3D()
        b.time = b.time.astype(np.int32)
        with pytest.raises(ValueError, match="time must be a uint32"):
            b.write_b3d_file(str(tmp_path / "bad.b3d"))

    def test_write_validation_bad_ex_dtype(self, tmp_path):
        b = B3D()
        b.ex = b.ex.astype(np.float64)
        with pytest.raises(ValueError, match="ex must be a float32"):
            b.write_b3d_file(str(tmp_path / "bad.b3d"))

    def test_write_validation_bad_ey_dtype(self, tmp_path):
        b = B3D()
        b.ey = b.ey.astype(np.float64)
        with pytest.raises(ValueError, match="ey must be a float32"):
            b.write_b3d_file(str(tmp_path / "bad.b3d"))

    def test_write_validation_ex_shape_mismatch(self, tmp_path):
        b = B3D()
        b.ex = np.zeros((3, 5), dtype=np.float32)
        with pytest.raises(ValueError, match="ex columns"):
            b.write_b3d_file(str(tmp_path / "bad.b3d"))

    def test_write_validation_ey_shape_mismatch(self, tmp_path):
        b = B3D()
        b.ey = np.zeros((3, 5), dtype=np.float32)
        with pytest.raises(ValueError, match="ey columns"):
            b.write_b3d_file(str(tmp_path / "bad.b3d"))

    def test_write_validation_ex_rows_mismatch(self, tmp_path):
        b = B3D()
        b.ex = np.zeros((5, 4), dtype=np.float32)
        with pytest.raises(ValueError, match="ex rows"):
            b.write_b3d_file(str(tmp_path / "bad.b3d"))

    def test_write_validation_ey_rows_mismatch(self, tmp_path):
        b = B3D()
        b.ey = np.zeros((5, 4), dtype=np.float32)
        with pytest.raises(ValueError, match="ey rows"):
            b.write_b3d_file(str(tmp_path / "bad.b3d"))

    def test_load_no_meta_strings(self, tmp_path):
        """B3D file with nmeta=0 triggers 'No comment' branch."""
        b = B3D()
        fpath = str(tmp_path / "test.b3d")
        b.write_b3d_file(fpath)

        # Patch the file: set nmeta=0 and remove meta string bytes.
        # Easier approach: build a raw file from scratch.
        fpath2 = str(tmp_path / "nometa.b3d")
        n = 1  # 1 location
        nt = 1  # 1 time step
        with open(fpath2, "wb") as f:
            _w = lambda val: f.write(val.to_bytes(4, "little"))
            _w(34280)  # code
            _w(4)      # version
            _w(0)      # nmeta = 0
            _w(2)      # float_channels
            _w(0)      # byte_channels
            _w(1)      # loc_format
            _w(n)      # n locations
            # Location data: lon, lat, z for each point
            loc = np.array([[0.0, 0.0, 0.0]], dtype=np.float64)
            f.write(loc.tobytes())
            _w(0)   # time_0
            _w(0)   # time_units
            _w(0)   # time_offset
            _w(0)   # time_step (variable)
            _w(nt)  # nt
            f.write(np.array([0], dtype=np.uint32).tobytes())
            # ex, ey interleaved: [ex0, ey0]
            f.write(np.zeros(2, dtype=np.float32).tobytes())

        b2 = B3D(fpath2)
        assert b2.comment == "No comment"

    def test_load_one_meta_string(self, tmp_path):
        """B3D with nmeta=1 skips grid_dim parsing (line 230->242 branch)."""
        fpath = str(tmp_path / "onemeta.b3d")
        n = 1
        nt = 1
        meta = "Only comment\x00"
        with open(fpath, "wb") as f:
            _w = lambda val: f.write(val.to_bytes(4, "little"))
            _w(34280); _w(4)
            _w(1)  # nmeta = 1
            f.write(meta.encode('ascii'))
            _w(2); _w(0); _w(1); _w(n)
            f.write(np.zeros((n, 3), dtype=np.float64).tobytes())
            _w(0); _w(0); _w(0); _w(0); _w(nt)
            f.write(np.array([0], dtype=np.uint32).tobytes())
            f.write(np.zeros(n * 2, dtype=np.float32).tobytes())

        b = B3D(fpath)
        assert b.comment == "Only comment"
        # grid_dim stays [0,0] since nmeta < 2, then product != n → [n, 1]
        assert b.grid_dim == [n, 1]

    def test_load_grid_dim_space_separated(self, tmp_path):
        """B3D with grid_dim meta using space-separated format."""
        fpath = str(tmp_path / "spacedim.b3d")
        n = 2
        nt = 1
        meta = "Test comment\x002 1\x00"  # space-separated grid_dim
        with open(fpath, "wb") as f:
            _w = lambda val: f.write(val.to_bytes(4, "little"))
            _w(34280); _w(4)
            _w(2)  # nmeta = 2
            f.write(meta.encode('ascii'))
            _w(2); _w(0); _w(1); _w(n)
            loc = np.zeros((n, 3), dtype=np.float64)
            f.write(loc.tobytes())
            _w(0); _w(0); _w(0); _w(0); _w(nt)
            f.write(np.array([0], dtype=np.uint32).tobytes())
            f.write(np.zeros(n * 2, dtype=np.float32).tobytes())

        b = B3D(fpath)
        assert b.grid_dim == [2, 1]

    def test_load_grid_dim_bad_format(self, tmp_path):
        """B3D with unparseable grid_dim falls back to [0, 0]."""
        fpath = str(tmp_path / "baddim.b3d")
        n = 2
        nt = 1
        meta = "Test\x00not_a_dim\x00"
        with open(fpath, "wb") as f:
            _w = lambda val: f.write(val.to_bytes(4, "little"))
            _w(34280); _w(4)
            _w(2)  # nmeta = 2
            f.write(meta.encode('ascii'))
            _w(2); _w(0); _w(1); _w(n)
            loc = np.zeros((n, 3), dtype=np.float64)
            f.write(loc.tobytes())
            _w(0); _w(0); _w(0); _w(0); _w(nt)
            f.write(np.array([0], dtype=np.uint32).tobytes())
            f.write(np.zeros(n * 2, dtype=np.float32).tobytes())

        b = B3D(fpath)
        # grid_dim falls back to [0,0], then product != n so becomes [n, 1]
        assert b.grid_dim == [n, 1]

    def test_load_grid_dim_wrong_length(self, tmp_path):
        """B3D with grid_dim having !=2 elements triggers ValueError fallback."""
        fpath = str(tmp_path / "wrongdim.b3d")
        n = 2
        nt = 1
        meta = "Test\x001, 2, 3\x00"  # 3 elements
        with open(fpath, "wb") as f:
            _w = lambda val: f.write(val.to_bytes(4, "little"))
            _w(34280); _w(4)
            _w(2)
            f.write(meta.encode('ascii'))
            _w(2); _w(0); _w(1); _w(n)
            loc = np.zeros((n, 3), dtype=np.float64)
            f.write(loc.tobytes())
            _w(0); _w(0); _w(0); _w(0); _w(nt)
            f.write(np.array([0], dtype=np.uint32).tobytes())
            f.write(np.zeros(n * 2, dtype=np.float32).tobytes())

        b = B3D(fpath)
        assert b.grid_dim == [n, 1]

    def test_load_float_channels_too_few(self, tmp_path):
        """B3D with float_channels < 2 raises IOError."""
        fpath = str(tmp_path / "fewchan.b3d")
        meta = "Test\x00[2, 1]\x00"
        with open(fpath, "wb") as f:
            _w = lambda val: f.write(val.to_bytes(4, "little"))
            _w(34280); _w(4)
            _w(2)
            f.write(meta.encode('ascii'))
            _w(1)  # float_channels = 1 (too few)
            _w(0); _w(1); _w(2)
            f.write(b'\x00' * 200)

        with pytest.raises(IOError, match="at least 2 float channels"):
            B3D(fpath)

    def test_load_bad_loc_format(self, tmp_path):
        """B3D with loc_format != 1 raises IOError."""
        fpath = str(tmp_path / "badloc.b3d")
        meta = "Test\x00[2, 1]\x00"
        with open(fpath, "wb") as f:
            _w = lambda val: f.write(val.to_bytes(4, "little"))
            _w(34280); _w(4)
            _w(2)
            f.write(meta.encode('ascii'))
            _w(2); _w(0)
            _w(0)  # loc_format = 0 (unsupported)
            _w(2)
            f.write(b'\x00' * 200)

        with pytest.raises(IOError, match="Only location format 1 is supported"):
            B3D(fpath)

    def test_load_nonzero_time_step(self, tmp_path):
        """B3D with time_step != 0 raises IOError."""
        fpath = str(tmp_path / "fixedtime.b3d")
        n = 1
        meta = "Test\x00[1, 1]\x00"
        with open(fpath, "wb") as f:
            _w = lambda val: f.write(val.to_bytes(4, "little"))
            _w(34280); _w(4)
            _w(2)
            f.write(meta.encode('ascii'))
            _w(2); _w(0); _w(1); _w(n)
            f.write(np.zeros((n, 3), dtype=np.float64).tobytes())
            _w(0); _w(0); _w(0)
            _w(100)  # time_step != 0
            _w(1)
            f.write(b'\x00' * 200)

        with pytest.raises(IOError, match="variable time points"):
            B3D(fpath)

    def test_load_extra_channels(self, tmp_path):
        """B3D with extra float/byte channels uses the extraction loop."""
        fpath = str(tmp_path / "extrachan.b3d")
        n = 1
        nt = 1
        float_channels = 3  # 3 floats per point (ex, ey, extra)
        byte_channels = 1   # 1 extra byte per point
        meta = "Test\x00[1, 1]\x00"
        with open(fpath, "wb") as f:
            _w = lambda val: f.write(val.to_bytes(4, "little"))
            _w(34280); _w(4)
            _w(2)
            f.write(meta.encode('ascii'))
            _w(float_channels); _w(byte_channels); _w(1); _w(n)
            f.write(np.zeros((n, 3), dtype=np.float64).tobytes())
            _w(0); _w(0); _w(0); _w(0); _w(nt)
            f.write(np.array([0], dtype=np.uint32).tobytes())
            # Data: 3 floats + 1 byte per point per timestep
            ex_val = np.float32(1.5)
            ey_val = np.float32(-0.5)
            extra_val = np.float32(0.0)
            f.write(struct.pack('<fff', ex_val, ey_val, extra_val))
            f.write(b'\x00')  # 1 byte channel

        b = B3D(fpath)
        assert_allclose(b.ex[0, 0], 1.5, atol=1e-5)
        assert_allclose(b.ey[0, 0], -0.5, atol=1e-5)

    def test_load_grid_dim_product_mismatch(self, tmp_path):
        """When grid_dim product != n, grid_dim is reset to [n, 1]."""
        fpath = str(tmp_path / "mismatch.b3d")
        n = 3
        nt = 1
        # grid_dim says 2x2=4 but we have n=3 points
        meta = "Test\x00[2, 2]\x00"
        with open(fpath, "wb") as f:
            _w = lambda val: f.write(val.to_bytes(4, "little"))
            _w(34280); _w(4)
            _w(2)
            f.write(meta.encode('ascii'))
            _w(2); _w(0); _w(1); _w(n)
            f.write(np.zeros((n, 3), dtype=np.float64).tobytes())
            _w(0); _w(0); _w(0); _w(0); _w(nt)
            f.write(np.array([0], dtype=np.uint32).tobytes())
            f.write(np.zeros(n * 2, dtype=np.float32).tobytes())

        b = B3D(fpath)
        assert b.grid_dim == [3, 1]

    def test_load_invalid_code(self, tmp_path):
        fpath = str(tmp_path / "bad.b3d")
        with open(fpath, "wb") as f:
            f.write((0).to_bytes(4, "little"))
            f.write(b'\x00' * 100)
        with pytest.raises(IOError, match="Invalid B3D file"):
            B3D(fpath)

    def test_load_invalid_version(self, tmp_path):
        fpath = str(tmp_path / "badver.b3d")
        with open(fpath, "wb") as f:
            f.write((34280).to_bytes(4, "little"))
            f.write((99).to_bytes(4, "little"))
            f.write(b'\x00' * 100)
        with pytest.raises(IOError, match="Unsupported B3D version"):
            B3D(fpath)

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main(["-v", __file__]))
