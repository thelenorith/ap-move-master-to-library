# Generated-by: Claude Code (Claude Sonnet 4.5)
"""
Tests for the move_calibration module.
"""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock

from ap_move_master_to_library.move_calibration import (
    build_destination_path,
    copy_calibration_frames,
    _build_filename,
    _build_bias_path,
    _build_dark_path,
    _build_flat_path,
    _check_for_collisions,
)

# Tests for destination path building


def test_build_destination_path_bias():
    """Test building destination path for BIAS frames."""
    datum = {
        "type": "MASTER BIAS",
        "camera": "DWARFIII",
        "gain": 100,
        "offset": 10,
        "settemp": -10,
        "readoutmode": "Normal",
    }

    dest_path = build_destination_path(
        source_file="test.xisf",
        dest_dir="/dest",
        datum=datum,
    )

    # Check path structure
    assert "MASTER BIAS" in dest_path
    assert "DWARFIII" in dest_path
    assert "masterBias" in dest_path
    assert "GAIN_100" in dest_path
    assert "OFFSET_10" in dest_path
    assert ".xisf" in dest_path


def test_build_destination_path_dark():
    """Test building destination path for DARK frames."""
    datum = {
        "type": "MASTER DARK",
        "camera": "DWARFIII",
        "exposureseconds": 300,
        "gain": 100,
        "offset": 10,
        "settemp": -10,
    }

    dest_path = build_destination_path(
        source_file="test.fits",
        dest_dir="/dest",
        datum=datum,
    )

    # Check path structure
    assert "MASTER DARK" in dest_path
    assert "DWARFIII" in dest_path
    assert "masterDark" in dest_path
    # Check for exposure time in filename (denormalize_header may return different values)
    assert "_300_" in dest_path  # Exposure value should be in filename
    assert "GAIN_100" in dest_path
    assert ".fits" in dest_path


def test_build_destination_path_flat():
    """Test building destination path for FLAT frames."""
    datum = {
        "type": "MASTER FLAT",
        "camera": "DWARFIII",
        "optic": "REDCAT51",
        "date": "2026-01-27",
        "filter": "L",
        "gain": 100,
        "offset": 10,
    }

    dest_path = build_destination_path(
        source_file="test.xisf",
        dest_dir="/dest",
        datum=datum,
    )

    # Check path structure
    assert "MASTER FLAT" in dest_path
    assert "DWARFIII" in dest_path
    assert "REDCAT51" in dest_path
    assert "DATE_2026-01-27" in dest_path
    assert "masterFlat" in dest_path
    assert "FILTER_L" in dest_path
    assert ".xisf" in dest_path
    # Date should NOT be in filename (only in directory)
    assert dest_path.count("2026-01-27") == 1


def test_build_destination_path_flat_no_optic():
    """Test building destination path for FLAT frames without optic."""
    datum = {
        "type": "MASTER FLAT",
        "camera": "DWARFIII",
        "date": "2026-01-27",
        "filter": "L",
        "gain": 100,
    }

    dest_path = build_destination_path(
        source_file="test.xisf",
        dest_dir="/dest",
        datum=datum,
    )

    # Check path structure - optic should not be in path
    assert "MASTER FLAT" in dest_path
    assert "DWARFIII" in dest_path
    assert "DATE_2026-01-27" in dest_path
    # Ensure path is camera -> DATE (no optic in between)
    path_parts = dest_path.split(os.sep)
    # Find indices of camera and DATE
    camera_idx = None
    date_idx = None
    for i, part in enumerate(path_parts):
        if "DWARFIII" in part:
            camera_idx = i
        if "DATE_" in part:
            date_idx = i
    assert camera_idx is not None
    assert date_idx is not None
    # DATE should immediately follow camera (no optic in between)
    assert date_idx == camera_idx + 1


def test_build_destination_path_missing_camera():
    """Test that missing camera raises ValueError."""
    datum = {
        "type": "MASTER BIAS",
        "gain": 100,
    }

    with pytest.raises(ValueError, match="Missing required 'camera' metadata"):
        build_destination_path(
            source_file="test.xisf",
            dest_dir="/dest",
            datum=datum,
        )


def test_build_destination_path_missing_date_for_flat():
    """Test that missing date for FLAT raises ValueError."""
    datum = {
        "type": "MASTER FLAT",
        "camera": "DWARFIII",
        "filter": "L",
    }

    with pytest.raises(ValueError, match="Missing required 'date' metadata"):
        build_destination_path(
            source_file="test.xisf",
            dest_dir="/dest",
            datum=datum,
        )


def test_build_destination_path_unknown_type():
    """Test that unknown frame type raises ValueError."""
    datum = {
        "type": "MASTER UNKNOWN",
        "camera": "DWARFIII",
    }

    with pytest.raises(ValueError, match="Unknown frame type"):
        build_destination_path(
            source_file="test.xisf",
            dest_dir="/dest",
            datum=datum,
        )


def test_build_destination_path_dark_exposure_first():
    """Test that DARK frames have exposure time first in filename."""
    datum = {
        "type": "MASTER DARK",
        "camera": "DWARFIII",
        "exposureseconds": 300,
        "gain": 100,
        "offset": 10,
    }

    dest_path = build_destination_path(
        source_file="test.xisf",
        dest_dir="/dest",
        datum=datum,
    )

    # Extract filename from path
    filename = os.path.basename(dest_path)
    # Exposure time should appear before gain in filename
    # Pattern: masterDark_EXPTIME_300_GAIN_100_...
    exp_pos = filename.find("300")
    gain_pos = filename.find("100")
    assert exp_pos > 0, "Exposure time not found in filename"
    assert gain_pos > 0, "Gain not found in filename"
    assert exp_pos < gain_pos, "Exposure time must appear before gain in filename"


def test_build_destination_path_missing_optional_properties():
    """Test that missing optional properties are skipped in filename."""
    # BIAS with only required camera and minimal properties
    datum = {
        "type": "MASTER BIAS",
        "camera": "DWARFIII",
        "gain": 100,
        # No offset, settemp, readoutmode
    }

    dest_path = build_destination_path(
        source_file="test.xisf",
        dest_dir="/dest",
        datum=datum,
    )

    # Should have gain but not have offset
    assert "GAIN_100" in dest_path
    assert "OFFSET" not in dest_path
    # Should still be valid path with camera directory
    assert "DWARFIII" in dest_path


def test_build_destination_path_file_extension_preservation():
    """Test that file extensions are preserved correctly."""
    datum = {
        "type": "MASTER BIAS",
        "camera": "DWARFIII",
        "gain": 100,
    }

    # Test .xisf extension
    dest_path_xisf = build_destination_path(
        source_file="test.xisf",
        dest_dir="/dest",
        datum=datum,
    )
    assert dest_path_xisf.endswith(".xisf")

    # Test .fits extension
    dest_path_fits = build_destination_path(
        source_file="test.fits",
        dest_dir="/dest",
        datum=datum,
    )
    assert dest_path_fits.endswith(".fits")

    # Test .FIT extension (uppercase)
    dest_path_fit = build_destination_path(
        source_file="test.FIT",
        dest_dir="/dest",
        datum=datum,
    )
    assert dest_path_fit.endswith(".FIT")


def test_build_destination_path_flat_empty_optic():
    """Test that empty string optic is treated same as None (no optic directory)."""
    datum = {
        "type": "MASTER FLAT",
        "camera": "DWARFIII",
        "optic": "",  # Empty string
        "date": "2026-01-27",
        "filter": "L",
    }

    dest_path = build_destination_path(
        source_file="test.xisf",
        dest_dir="/dest",
        datum=datum,
    )

    # Should not have optic in path
    path_parts = dest_path.split(os.sep)
    camera_idx = None
    date_idx = None
    for i, part in enumerate(path_parts):
        if "DWARFIII" in part:
            camera_idx = i
        if "DATE_" in part:
            date_idx = i

    assert camera_idx is not None
    assert date_idx is not None
    # DATE should immediately follow camera (no optic directory)
    assert date_idx == camera_idx + 1


def test_build_destination_path_directory_structure():
    """Test that directory structure is correct for each frame type."""
    # BIAS: dest_dir/MASTER BIAS/camera/filename
    bias_datum = {
        "type": "MASTER BIAS",
        "camera": "DWARFIII",
        "gain": 100,
    }
    bias_path = build_destination_path(
        source_file="test.xisf",
        dest_dir="/dest",
        datum=bias_datum,
    )
    bias_parts = bias_path.split(os.sep)
    assert "dest" in bias_parts
    assert "MASTER BIAS" in bias_parts
    assert "DWARFIII" in bias_parts
    # Verify order: dest -> MASTER BIAS -> camera -> filename
    dest_idx = next(i for i, p in enumerate(bias_parts) if "dest" in p)
    bias_idx = next(i for i, p in enumerate(bias_parts) if p == "MASTER BIAS")
    camera_idx = next(i for i, p in enumerate(bias_parts) if "DWARFIII" in p)
    assert dest_idx < bias_idx < camera_idx

    # DARK: dest_dir/MASTER DARK/camera/filename
    dark_datum = {
        "type": "MASTER DARK",
        "camera": "DWARFIII",
        "exposureseconds": 300,
    }
    dark_path = build_destination_path(
        source_file="test.xisf",
        dest_dir="/dest",
        datum=dark_datum,
    )
    dark_parts = dark_path.split(os.sep)
    assert "MASTER DARK" in dark_parts
    assert "DWARFIII" in dark_parts

    # FLAT: dest_dir/MASTER FLAT/camera/DATE_date/filename
    flat_datum = {
        "type": "MASTER FLAT",
        "camera": "DWARFIII",
        "date": "2026-01-27",
        "filter": "L",
    }
    flat_path = build_destination_path(
        source_file="test.xisf",
        dest_dir="/dest",
        datum=flat_datum,
    )
    flat_parts = flat_path.split(os.sep)
    assert "MASTER FLAT" in flat_parts
    assert "DWARFIII" in flat_parts
    assert any("DATE_" in p for p in flat_parts)
    # Verify order: dest -> MASTER FLAT -> camera -> DATE_xxx -> filename
    dest_idx = next(i for i, p in enumerate(flat_parts) if "dest" in p)
    flat_idx = next(i for i, p in enumerate(flat_parts) if p == "MASTER FLAT")
    camera_idx = next(i for i, p in enumerate(flat_parts) if "DWARFIII" in p)
    date_idx = next(i for i, p in enumerate(flat_parts) if "DATE_" in p)
    assert dest_idx < flat_idx < camera_idx < date_idx


def test_build_destination_path_flat_with_optic_structure():
    """Test that FLAT with optic has correct directory structure."""
    datum = {
        "type": "MASTER FLAT",
        "camera": "DWARFIII",
        "optic": "REDCAT51",
        "date": "2026-01-27",
        "filter": "L",
    }

    dest_path = build_destination_path(
        source_file="test.xisf",
        dest_dir="/dest",
        datum=datum,
    )

    # Verify order: dest -> MASTER FLAT -> camera -> optic -> DATE_xxx -> filename
    path_parts = dest_path.split(os.sep)
    dest_idx = next(i for i, p in enumerate(path_parts) if "dest" in p)
    flat_idx = next(i for i, p in enumerate(path_parts) if p == "MASTER FLAT")
    camera_idx = next(i for i, p in enumerate(path_parts) if "DWARFIII" in p)
    optic_idx = next(i for i, p in enumerate(path_parts) if "REDCAT51" in p)
    date_idx = next(i for i, p in enumerate(path_parts) if "DATE_" in p)
    assert dest_idx < flat_idx < camera_idx < optic_idx < date_idx


# Tests for helper functions


def test_build_filename_bias():
    """Test filename building for BIAS frames."""
    datum = {
        "type": "MASTER BIAS",
        "gain": 100,
        "offset": 10,
        "settemp": -10,
    }

    filename = _build_filename(datum, ".xisf")

    assert filename.startswith("masterBias")
    assert "GAIN_100" in filename
    assert "OFFSET_10" in filename
    assert filename.endswith(".xisf")


def test_build_filename_dark():
    """Test filename building for DARK frames."""
    datum = {
        "type": "MASTER DARK",
        "exposureseconds": 300,
        "gain": 100,
    }

    filename = _build_filename(datum, ".fits")

    assert filename.startswith("masterDark")
    assert "_300_" in filename
    assert "GAIN_100" in filename
    assert filename.endswith(".fits")


def test_build_filename_flat():
    """Test filename building for FLAT frames."""
    datum = {
        "type": "MASTER FLAT",
        "filter": "L",
        "gain": 100,
    }

    filename = _build_filename(datum, ".xisf")

    assert filename.startswith("masterFlat")
    assert "FILTER_L" in filename
    assert "GAIN_100" in filename
    assert filename.endswith(".xisf")


def test_build_filename_missing_optional():
    """Test filename building with missing optional properties."""
    datum = {
        "type": "MASTER BIAS",
        "gain": 100,
        # offset is missing
    }

    filename = _build_filename(datum, ".xisf")

    assert "GAIN_100" in filename
    assert "OFFSET" not in filename


def test_build_bias_path():
    """Test BIAS path construction."""
    datum = {"type": "MASTER BIAS", "camera": "DWARFIII"}
    path = _build_bias_path(datum, "/dest", "test.xisf")

    assert "/dest" in path or "\\dest" in path
    assert "MASTER BIAS" in path
    assert "DWARFIII" in path
    assert "test.xisf" in path


def test_build_dark_path():
    """Test DARK path construction."""
    datum = {"type": "MASTER DARK", "camera": "DWARFIII"}
    path = _build_dark_path(datum, "/dest", "test.xisf")

    assert "/dest" in path or "\\dest" in path
    assert "MASTER DARK" in path
    assert "DWARFIII" in path
    assert "test.xisf" in path


def test_build_flat_path_with_optic():
    """Test FLAT path construction with optic."""
    datum = {
        "type": "MASTER FLAT",
        "camera": "DWARFIII",
        "optic": "REDCAT51",
        "date": "2026-01-27",
    }
    path = _build_flat_path(datum, "/dest", "test.xisf")

    assert "/dest" in path or "\\dest" in path
    assert "MASTER FLAT" in path
    assert "DWARFIII" in path
    assert "REDCAT51" in path
    assert "DATE_2026-01-27" in path
    assert "test.xisf" in path


def test_build_flat_path_without_optic():
    """Test FLAT path construction without optic."""
    datum = {"type": "MASTER FLAT", "camera": "DWARFIII", "date": "2026-01-27"}
    path = _build_flat_path(datum, "/dest", "test.xisf")

    assert "MASTER FLAT" in path
    assert "DWARFIII" in path
    assert "DATE_2026-01-27" in path
    assert "test.xisf" in path
    # Verify optic is not in path
    path_parts = path.split(os.sep)
    camera_idx = next(i for i, p in enumerate(path_parts) if "DWARFIII" in p)
    date_idx = next(i for i, p in enumerate(path_parts) if "DATE_" in p)
    assert date_idx == camera_idx + 1


def test_check_for_collisions_no_files():
    """Test collision detection with no existing files."""
    copy_list = [("src1.xisf", "/nonexistent/dest1.xisf")]
    collisions = _check_for_collisions(copy_list)

    assert collisions == []


def test_check_for_collisions_with_existing_files():
    """Test collision detection with existing files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create an existing file
        existing_file = os.path.join(tmpdir, "existing.xisf")
        with open(existing_file, "w") as f:
            f.write("test")

        copy_list = [
            ("src1.xisf", existing_file),
            ("src2.xisf", os.path.join(tmpdir, "nonexistent.xisf")),
        ]

        collisions = _check_for_collisions(copy_list)

        assert len(collisions) == 1
        assert existing_file in collisions


def test_check_for_collisions_multiple():
    """Test collision detection with multiple existing files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create multiple existing files
        file1 = os.path.join(tmpdir, "file1.xisf")
        file2 = os.path.join(tmpdir, "file2.xisf")
        with open(file1, "w") as f:
            f.write("test1")
        with open(file2, "w") as f:
            f.write("test2")

        copy_list = [
            ("src1.xisf", file1),
            ("src2.xisf", file2),
        ]

        collisions = _check_for_collisions(copy_list)

        assert len(collisions) == 2
        assert file1 in collisions
        assert file2 in collisions


# Integration tests for copy_calibration_frames


def test_copy_calibration_frames_invalid_source_dir():
    """Test that invalid source directory raises ValueError."""
    with pytest.raises(ValueError, match="Source directory does not exist"):
        copy_calibration_frames(
            source_dir="/nonexistent/path",
            dest_dir="/dest",
        )


def test_copy_calibration_frames_no_files():
    """Test copy_calibration_frames with no matching files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Mock get_filtered_metadata to return empty results
        with patch(
            "ap_move_master_to_library.move_calibration.get_filtered_metadata"
        ) as mock_get_metadata:
            mock_get_metadata.return_value = {}

            # Should complete without error
            copy_calibration_frames(source_dir=tmpdir, dest_dir=tmpdir)

            # Should be called 3 times (MASTER BIAS, MASTER DARK, MASTER FLAT)
            assert mock_get_metadata.call_count == 3


def test_copy_calibration_frames_with_files():
    """Test copy_calibration_frames with mock files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create mock metadata
        bias_metadata = {
            "/src/bias.xisf": {
                "type": "MASTER BIAS",
                "camera": "DWARFIII",
                "gain": 100,
            }
        }

        dark_metadata = {
            "/src/dark.xisf": {
                "type": "MASTER DARK",
                "camera": "DWARFIII",
                "exposureseconds": 300,
                "gain": 100,
            }
        }

        flat_metadata = {
            "/src/flat.xisf": {
                "type": "MASTER FLAT",
                "camera": "DWARFIII",
                "date": "2026-01-27",
                "filter": "L",
            }
        }

        def mock_get_metadata(*args, **kwargs):
            filter_type = kwargs.get("filters", {}).get("type", "")
            if filter_type == "MASTER BIAS":
                return bias_metadata
            elif filter_type == "MASTER DARK":
                return dark_metadata
            elif filter_type == "MASTER FLAT":
                return flat_metadata
            return {}

        with patch(
            "ap_move_master_to_library.move_calibration.get_filtered_metadata",
            side_effect=mock_get_metadata,
        ):
            with patch(
                "ap_move_master_to_library.move_calibration.copy_file"
            ) as mock_copy_file:
                copy_calibration_frames(source_dir=tmpdir, dest_dir=tmpdir)

                # Should copy 3 files (1 BIAS, 1 DARK, 1 FLAT)
                assert mock_copy_file.call_count == 3


def test_copy_calibration_frames_dryrun():
    """Test copy_calibration_frames in dry run mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        bias_metadata = {
            "/src/bias.xisf": {
                "type": "MASTER BIAS",
                "camera": "DWARFIII",
                "gain": 100,
            }
        }

        def mock_get_metadata(*args, **kwargs):
            filter_type = kwargs.get("filters", {}).get("type", "")
            if filter_type == "MASTER BIAS":
                return bias_metadata
            return {}

        with patch(
            "ap_move_master_to_library.move_calibration.get_filtered_metadata",
            side_effect=mock_get_metadata,
        ):
            with patch(
                "ap_move_master_to_library.move_calibration.copy_file"
            ) as mock_copy_file:
                copy_calibration_frames(source_dir=tmpdir, dest_dir=tmpdir, dryrun=True)

                # copy_file should be called once with dryrun=True
                assert mock_copy_file.call_count == 1
                call_args = mock_copy_file.call_args
                assert call_args.kwargs["dryrun"] is True


def test_copy_calibration_frames_no_overwrite_with_collision():
    """Test copy_calibration_frames with no_overwrite and existing files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create an existing destination file
        dest_dir = os.path.join(tmpdir, "dest")
        os.makedirs(dest_dir, exist_ok=True)
        bias_dir = os.path.join(dest_dir, "MASTER BIAS", "DWARFIII")
        os.makedirs(bias_dir, exist_ok=True)
        existing_file = os.path.join(bias_dir, "masterBias_GAIN_100.xisf")
        with open(existing_file, "w") as f:
            f.write("existing")

        bias_metadata = {
            "/src/bias.xisf": {
                "type": "MASTER BIAS",
                "camera": "DWARFIII",
                "gain": 100,
            }
        }

        with patch(
            "ap_move_master_to_library.move_calibration.get_filtered_metadata",
            return_value=bias_metadata,
        ):
            with pytest.raises(FileExistsError, match="existing files"):
                copy_calibration_frames(
                    source_dir=tmpdir, dest_dir=dest_dir, no_overwrite=True
                )


def test_copy_calibration_frames_missing_metadata():
    """Test copy_calibration_frames with missing required metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # BIAS with missing camera (required)
        bias_metadata = {
            "/src/bias.xisf": {
                "type": "MASTER BIAS",
                "gain": 100,
                # camera is missing
            }
        }

        with patch(
            "ap_move_master_to_library.move_calibration.get_filtered_metadata",
            return_value=bias_metadata,
        ):
            with patch(
                "ap_move_master_to_library.move_calibration.copy_file"
            ) as mock_copy_file:
                # Should not raise, but skip the file
                copy_calibration_frames(source_dir=tmpdir, dest_dir=tmpdir)

                # Should not copy any files
                assert mock_copy_file.call_count == 0


def test_copy_calibration_frames_copy_failure():
    """Test copy_calibration_frames when copy_file fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        bias_metadata = {
            "/src/bias.xisf": {
                "type": "MASTER BIAS",
                "camera": "DWARFIII",
                "gain": 100,
            }
        }

        with patch(
            "ap_move_master_to_library.move_calibration.get_filtered_metadata",
            return_value=bias_metadata,
        ):
            with patch(
                "ap_move_master_to_library.move_calibration.copy_file",
                side_effect=Exception("Copy failed"),
            ):
                # Should not raise, but log error
                copy_calibration_frames(source_dir=tmpdir, dest_dir=tmpdir)
