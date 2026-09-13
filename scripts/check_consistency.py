"""Phase F consistency check (F-1).

Measures the codebase directly and compares those measurements against any
machine-readable ``<!-- baseline:begin -->`` block a document declares (see
docs/PHASE_F_IMPLEMENTATION_DOC_CONSISTENCY_SPEC_V0.1.md section 2). This
script only reads app/ and docs/ - it never edits either.

Two things it checks unconditionally (no baseline block needed):

- C5: every ``app/...py`` / ``scripts/...py``-shaped path mentioned in
  docs/**/*.md or README.md actually exists.
- Baseline block well-formedness: at most one per document.

Everything else (C1/C2/C3/C4 against a baseline block's ``implemented_*``
keys) only fires for documents that actually carry a baseline block. None do
yet (that is BLOCK 1's job - see spec section 2's "段階的な実効化"), so this
part is currently a no-op that still exercises its own comparison logic
against zero documents.

No PyYAML dependency: the baseline block's schema is a small, fixed subset
(flat 2-level mappings and one inline list), parsed by hand below rather than
adding a project dependency for it.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# C5: path-shaped mentions the docs make about the code, checked for real existence.
CODE_PATH_RE = re.compile(r'\b(?:app|scripts)/[A-Za-z0-9_./-]+\.py\b')

BASELINE_BLOCK_RE = re.compile(
    r'<!--\s*baseline:begin\s*-->\s*```ya?ml\s*\n(?P<body>.*?)\n```\s*<!--\s*baseline:end\s*-->',
    re.DOTALL,
)

# The Phase F spec document itself contains a *syntactically real* baseline block as its own
# illustrative example of the format (section 2) - it is documentation of the schema, not a claim
# that c_core has 1 genus. Scanning it as a live claim would make check_consistency fail against the
# very document that defines what a baseline block is. The spec's own section 2 "段階的な実効化"
# says no document is meant to carry a real baseline block until BLOCK 1, so this is a one-line
# exclusion of the file that defines the syntax, not a general carve-out.
BASELINE_EXAMPLE_ONLY_DOC = "PHASE_F_IMPLEMENTATION_DOC_CONSISTENCY_SPEC_V0.1.md"


def measure_c1_c2(c_core_path: Path) -> tuple[int, int, list[str]]:
    """Returns (implemented_genera, implemented_rulesets, genus_rule_names).

    Finds every module-level ``*_RULES: tuple[NormalizedRule, ...] = (...)``
    definition by AST - not by importing and counting, which would silently
    stop reflecting reality the day a rule set moves to external data (see
    spec section 1). The genus count is ``len()`` of what AST actually finds,
    never a written-out number or name list.
    """
    tree = ast.parse(c_core_path.read_text(encoding="utf-8"))
    rule_var_names: list[str] = []
    total_rulesets = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.AnnAssign):
            continue
        if not isinstance(node.target, ast.Name) or not node.target.id.endswith("_RULES"):
            continue
        annotation_text = ast.dump(node.annotation)
        if "NormalizedRule" not in annotation_text:
            continue
        if not isinstance(node.value, ast.Tuple):
            continue
        rule_var_names.append(node.target.id)
        total_rulesets += len(node.value.elts)
    return len(rule_var_names), total_rulesets, rule_var_names


def measure_c3() -> int:
    """``len(SPECIES_VALUE_MASTER)`` via import, per spec section 1: import
    catches a definition gap a literal AST count of dict keys would not."""
    from app.bio.species_value_master import SPECIES_VALUE_MASTER

    return len(SPECIES_VALUE_MASTER)


def measure_c4() -> list[str]:
    """Registered Typer sub-command group names on ``app.cli.__main__.app``."""
    from app.cli.__main__ import app

    return [group.name for group in app.registered_groups]


def check_c5(repo_root: Path) -> list[str]:
    """Every app/...py or scripts/...py path mentioned in docs/README actually exists.

    Returns the list of mentioned paths that do not exist (empty when clean).
    """
    doc_files = list(repo_root.glob("docs/**/*.md"))
    readme = repo_root / "README.md"
    if readme.exists():
        doc_files.append(readme)

    missing: list[str] = []
    seen: set[str] = set()
    for doc in doc_files:
        text = doc.read_text(encoding="utf-8", errors="replace")
        for match in CODE_PATH_RE.finditer(text):
            ref = match.group(0)
            if "..." in ref:
                # A placeholder in prose describing the *shape* of a path (this very check's own
                # spec document writes "app/...py" to mean "some path under app/"), not an actual
                # file reference - found by running this against the real repo, where the spec
                # doc's own description of this rule was otherwise flagged as a missing file.
                continue
            if ref in seen:
                continue
            seen.add(ref)
            if not (repo_root / ref).exists():
                missing.append(ref)
    return sorted(missing)


def find_baseline_blocks(repo_root: Path) -> dict[Path, list[str]]:
    """Maps each doc with at least one baseline block to its raw YAML bodies.

    A document with more than one block is itself an error (checked by the
    caller); this function just reports how many it found per file.
    """
    result: dict[Path, list[str]] = {}
    doc_files = list(repo_root.glob("docs/**/*.md"))
    readme = repo_root / "README.md"
    if readme.exists():
        doc_files.append(readme)
    for doc in doc_files:
        if doc.name == BASELINE_EXAMPLE_ONLY_DOC:
            continue
        text = doc.read_text(encoding="utf-8", errors="replace")
        bodies = [m.group("body") for m in BASELINE_BLOCK_RE.finditer(text)]
        if bodies:
            result[doc] = bodies
    return result


def parse_baseline_yaml(body: str) -> dict:
    """Hand-rolled parser for the one fixed shape the spec defines (section 2):

    ```yaml
    c_core:
      implemented_genera: 1
      implemented_rulesets: 5
      target_genera: 20
      target_rulesets: 254
    species_value_master:
      implemented_entries: 114
      target_entries: provisional
    cli_commands: [journal, state, collector, api, calibration]
    ```

    Deliberately not a general YAML parser (no PyYAML dependency is declared
    for this project - see module docstring): two-level flat mappings plus
    one inline flow-sequence line, nothing else.
    """
    result: dict = {}
    current_section: dict | None = None
    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        indented = raw_line.startswith((" ", "\t"))
        key, _, value = line.strip().partition(":")
        key = key.strip()
        value = value.strip()
        if not indented:
            if value.startswith("[") and value.endswith("]"):
                items = [item.strip() for item in value[1:-1].split(",") if item.strip()]
                result[key] = items
                current_section = None
            elif value == "":
                current_section = {}
                result[key] = current_section
            else:
                result[key] = value
                current_section = None
        else:
            if current_section is None:
                raise ValueError(f"indented key {key!r} with no open section")
            current_section[key] = value
    return result


def compare_baseline(doc: Path, data: dict, measured: dict) -> list[str]:
    """Checks only ``implemented_*`` keys and ``cli_commands`` (spec section 2
    rule 2/3) - ``target_*`` is never compared, by design."""
    problems: list[str] = []

    c_core = data.get("c_core", {})
    if "implemented_genera" in c_core:
        expected = int(c_core["implemented_genera"])
        if expected != measured["genera"]:
            problems.append(
                f"{doc}: c_core.implemented_genera says {expected}, "
                f"AST measured {measured['genera']}"
            )
    if "implemented_rulesets" in c_core:
        expected = int(c_core["implemented_rulesets"])
        if expected != measured["rulesets"]:
            problems.append(
                f"{doc}: c_core.implemented_rulesets says {expected}, "
                f"AST measured {measured['rulesets']}"
            )

    species_master = data.get("species_value_master", {})
    if "implemented_entries" in species_master:
        expected = int(species_master["implemented_entries"])
        if expected != measured["species_master_entries"]:
            problems.append(
                f"{doc}: species_value_master.implemented_entries says {expected}, "
                f"measured {measured['species_master_entries']}"
            )

    if "cli_commands" in data:
        expected_cli = sorted(data["cli_commands"])
        actual_cli = sorted(measured["cli_commands"])
        if expected_cli != actual_cli:
            problems.append(
                f"{doc}: cli_commands says {expected_cli}, "
                f"actual registered commands are {actual_cli}"
            )

    return problems


def main() -> int:
    problems: list[str] = []

    genera, rulesets, rule_var_names = measure_c1_c2(REPO_ROOT / "app" / "bio" / "c_core.py")
    species_master_entries = measure_c3()
    cli_commands = measure_c4()

    print("Measured values:")
    print(f"  C1 implemented_genera   = {genera}  ({', '.join(rule_var_names)})")
    print(f"  C2 implemented_rulesets = {rulesets}")
    print(f"  C3 species_value_master = {species_master_entries}")
    print(f"  C4 cli_commands         = {sorted(cli_commands)}")
    print()

    missing_paths = check_c5(REPO_ROOT)
    if missing_paths:
        for ref in missing_paths:
            problems.append(f"C5: referenced path does not exist: {ref}")
    else:
        print("C5: every app/...py and scripts/...py path mentioned in docs/README exists.")

    measured = {
        "genera": genera,
        "rulesets": rulesets,
        "species_master_entries": species_master_entries,
        "cli_commands": cli_commands,
    }

    baseline_docs = find_baseline_blocks(REPO_ROOT)
    if not baseline_docs:
        print("No document currently carries a baseline block - C1-C4 comparison is inactive "
              "(expected until BLOCK 1 places the first one; see spec section 2).")
    for doc, bodies in baseline_docs.items():
        if len(bodies) > 1:
            problems.append(f"{doc}: {len(bodies)} baseline blocks found, at most 1 allowed")
            continue
        try:
            data = parse_baseline_yaml(bodies[0])
        except ValueError as exc:
            problems.append(f"{doc}: could not parse baseline block: {exc}")
            continue
        problems.extend(compare_baseline(doc, data, measured))

    print()
    if problems:
        print(f"FAILED - {len(problems)} problem(s):")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("check_consistency: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
