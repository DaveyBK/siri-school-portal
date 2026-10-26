"""
Test-mode switch (marathon Batch 0, B0-1).

Test mode is on if and only if the file TEST_MODE exists in the folder that holds both apps
(...\\apps\\TEST_MODE). The live folder never has that file, so live behaviour is unchanged.

Practice mode (a training copy for staff) is the same with a second marker file, PRACTICE_MODE, in the same folder.
It switches on every test-mode guard (so TEST_MODE below means "sandbox guards on": either marker) and changes only
what the user sees: the banner, the window title and the "Disabled in ..." texts.

Guard 1: if a marker is found in the live apps folder, the apps refuse to start.
Guard 2: with a marker, every data path must resolve inside the apps folder, or the app refuses to start.
"""

import importlib.util
import os
from pathlib import Path
from typing import Iterable

MARKER_NAME = "TEST_MODE"
PRACTICE_MARKER_NAME = "PRACTICE_MODE"
APPS_DIR = Path(__file__).resolve().parents[2]
LIVE_APPS_DIR = Path(r"D:\AI_phase\school\apps")  # used only to refuse
_LIVE_SPELLINGS = (LIVE_APPS_DIR, Path("/mnt/d/AI_phase/school/apps"))  # Windows, and WSL's mount point


class RunModeError(RuntimeError):
    """The apps must not start in this folder or with these paths."""


def is_practice_mode(apps_dir=None) -> bool:
    """True if the PRACTICE_MODE marker file is in apps_dir (default: the folder that holds both apps)."""
    base = Path(apps_dir) if apps_dir is not None else APPS_DIR
    return (base / PRACTICE_MARKER_NAME).is_file()


def is_test_mode(apps_dir=None) -> bool:
    """True if a marker file (TEST_MODE or PRACTICE_MODE) is in apps_dir: the sandbox guards are on."""
    base = Path(apps_dir) if apps_dir is not None else APPS_DIR
    return (base / MARKER_NAME).is_file() or is_practice_mode(base)


def mode_name(apps_dir=None) -> str:
    """What the marker in apps_dir is called on screen: "PRACTICE MODE" or "TEST MODE"."""
    return "PRACTICE MODE" if is_practice_mode(apps_dir) else "TEST MODE"


TEST_MODE = is_test_mode()
PRACTICE_MODE = is_practice_mode()
MODE_NAME = mode_name()


def same_dir(a, b) -> bool:
    """True if a and b are the same folder (samefile; falls back to a case-insensitive text compare)."""
    try:
        return os.path.samefile(a, b)
    except OSError:
        return os.path.normcase(os.path.normpath(str(a))) == os.path.normcase(os.path.normpath(str(b)))


def is_inside(path, root) -> bool:
    """True if path is root or lies inside it (case-insensitive on Windows; symlinks resolved)."""
    try:
        p = os.path.normcase(str(Path(path).resolve()))
        r = os.path.normcase(str(Path(root).resolve()))
        return os.path.commonpath([p, r]) == r
    except (OSError, ValueError):
        return False


def check(paths: Iterable = (), apps_dir=None, live_apps_dir=None) -> None:
    """Raise RunModeError if the apps must refuse to start. Does nothing when there is no marker.

    apps_dir and live_apps_dir default to this install's folder and the live folder; tests pass their own.
    """
    apps = Path(apps_dir) if apps_dir is not None else APPS_DIR
    if not is_test_mode(apps):
        return
    name = mode_name(apps)
    marker = PRACTICE_MARKER_NAME if is_practice_mode(apps) else MARKER_NAME
    lives = [Path(live_apps_dir)] if live_apps_dir is not None else list(_LIVE_SPELLINGS)
    for live in lives:
        if same_dir(apps, live):
            raise RunModeError(
                f"The {name} marker is in the live apps folder ({apps}). "
                f"Remove {apps / marker}: it must never be placed there."
            )
    for p in paths:
        if not is_inside(p, apps):
            raise RunModeError(
                f"{name}: the data path {p} is outside the sandbox ({apps}). Refusing to start."
            )


_ctest_config = None


def load_ctest_config():
    """C-Test's config.py, loaded from this install's c_test_app folder under its own module name."""
    global _ctest_config
    if _ctest_config is None:
        path = APPS_DIR / "c_test_app" / "config.py"
        spec = importlib.util.spec_from_file_location("marathon_ctest_config", path)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except RuntimeError as e:  # C-Test's own guard 1
            raise RunModeError(str(e)) from e
        _ctest_config = module
    return _ctest_config
