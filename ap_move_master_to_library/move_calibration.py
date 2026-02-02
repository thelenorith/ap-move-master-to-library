# Generated-by: Claude Code (Claude Sonnet 4.5)
"""
Main module for copying and organizing master calibration frames.

This module provides the CLI entry point and core logic for organizing
master calibration frames by type and optical configuration.
"""

import argparse
import logging
import os
import sys

from ap_common.filesystem import copy_file
from ap_common.logging_config import setup_logging
from ap_common.metadata import get_filtered_metadata
from ap_common.normalization import denormalize_header
from ap_common.progress import progress_iter
from ap_common.utils import camelCase, replace_env_vars

from . import config

# Configure logging
logger = logging.getLogger(__name__)


def _build_filename(datum: dict, file_extension: str) -> str:
    """
    Builds a filename from metadata properties.

    Args:
        datum: Metadata dictionary
        file_extension: File extension to append

    Returns:
        Filename string
    """
    # Use camelCase for type prefix (e.g., "MASTER BIAS" -> "masterBias")
    output_filename = camelCase(datum["type"])

    # Add metadata to filename
    for key in config.FILENAME_PROPERTIES[datum["type"]]:
        if key in datum and datum[key] is not None:
            p = denormalize_header(key)
            if p is None:
                p = str(key).upper()
            output_filename += f"_{p}_{datum[key]}"

    output_filename += file_extension
    return output_filename


def _build_bias_path(datum: dict, dest_dir: str, filename: str) -> str:
    """
    Builds destination path for MASTER BIAS frames.

    Args:
        datum: Metadata dictionary
        dest_dir: Destination base directory
        filename: Filename to use

    Returns:
        Full destination path
    """
    return os.path.join(
        dest_dir, datum["type"], datum[config.NORMALIZED_HEADER_CAMERA], filename
    )


def _build_dark_path(datum: dict, dest_dir: str, filename: str) -> str:
    """
    Builds destination path for MASTER DARK frames.

    Args:
        datum: Metadata dictionary
        dest_dir: Destination base directory
        filename: Filename to use

    Returns:
        Full destination path
    """
    return os.path.join(
        dest_dir, datum["type"], datum[config.NORMALIZED_HEADER_CAMERA], filename
    )


def _build_flat_path(datum: dict, dest_dir: str, filename: str) -> str:
    """
    Builds destination path for MASTER FLAT frames.

    Args:
        datum: Metadata dictionary
        dest_dir: Destination base directory
        filename: Filename to use

    Returns:
        Full destination path
    """
    date_subdir = f"DATE_{datum[config.NORMALIZED_HEADER_DATE]}"

    dest_path_parts = [dest_dir, datum["type"], datum[config.NORMALIZED_HEADER_CAMERA]]
    if (
        config.NORMALIZED_HEADER_OPTIC in datum
        and datum[config.NORMALIZED_HEADER_OPTIC] is not None
        and len(datum[config.NORMALIZED_HEADER_OPTIC]) > 0
    ):
        dest_path_parts.append(datum[config.NORMALIZED_HEADER_OPTIC])
    dest_path_parts.append(date_subdir)
    dest_path_parts.append(filename)

    return os.path.join(*dest_path_parts)


def build_destination_path(
    source_file: str, dest_dir: str, datum: dict, debug: bool = False
) -> str:
    """
    Builds the destination path for a calibration frame based on its type and metadata.

    Args:
        source_file: Source file path
        dest_dir: Destination base directory
        datum: Metadata dictionary for the file
        debug: Print debug information

    Returns:
        Full destination path for the file

    Raises:
        ValueError: If required metadata is missing for the given frame type
    """
    # Check for required 'type' field
    if "type" not in datum:
        raise ValueError(f"Missing 'type' metadata in {source_file}")

    frame_type = datum["type"]

    # Validate frame type
    if frame_type not in config.REQUIRED_PROPERTIES:
        raise ValueError(f"Unknown frame type '{frame_type}' in {source_file}")

    # Get file extension
    file_extension = os.path.splitext(source_file)[1]

    # Validate required metadata
    required_props = config.REQUIRED_PROPERTIES.get(frame_type, [])
    for prop in required_props:
        if prop not in datum or datum[prop] is None:
            raise ValueError(f"Missing required '{prop}' metadata for {source_file}")

    # Build filename
    filename = _build_filename(datum, file_extension)

    # Build path based on type
    if frame_type == config.TYPE_MASTER_BIAS:
        dest_path = _build_bias_path(datum, dest_dir, filename)
    elif frame_type == config.TYPE_MASTER_DARK:
        dest_path = _build_dark_path(datum, dest_dir, filename)
    elif frame_type == config.TYPE_MASTER_FLAT:
        dest_path = _build_flat_path(datum, dest_dir, filename)

    return os.path.normpath(dest_path)


def _check_for_collisions(copy_list: list) -> list:
    """
    Checks for existing destination files.

    Args:
        copy_list: List of (source_file, dest_file) tuples

    Returns:
        List of existing destination files
    """
    existing_files = []
    for source_file, dest_file in copy_list:
        if os.path.exists(dest_file):
            existing_files.append(dest_file)
    return existing_files


def _print_summary(stats: dict, dryrun: bool):
    """
    Prints summary statistics.

    Args:
        stats: Statistics dictionary
        dryrun: Whether this was a dry run
    """
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    for frame_type in config.MASTER_CALIBRATION_TYPES:
        logger.info(
            f"{frame_type}: scanned={stats[frame_type]['scanned']}, "
            f"copied={stats[frame_type]['copied']}, skipped={stats[frame_type]['skipped']}"
        )

    total_scanned = sum(s["scanned"] for s in stats.values())
    total_copied = sum(s["copied"] for s in stats.values())
    total_skipped = sum(s["skipped"] for s in stats.values())

    logger.info(
        f"TOTAL: scanned={total_scanned}, copied={total_copied}, skipped={total_skipped}"
    )
    logger.info("=" * 60)

    if dryrun:
        logger.info("(DRY RUN - no files were actually copied)")


def copy_calibration_frames(
    source_dir: str,
    dest_dir: str,
    debug: bool = False,
    dryrun: bool = False,
    no_overwrite: bool = False,
):
    """
    Copies and organizes master calibration frames from source to destination.

    Args:
        source_dir: Source directory containing master calibration files
        dest_dir: Destination directory for organized library
        debug: Enable debug output
        dryrun: Perform dry run without copying files
        no_overwrite: If True, fail if any destination files already exist

    Raises:
        FileExistsError: If no_overwrite is True and destination files exist
        ValueError: If required metadata is missing
    """
    # Replace environment variables
    source_dir = replace_env_vars(source_dir)
    dest_dir = replace_env_vars(dest_dir)

    # Validate directories
    if not os.path.isdir(source_dir):
        raise ValueError(f"Source directory does not exist: {source_dir}")

    logger.info(f"Scanning source directory: {source_dir}")

    # Track statistics
    stats = {
        config.TYPE_MASTER_BIAS: {"scanned": 0, "copied": 0, "skipped": 0},
        config.TYPE_MASTER_DARK: {"scanned": 0, "copied": 0, "skipped": 0},
        config.TYPE_MASTER_FLAT: {"scanned": 0, "copied": 0, "skipped": 0},
    }

    # Process each calibration type
    for frame_type in config.MASTER_CALIBRATION_TYPES:
        logger.debug(f"Scanning for {frame_type} frames...")

        # Get all calibration frames of this type
        metadata = get_filtered_metadata(
            dirs=[source_dir],
            patterns=[r".*\.xisf$", r".*\.fits$"],
            recursive=True,
            required_properties=[],
            filters={"type": frame_type},
            debug=debug,
            profileFromPath=False,
        )

        stats[frame_type]["scanned"] = len(metadata)

        logger.debug(f"Found {len(metadata)} {frame_type} frames")

        # Build copy list with destination paths
        copy_list = []
        for source_file, datum in metadata.items():
            try:
                dest_file = build_destination_path(
                    source_file=source_file,
                    dest_dir=dest_dir,
                    datum=datum,
                    debug=debug,
                )
                copy_list.append((source_file, dest_file))
            except (ValueError, KeyError) as e:
                logger.warning(f"Skipping {source_file}: {e}")
                stats[frame_type]["skipped"] += 1
                continue

        # If no_overwrite is set, check for collisions up front
        if no_overwrite:
            existing_files = _check_for_collisions(copy_list)

            if existing_files:
                logger.error("The following destination files already exist:")
                for f in existing_files:
                    logger.error(f"  {f}")
                raise FileExistsError(
                    f"Found {len(existing_files)} existing files. Use without --no-overwrite to overwrite them."
                )

        # Copy files
        for source_file, dest_file in copy_list:
            logger.debug(f"Copy {source_file} -> {dest_file}")

            try:
                copy_file(
                    from_file=source_file,
                    to_file=dest_file,
                    debug=debug,
                    dryrun=dryrun,
                )
                stats[frame_type]["copied"] += 1
            except Exception as e:
                logger.error(f"Failed to copy {source_file}: {e}")
                stats[frame_type]["skipped"] += 1

    # Print summary
    _print_summary(stats, dryrun)


def main():
    """
    Main entry point for the ap-move-calibration CLI tool.
    """
    parser = argparse.ArgumentParser(
        description="Copy and organize master calibration frames from source to destination library"
    )

    parser.add_argument(
        "source_dir",
        type=str,
        help="Source directory containing master calibration files",
    )
    parser.add_argument(
        "dest_dir",
        type=str,
        help="Destination directory for organized calibration library",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument(
        "--dryrun",
        action="store_true",
        help="Perform dry run without copying files",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Fail if destination files already exist (default: overwrite existing files)",
    )

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(name="ap_move_master_to_library", debug=args.debug)

    try:
        copy_calibration_frames(
            source_dir=args.source_dir,
            dest_dir=args.dest_dir,
            debug=args.debug,
            dryrun=args.dryrun,
            no_overwrite=args.no_overwrite,
        )
    except Exception as e:
        logger.error(f"{e}")
        if args.debug:
            logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()
