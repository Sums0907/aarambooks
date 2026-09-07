"""
Boundary & Self-Containment Invariant Tests for Catalog BS
Strictly verifies that Catalog BS does NOT import or depend on Brain Core or ShopDeck BS runtime code.
"""

import ast
import os
import pytest

PROHIBITED_IMPORT_PREFIXES = (
    "src",
    "brain_core",
    "business_systems.shopdeck",
    "shopdeck",
)

def get_catalog_python_files():
    catalog_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    py_files = []
    for root, dirs, files in os.walk(catalog_root):
        if "__pycache__" in root or ".pytest_cache" in root:
            continue
        for f in files:
            if f.endswith(".py"):
                py_files.append(os.path.join(root, f))
    return py_files

def test_catalog_zero_external_dependencies():
    py_files = get_catalog_python_files()
    assert len(py_files) > 0

    violations = []

    for file_path in py_files:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=file_path)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    for prohibited in PROHIBITED_IMPORT_PREFIXES:
                        if name == prohibited or name.startswith(prohibited + "."):
                            violations.append((file_path, node.lineno, name))
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for prohibited in PROHIBITED_IMPORT_PREFIXES:
                    if mod == prohibited or mod.startswith(prohibited + "."):
                        violations.append((file_path, node.lineno, mod))

    assert len(violations) == 0, f"Found prohibited cross-boundary imports: {violations}"

def test_catalog_self_containment_structure():
    catalog_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    required_files = [
        "schema.sql",
        "models.py",
        "validation.py",
        "service.py",
        "shopdeck_adapter.py",
        "public_views.sql",
        "config.py",
        "__init__.py",
    ]
    for rf in required_files:
        p = os.path.join(catalog_root, rf)
        assert os.path.exists(p), f"Missing self-contained Catalog BS core file: {rf}"
