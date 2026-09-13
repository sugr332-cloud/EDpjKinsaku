"""Phase F dangling reference check (F-2).

Scans docs/**/*.md, README.md, app/**/*.py, scripts/**/*.py, and tests/**/*.py
for ``.md`` filename mentions and verifies each actually resolves to a file in
this repository. See docs/PHASE_F_IMPLEMENTATION_DOC_CONSISTENCY_SPEC_V0.1.md
section 3-4 for the full rules this implements. Read-only: it never edits the
files it scans, and never rewrites docs to fix what it finds (that is BLOCK
1/2/6's job, not F's - spec section 0).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ALLOWLIST_PATH = REPO_ROOT / ".github" / "known_dangling.txt"

SCAN_GLOBS = ["docs/**/*.md", "app/**/*.py", "scripts/**/*.py", "tests/**/*.py"]
EXCLUDED_DIR_PARTS = {"__pycache__", ".git"}

URL_RE = re.compile(r'https?://[^\s)"\'`<>]*')

# A .md reference's character run ([A-Za-z0-9_./-]+, spec section 3), optionally continued across
# a hard line-wrap. Found by running this against the real repository: a long filename inside an
# 80-column-wrapped docstring/comment can be split by a bare newline (optionally followed by
# leading indentation and/or a comment marker), which a single-line-unaware regex sees as the
# run ending early and starting a bogus new one from the fragment after the wrap
# (app/backtest/trade_market_persistence.py's own docstring is the real example that surfaced
# this). The (?<=_)\n... lookbehind only allows that join when the character right before the
# newline is specifically an underscore - this repo's own naming convention for the long
# SCREAMING_SNAKE_CASE spec filenames the wrap breaks in the middle of - never a plain letter,
# digit, dot, or hyphen. A broader class also matched prose: an em dash ("... placeholder --")
# ending one comment line right before an unrelated reference starting the next fused into one
# bogus token under a class that included hyphens, and a following-word coincidence did the same
# under a class that allowed any letter. Restricting the trigger to underscore is what tells a
# genuinely wrapped identifier apart from two unrelated lines that simply sit next to each other.
# Allowlisting any of these bad matches would hide a real extraction bug instead of fixing it,
# which is why they are handled here and not there.
REF_TOKEN_RE = re.compile(
    r'[A-Za-z0-9_./-]+(?:(?<=_)\n[ \t]*#?[ \t]*[A-Za-z0-9_./-]+)*\.md'
)
LINE_JOIN_RE = re.compile(r'\n[ \t]*#?[ \t]*')


def iter_scan_files(repo_root: Path):
    seen: set[Path] = set()
    for pattern in SCAN_GLOBS:
        for path in repo_root.glob(pattern):
            if any(part in EXCLUDED_DIR_PARTS for part in path.parts):
                continue
            if path not in seen:
                seen.add(path)
                yield path
    readme = repo_root / "README.md"
    if readme.exists() and readme not in seen:
        yield readme


def extract_references(text: str) -> set[str]:
    """The set of distinct, cleaned .md references mentioned in ``text``."""
    masked = URL_RE.sub("", text)  # a .md at the tail of a URL is not a bare filename reference
    refs: set[str] = set()
    for match in REF_TOKEN_RE.finditer(masked):
        raw = match.group(0)
        if "*" in raw:
            continue  # a wildcard mention such as "*.md", not a concrete reference
        cleaned = LINE_JOIN_RE.sub("", raw)
        refs.add(cleaned)
    return refs


def resolves(repo_root: Path, ref: str) -> bool:
    """Spec section 3's three-step resolution order."""
    candidates = [repo_root / "docs" / ref, repo_root / ref]
    if ref.startswith("docs/"):
        candidates.append(repo_root / ref)
    return any(candidate.exists() for candidate in candidates)


def find_dangling(repo_root: Path) -> dict[str, set[str]]:
    """Maps each dangling reference to the files that mention it."""
    by_ref: dict[str, set[str]] = {}
    for path in iter_scan_files(repo_root):
        text = path.read_text(encoding="utf-8", errors="replace")
        for ref in extract_references(text):
            by_ref.setdefault(ref, set()).add(str(path.relative_to(repo_root)))
    return {ref: files for ref, files in by_ref.items() if not resolves(repo_root, ref)}


def load_allowlist(allowlist_path: Path) -> set[str]:
    if not allowlist_path.exists():
        return set()
    entries = set()
    for raw_line in allowlist_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        ref = line.split("#", 1)[0].strip()
        if ref:
            entries.add(ref)
    return entries


def main() -> int:
    dangling = find_dangling(REPO_ROOT)
    allowlist = load_allowlist(ALLOWLIST_PATH)

    new_dangling = sorted(set(dangling) - allowlist)
    stale_allowlist = sorted(allowlist - set(dangling))

    problems: list[str] = []

    if new_dangling:
        print(f"New dangling reference(s) not in {ALLOWLIST_PATH.name} ({len(new_dangling)}):")
        for ref in new_dangling:
            files = sorted(dangling[ref])[:3]
            print(f"  - {ref}  (e.g. {', '.join(files)})")
        problems.append(f"{len(new_dangling)} new dangling reference(s)")

    if stale_allowlist:
        print(f"Stale allowlist entr(y/ies) that are no longer dangling ({len(stale_allowlist)}):")
        for ref in stale_allowlist:
            print(f"  - {ref}")
        problems.append(f"{len(stale_allowlist)} stale allowlist entr(y/ies)")

    print()
    if problems:
        print(f"FAILED - {'; '.join(problems)}")
        return 1

    print(f"check_dangling_refs: OK ({len(dangling)} known dangling reference(s), all allowlisted)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
