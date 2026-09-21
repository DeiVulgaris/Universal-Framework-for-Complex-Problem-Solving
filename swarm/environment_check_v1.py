"""
UFCPS — Environment Check v1

Standalone diagnostic.

This file intentionally has NO UFCPS imports and uses only
the Python standard library.

Purpose:
    determine whether the local environment is capable of
    running the UFCPS Python modules.

It checks:
    - Python version
    - current directory
    - availability of expected UFCPS files
    - importability of selected modules
    - basic filesystem access

It does not modify the repository.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import importlib.util


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

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


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def print_header(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def check_file(path: Path) -> bool:
    exists = path.is_file()

    status = "PASS" if exists else "FAIL"

    print(
        f"{status:5} file: {path}"
    )

    return exists


def check_module(module_name: str) -> bool:

    try:

        spec = importlib.util.find_spec(
            module_name
        )

        available = (
            spec is not None
        )

        status = (
            "PASS"
            if available
            else "FAIL"
        )

        print(
            f"{status:5} module: {module_name}"
        )

        return available

    except Exception as exc:

        print(
            f"FAIL  module: {module_name}"
        )

        print(
            f"      {type(exc).__name__}: {exc}"
        )

        return False


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def main() -> int:

    print(
        "UFCPS — Environment Check v1"
    )

    print(
        f"Python: {sys.version}"
    )

    print(
        f"Executable: {sys.executable}"
    )

    print(
        f"Current directory: {Path.cwd()}"
    )

    # --------------------------------------------------------------
    # Python
    # --------------------------------------------------------------

    print_header(
        "PYTHON"
    )

    python_ok = (
        sys.version_info >= (3, 9)
    )

    print(
        "PASS  Python >= 3.9"
        if python_ok
        else
        "FAIL  Python >= 3.9 required"
    )

    # --------------------------------------------------------------
    # Repository
    # --------------------------------------------------------------

    print_header(
        "EXPECTED UFCPS FILES"
    )

    file_results = []

    for filename in EXPECTED_FILES:

        file_results.append(
            check_file(
                Path(filename)
            )
        )

    files_ok = all(
        file_results
    )

    # --------------------------------------------------------------
    # Package/module discovery
    # --------------------------------------------------------------

    print_header(
        "PYTHON MODULE DISCOVERY"
    )

    module_results = []

    for module_name in EXPECTED_MODULES:

        module_results.append(
            check_module(
                module_name
            )
        )

    modules_ok = all(
        module_results
    )

    # --------------------------------------------------------------
    # Import test
    # --------------------------------------------------------------

    print_header(
        "IMPORT TEST"
    )

    import_results = []

    for module_name in EXPECTED_MODULES:

        try:

            __import__(
                module_name
            )

            print(
                f"PASS  import {module_name}"
            )

            import_results.append(
                True
            )

        except Exception as exc:

            print(
                f"FAIL  import {module_name}"
            )

            print(
                f"      {type(exc).__name__}: {exc}"
            )

            import_results.append(
                False
            )

    imports_ok = all(
        import_results
    )

    # --------------------------------------------------------------
    # Summary
    # --------------------------------------------------------------

    print_header(
        "SUMMARY"
    )

    print(
        f"Python environment: "
        f"{'READY' if python_ok else 'NOT READY'}"
    )

    print(
        f"UFCPS files: "
        f"{'READY' if files_ok else 'INCOMPLETE'}"
    )

    print(
        f"Module discovery: "
        f"{'READY' if modules_ok else 'FAILED'}"
    )

    print(
        f"Imports: "
        f"{'READY' if imports_ok else 'FAILED'}"
    )

    ready = (
        python_ok
        and files_ok
        and modules_ok
        and imports_ok
    )

    print()

    if ready:

        print(
            "RESULT: UFCPS Python environment is READY."
        )

        print(
            "You can now run the Level 3 diagnostics."
        )

        return 0

    print(
        "RESULT: UFCPS Python environment is NOT READY."
    )

    print(
        "The diagnostic above identifies the missing layer."
    )

    return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
