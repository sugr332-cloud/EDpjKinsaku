"""Deterministically count BioScan species and ruleset blocks from a baseline tree.

This script intentionally reports separate units instead of collapsing them:
- species_count: entries exposed by the selected module's species mapping
- ruleset_count: total number of items in each species' ``rulesets`` list

It does not interpret individual conditions, OR semantics, N/A markers, or
variants. Those definitions must be made explicit by the source modules and
future filter options rather than inferred during manual counting.
"""
from __future__ import annotations

import argparse
import ast
from pathlib import Path


def _find_species_mapping(tree: ast.Module) -> ast.Dict | None:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "SPECIES":
                    if isinstance(node.value, ast.Dict):
                        return node.value
    return None


def _literal_dict(node: ast.AST) -> dict[str, object] | None:
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def count_module(path: Path) -> tuple[int, int, list[tuple[str, int]]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    species_node = _find_species_mapping(tree)
    if species_node is None:
        raise ValueError(f"{path}: SPECIES mapping not found")

    species_count = len(species_node.keys)
    details: list[tuple[str, int]] = []
    ruleset_count = 0

    for key_node, value_node in zip(species_node.keys, species_node.values):
        species_name = ast.literal_eval(key_node)
        if not isinstance(species_name, str):
            raise ValueError(f"{path}: species key is not a string")
        species_def = _literal_dict(value_node)
        if species_def is None:
            raise ValueError(f"{path}: {species_name}: definition is not literal")
        rulesets = species_def.get("rulesets", [])
        if not isinstance(rulesets, list):
            raise ValueError(f"{path}: {species_name}: rulesets is not a list")
        count = len(rulesets)
        details.append((species_name, count))
        ruleset_count += count

    return species_count, ruleset_count, details


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()

    for path in args.files:
        species_count, ruleset_count, details = count_module(path)
        print(f"{path}: species={species_count} rulesets={ruleset_count}")
        for species_name, count in details:
            print(f"  {species_name}: rulesets={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
