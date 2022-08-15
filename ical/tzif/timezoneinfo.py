"""Library for returning details about a timezone.

This package follows the same approach as zoneinfo for loading timezone
data. It first checks the system TZPATH, then falls back to the tzdata
python package.
"""

from __future__ import annotations

import os
import zoneinfo
from functools import cache
from importlib import resources

from .model import TimezoneInfo
from .tzif import read_tzif


class TimezoneInfoError(Exception):
    """Raised on error working with timezone information."""


@cache
def _read_system_timezones() -> set[str]:
    """Read and cache the set of system and tzdata timezones."""
    return zoneinfo.available_timezones()


def _find_tzfile(key: str) -> str | None:
    """Retrieve the path to a TZif file from a key."""
    for search_path in zoneinfo.TZPATH:
        filepath = os.path.join(search_path, key)
        if os.path.isfile(filepath):
            return filepath

    return None


@cache
def _read_tzdata_timezones() -> set[str]:
    """Returns the set of valid timezones from tzdata only."""
    try:
        with resources.files("tzdata").joinpath("zones").open(
            "r", encoding="utf-8"
        ) as zones_file:
            return {line.strip() for line in zones_file.readlines()}
    except ModuleNotFoundError:
        return set()


def _iana_key_to_resource(key: str) -> tuple[str, str]:
    """Returns the package and resource file for the specified timezone."""
    if "/" not in key:
        return "tzdata.zoneinfo", key
    package_loc, resource = key.rsplit("/", 1)
    package = "tzdata.zoneinfo." + package_loc.replace("/", ".")
    return package, resource


def read(key: str) -> TimezoneInfo:
    """Read the TZif file from the tzdata package and return timezone records."""
    if key not in _read_system_timezones():
        raise TimezoneInfoError(f"Unable to find timezone in system timezones: {key}")

    # Prefer system timezone data when available
    tzfile = _find_tzfile(key)
    if tzfile is not None:
        with open(tzfile, "rb") as tzfile_file:
            return read_tzif(tzfile_file.read())

    # Fallback to tzdata package if installed
    if key not in _read_tzdata_timezones():
        raise TimezoneInfoError(f"Unable to find timezone: {key}")

    (package, resource) = _iana_key_to_resource(key)
    try:
        with resources.files(package).joinpath(resource).open("rb") as tzdata_file:
            return read_tzif(tzdata_file.read())
    except ModuleNotFoundError as err:
        # Unexpected given we previously read the list of timezones
        raise TimezoneInfoError(f"Unable to load tzdata module: {key}") from err
    except FileNotFoundError as err:
        raise TimezoneInfoError(f"Unable to read tzdata file: {key}") from err