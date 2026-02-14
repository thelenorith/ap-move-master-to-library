# ap-move-master-to-library

[![Test](https://github.com/jewzaam/ap-move-master-to-library/workflows/Test/badge.svg)](https://github.com/jewzaam/ap-move-master-to-library/actions/workflows/test.yml)
[![Coverage](https://github.com/jewzaam/ap-move-master-to-library/workflows/Coverage%20Check/badge.svg)](https://github.com/jewzaam/ap-move-master-to-library/actions/workflows/coverage.yml)
[![Lint](https://github.com/jewzaam/ap-move-master-to-library/workflows/Lint/badge.svg)](https://github.com/jewzaam/ap-move-master-to-library/actions/workflows/lint.yml)
[![Format](https://github.com/jewzaam/ap-move-master-to-library/workflows/Format%20Check/badge.svg)](https://github.com/jewzaam/ap-move-master-to-library/actions/workflows/format.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Organizes master calibration frames (bias, dark, flat) into a structured library by camera, optic, and date.

## What It Does

- Scans source directory for master calibration frames (.xisf, .fits)
- Organizes masters by type (BIAS, DARK, FLAT) and optical configuration
- Names files with full metadata for traceability
- Creates date-based subdirectories for flats

## Documentation

This tool is part of the astrophotography pipeline. For comprehensive documentation including workflow guides and integration with other tools, see:

- **[Pipeline Overview](https://github.com/jewzaam/ap-base/blob/main/docs/index.md)** - Full pipeline documentation
- **[Workflow Guide](https://github.com/jewzaam/ap-base/blob/main/docs/workflow.md)** - Detailed workflow with diagrams
- **[ap-move-master-to-library Reference](https://github.com/jewzaam/ap-base/blob/main/docs/tools/ap-move-master-to-library.md)** - Tool reference documentation

## Installation

### Development

```bash
make install-dev
```

### From Git

```bash
pip install git+https://github.com/jewzaam/ap-move-master-to-library.git
```

## Usage

```powershell
python -m ap_move_master_to_library <source_dir> <dest_dir> [--debug] [--dryrun] [--no-overwrite] [--quiet]
```

Options:
- `source_dir`: Source directory containing master calibration files
- `dest_dir`: Destination directory for organized calibration library
- `--debug`: Enable debug output
- `--dryrun`: Perform dry run without copying files
- `--no-overwrite`: Fail if destination files already exist (default: overwrite)
- `-q`, `--quiet`: Suppress progress output

**Windows Note**: Avoid trailing backslashes in quoted paths (use `"D:\path"` not `"D:\path\"`) as the backslash escapes the closing quote.

## Quick Start

**Organize master calibration frames:**
```powershell
python -m ap_move_master_to_library "D:\WBPP\_calibration\master" "D:\Calibration_Library"
```

**Dry run to preview changes:**
```powershell
python -m ap_move_master_to_library "D:\WBPP\_calibration\master" "D:\Calibration_Library" --dryrun
```

**Check for collisions without overwriting:**
```powershell
python -m ap_move_master_to_library "D:\WBPP\_calibration\master" "D:\Calibration_Library" --no-overwrite
```

## Output Structure

```
dest_dir/
├── MASTER BIAS/
│   └── {camera}/
│       └── masterBias_GAIN_{gain}_OFFSET_{offset}_SETTEMP_{temp}_READOUTMODE_{mode}.xisf
├── MASTER DARK/
│   └── {camera}/
│       └── masterDark_EXPTIME_{seconds}_GAIN_{gain}_OFFSET_{offset}_SETTEMP_{temp}.xisf
└── MASTER FLAT/
    └── {camera}/
        └── [{optic}/]
            └── DATE_{CCYY-MM-DD}/
                └── masterFlat_FILTER_{filter}_GAIN_{gain}_OFFSET_{offset}_SETTEMP_{temp}.xisf
```

Masters are organized by:
- **MASTER BIAS/DARK**: Camera only (date-independent, reusable across sessions)
- **MASTER FLAT**: Camera, optional optic, and date (date-specific, organized chronologically)

Filenames include full metadata for matching:
- `GAIN`, `OFFSET`, `SETTEMP`, `READOUTMODE` - Instrument settings
- `EXPTIME` (darks only) - Exposure time
- `FILTER` (flats only) - Filter name
- `FOCALLEN` (flats, optional) - Focal length

## Requirements

- Python 3.10+
- `ap-common` package (installed automatically)

Frames must have proper FITS keywords:
- `IMAGETYP`: Frame type (`MASTER BIAS`, `MASTER DARK`, `MASTER FLAT`)
- `INSTRUME`: Camera model
- `GAIN`: Gain setting
- `OFFSET`: Offset setting (optional)
- `SET-TEMP` or `SETTEMP`: Sensor temperature (optional)
- `READOUTM`: Readout mode (optional)
- `EXPOSURE` or `EXPTIME`: Exposure time (for darks)
- `DATE-OBS`: Observation date (for flats)
- `FILTER`: Filter name (for flats)
- `TELESCOP`: Telescope/optic (for flats, optional)

## How It Works

1. Scans source directory for FITS/XISF files with `MASTER BIAS`, `MASTER DARK`, or `MASTER FLAT` frame types
2. Reads FITS headers to extract metadata
3. Builds destination paths based on frame type and metadata
4. Copies files to organized library structure
5. Reports statistics (scanned, copied, skipped)

Files are copied (not moved) to preserve the original source directory.

## Development

Run tests:
```powershell
make test
```

Run with coverage:
```powershell
make coverage
```

Format code:
```powershell
make format
```

Lint code:
```powershell
make lint
```
