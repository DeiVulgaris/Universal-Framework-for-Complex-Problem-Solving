"""
UFCPS — Environment Check v1

Checks:
1. Python version
2. Expected UFCPS files
3. Python module discovery
4. Importability of required swarm modules

The script is designed to work when executed as:

    python swarm/environment_check_v1.py

Therefore the repository root is explicitly added to sys.path.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Repository path setup
# ---------------------------------------------------------------------------

SCRIPT_PATH = Path(__file__).resolve()
SWARM_DIR = SCRIPT_PATH.parent
REPOSITORY_ROOT = SWARM_DIR.parent

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def section(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def passed(label: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    print(f"PASS  {label}{suffix}")


def failed(label: str, detail: str = "") -> None:
    suffix = f"\n      {detail}" if detail else ""
    print(f"FAIL  {label}{suffix}")


# ---------------------------------------------------------------------------
# Expected UFCPS files
# ---------------------------------------------------------------------------

EXPECTED_FILES = [
    "swarm/level3_emergent_integration_v1.py",
    "swarm/emergent_space_builder_v1.py",
    "swarm/orthogonal_transition_explorer_v1.py",
    "swarm/branch_interaction_v1.py",
    "swarm/reflection_v1.py",
    "swarm/frustration_v1.py",
    "swarm/cognitive_space_exhaustion_v1.py",
]


EXPECTED_MODULES = [
    "swarm.level3_emergent_integration_v1",
    "swarm.emergent_space_builder_v1",
    "swarm.orthogonal_transition_explorer_v1",
    "swarm.branch_interaction_v1",
    "swarm.reflection_v1",
    "swarm.frustration_v1",
    "swarm.cognitive_space_exhaustion_v1",
]


# ---------------------------------------------------------------------------
# Main diagnostic
# ---------------------------------------------------------------------------

def main() -> int:
    print("UFCPS — Environment Check v1")
    print()
    print(f"Python: {sys.version}")
    print(f"Executable: {sys.executable}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Repository root: {REPOSITORY_ROOT}")
    print(f"Python path root added: {REPOSITORY_ROOT}")

    failures = 0

    # -----------------------------------------------------------------------
    # Python
    # -----------------------------------------------------------------------

    section("PYTHON")

    if sys.version_info >= (3, 9):
        passed("Python >= 3.9")
    else:
        failed(
            "Python >= 3.9",
            f"Detected Python {sys.version_info.major}.{sys.version_info.minor}",
        )
        failures += 1

    # -----------------------------------------------------------------------
    # Expected files
    # -----------------------------------------------------------------------

    section("EXPECTED UFCPS FILES")

    for relative_path in EXPECTED_FILES:
        path = REPOSITORY_ROOT / relative_path

        if path.is_file():
            passed(f"file: {relative_path}")
        else:
            failed(f"file: {relative_path}")
            failures += 1

    # -----------------------------------------------------------------------
    # Package discovery
    # -----------------------------------------------------------------------

    section("PYTHON MODULE DISCOVERY")

    swarm_init = SWARM_DIR / "__init__.py"

    if swarm_init.is_file():
        passed("package: swarm")
    else:
        failed(
            "package: swarm",
            f"Missing {swarm_init}",
        )
        failures += 1

    for module_name in EXPECTED_MODULES:
        try:
            spec = importlib.util.find_spec(module_name)

            if spec is not None:
                passed(f"module: {module_name}")
            else:
                failed(
                    f"module: {module_name}",
                    "find_spec returned None",
                )
                failures += 1

        except Exception as exc:
            failed(
                f"module: {module_name}",
                f"{type(exc).__name__}: {exc}",
            )
            failures += 1

    # -----------------------------------------------------------------------
    # Import test
    # -----------------------------------------------------------------------

    section("IMPORT TEST")

    for module_name in EXPECTED_MODULES:
        try:
            importlib.import_module(module_name)
            passed(f"import {module_name}")

        except Exception as exc:
            failed(
                f"import {module_name}",
                f"{type(exc).__name__}: {exc}",
            )
            failures += 1

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------

    section("SUMMARY")

    if sys.version_info >= (3, 9):
        python_ready = True
    else:
        python_ready = False

    files_ready = all(
        (REPOSITORY_ROOT / relative_path).is_file()
        for relative_path in EXPECTED_FILES
    )

    module_discovery_ready = all(
        importlib.util.find_spec(module_name) is not None
        for module_name in EXPECTED_MODULES
        if _safe_find_spec(module_name)
    )

    imports_ready = _check_imports_safely()

    print(
        f"Python environment: "
        f"{'READY' if python_ready else 'NOT READY'}"
    )

    print(
        f"UFCPS files: "
        f"{'READY' if files_ready else 'INCOMPLETE'}"
    )

    print(
        f"Module discovery: "
        f"{'READY' if module_discovery_ready else 'FAILED'}"
    )

    print(
        f"Imports: "
        f"{'READY' if imports_ready else 'FAILED'}"
    )

    if failures == 0:
        print()
        print("RESULT: UFCPS Python environment is READY.")
        return 0

    print()
    print("RESULT: UFCPS Python environment is NOT READY.")
    print("The diagnostic above identifies the failing layer.")

    return 1


def _safe_find_spec(module_name: str) -> bool:
    """
    Safe helper used only by the summary section.

    Returns True when find_spec can be evaluated without raising.
    """

    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False


def _check_imports_safely() -> bool:
    """
    Re-check required imports without allowing one failure
    to interrupt the diagnostic summary.
    """

    for module_name in EXPECTED_MODULES:
        try:
            importlib.import_module(module_name)
        except Exception:
            return False

    return True


if __name__ == "__main__":
    raise SystemExit(main())
