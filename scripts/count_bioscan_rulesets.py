"""Deterministically count BioScan species and ruleset blocks.

The BioScan baseline uses a top-level ``catalog`` mapping. This counter reads
that mapping without importing the upstream package, so the audit is tied to
the selected source files rather than the local project's runtime imports.

Unsupported expressions are reported as warnings and never silently counted.
"""
from __future__ import annotations

import argparse
import ast
from pathlib import Path


def _find_catalog(tree: ast.Module) -> ast.Dict | None:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "catalog":
                    if isinstance(node.value, ast.Dict):
                        return node.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "catalog":
                if isinstance(node.value, ast.Dict):
                    return node.value
    return None


def _literal_dict(node: ast.AST) -> dict[object, object] | None:
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def count_module(path: Path) -> int:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    catalog_node = _find_catalog(tree)
    if catalog_node is None:
        raise ValueError(f"{path}: catalog mapping is not a literal dict")

    catalog = _literal_dict(catalog_node)
    if catalog is None:
        raise ValueError(f"{path}: catalog mapping is not statically literal")

    genus_count = len(catalog)
    species_count = 0
    ruleset_count = 0
    warnings = 0

    for genus_name, genus_value in catalog.items():
        if not isinstance(genus_value, dict):
            print(f"WARNING {path}: genus={genus_name!r}: unsupported definition")
            warnings += 1
            continue
        for species_key, species_value in genus_value.items():
            species_def = species_value if isinstance(species_value, dict) else None
            species_name = (
                species_def.get("name", species_key)
                if species_def is not None
                else species_key
            )
            species_count += 1
            if species_def is None:
                print(
                    f"WARNING {path}: species={species_name!r}: "
                    "definition is not statically literal"
                )
                warnings += 1
                continue
            rulesets = species_def.get("rulesets", [])
            if not isinstance(rulesets, list):
                print(
                    f"WARNING {path}: species={species_name!r}: "
                    f"rulesets expression is unsupported ({type(rulesets).__name__})"
                )
                warnings += 1
                continue
            count = len(rulesets)
            ruleset_count += count
            print(f"  {species_name}: rulesets={count}")

    print(
        f"RESULT {path}: genus_entries={genus_count} "
        f"species={species_count} rulesets={ruleset_count} warnings={warnings}"
    )
    return 0 if warnings == 0 else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    exit_code = 0
    for path in args.files:
        try:
            exit_code = max(exit_code, count_module(path))
        except (OSError, SyntaxError, ValueError) as exc:
            print(f"ERROR {path}: {exc}")
            exit_code = 2
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
