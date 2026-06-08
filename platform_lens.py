import re
import os
import json
import argparse
from pathlib import Path
from datetime import datetime

# ── Config ─────────────────────────────────────────────────────────────────────

PLATFORM_GUARDS = {
    "aix": {
        "exclude_patterns": [
            r"#if\s+SANITIZER_LINUX\b",
            r"#if\s+.*SANITIZER_LINUX\s*&&",
            r"#elif\s+SANITIZER_LINUX\b",
            r"#if\s+!SANITIZER_AIX\b",
            r"#ifdef\s+__linux__",
        ],
        "include_patterns": [
            r"SANITIZER_AIX",
            r"SI_NOT_AIX",
            r"__AIX__",
        ],
        "label": "AIX",
    }
}

SOURCE_EXTENSIONS = {".c", ".cpp", ".h", ".inc"}

AIX_LIT_PATTERNS = [
    r"//\s*REQUIRES:.*\baix\b",
    r"//\s*REQUIRES:.*target=\{\{.*aix.*\}\}",
]

# ── Scanner ─────────────────────────────────────────────────────────────────────

def scan_guards(path: Path, platform: str) -> list[dict]:
    """Scan files for platform guard gaps."""
    config = PLATFORM_GUARDS[platform]
    gaps = []

    files = [
        f for f in path.rglob("*")
        if f.suffix in SOURCE_EXTENSIONS and f.is_file()
    ]

    for filepath in files:
        try:
            lines = filepath.read_text(errors="replace").splitlines()
        except Exception:
            continue

        for i, line in enumerate(lines, start=1):
            for pattern in config["exclude_patterns"]:
                if re.search(pattern, line):
                    # Check if AIX is already considered nearby (±5 lines)
                    context = "\n".join(lines[max(0, i-5): min(len(lines), i+10)])
                    aix_nearby = any(
                        re.search(p, context)
                        for p in config["include_patterns"]
                    )
                    gaps.append({
                        "file": str(filepath),
                        "line": i,
                        "guard": line.strip(),
                        "context": context,
                        "aix_considered": aix_nearby,
                        "classification": None,   # filled by Bob layer
                        "suggestion": None,
                    })
                    break  # one gap per line is enough

    return gaps


def audit_lit_tests(path: Path) -> dict:
    """Find test files and check which have AIX coverage."""
    test_files = [
        f for f in path.rglob("*.cpp")
        if "test" in str(f).lower() and f.is_file()
    ]

    covered, uncovered = [], []

    for tf in test_files:
        try:
            # Only check first 10 lines for REQUIRES directives
            head = "\n".join(tf.read_text(errors="replace").splitlines()[:10])
        except Exception:
            continue

        has_aix = any(re.search(p, head) for p in AIX_LIT_PATTERNS)
        (covered if has_aix else uncovered).append(str(tf))

    return {"covered": covered, "uncovered": uncovered}


# ── Report ──────────────────────────────────────────────────────────────────────

def write_markdown_report(
    gaps: list[dict],
    lit_audit: dict,
    platform: str,
    scan_path: str,
    output_path: Path,
):
    label = PLATFORM_GUARDS[platform]["label"]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    oversight   = [g for g in gaps if not g["aix_considered"]]
    acknowledged = [g for g in gaps if g["aix_considered"]]

    lines = [
        f"# PlatformLens Report — {label}",
        f"**Scanned:** `{scan_path}`  ",
        f"**Generated:** {timestamp}  ",
        f"**Platform:** {label}",
        "",
        "---",
        "",
        "## Summary",
        "",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Total guard gaps found | {len(gaps)} |",
        f"| Likely oversights (no AIX consideration nearby) | {len(oversight)} |",
        f"| AIX already acknowledged nearby | {len(acknowledged)} |",
        f"| Test files with AIX coverage | {len(lit_audit['covered'])} |",
        f"| Test files without AIX coverage | {len(lit_audit['uncovered'])} |",
        "",
        "---",
        "",
        "## High Priority Gaps (No AIX Consideration)",
        "",
    ]

    for i, gap in enumerate(oversight[:20], start=1):  # cap at 20 for readability
        rel = os.path.relpath(gap["file"], scan_path)
        lines += [
            f"### Gap {i} — `{rel}` line {gap['line']}",
            "",
            f"```cpp",
            gap["guard"],
            f"```",
            "",
        ]
        if gap["classification"]:
            lines += [f"**Bob Classification:** {gap['classification']}", ""]
        if gap["suggestion"]:
            lines += [f"**Bob Suggestion:** {gap['suggestion']}", ""]
        lines.append("---")
        lines.append("")

    lines += [
        "## LIT Test Gaps (No AIX Coverage)",
        "",
    ]
    for tf in lit_audit["uncovered"][:20]:
        lines.append(f"- `{os.path.relpath(tf, scan_path)}`")

    lines += [
        "",
        "---",
        "",
        "## Roadmap",
        "",
        "- [ ] LIT test auditor full integration",
        "- [ ] llvm-cov JSON ingestion for runtime coverage",
        "- [ ] Symbol diff across platform builds",
        "- [ ] Nightly CI hook — diff report against previous run",
        "- [ ] Feed gap database into LLVM Regression Triage Agent RAG",
    ]

    output_path.write_text("\n".join(lines))
    print(f"[PlatformLens] Report written → {output_path}")


# ── Bob Stub ────────────────────────────────────────────────────────────────────

def bob_classify_gaps(gaps: list[dict], top_n: int = 10) -> list[dict]:
    """
    Stub for Bob integration.
    
    In the real tool, each gap's context is sent to Bob via Bob Shell
    with the three-prompt chain:
      1. Classify: oversight / intentional / linux-only
      2. Fix pattern: find nearest AIX equivalent
      3. Prioritize: group by root cause family

    Replace the stub values below with actual Bob Shell calls:
        import subprocess
        result = subprocess.run(
            ["bob", "--prompt", prompt],
            capture_output=True, text=True
        )
        classification = result.stdout.strip()
    """
    oversight_gaps = [g for g in gaps if not g["aix_considered"]]

    for gap in oversight_gaps[:top_n]:
        # ── Stub: replace with real Bob Shell call ──
        gap["classification"] = "⚠️  Likely oversight — Bob analysis pending"
        gap["suggestion"] = "Feed `gap['context']` to Bob with classification prompt."

    return gaps


# ── CLI ─────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="PlatformLens — Cross-platform coverage gap scanner"
    )
    parser.add_argument(
        "--path", required=True,
        help="Repo, folder, or file to scan"
    )
    parser.add_argument(
        "--platform", default="aix", choices=list(PLATFORM_GUARDS.keys()),
        help="Target platform to check coverage for (default: aix)"
    )
    parser.add_argument(
        "--output", default="platformlens_report.md",
        help="Output Markdown report path"
    )
    parser.add_argument(
        "--bob", action="store_true",
        help="Enable Bob analysis layer (requires Bob Shell)"
    )
    parser.add_argument(
        "--top", type=int, default=10,
        help="Number of top gaps to send to Bob (default: 10)"
    )
    args = parser.parse_args()

    scan_path = Path(args.path).resolve()
    output_path = Path(args.output)

    print(f"[PlatformLens] Scanning: {scan_path}")
    print(f"[PlatformLens] Platform: {args.platform.upper()}")

    # Phase 1 — Guard scan
    print("[PlatformLens] Running guard scanner...")
    gaps = scan_guards(scan_path, args.platform)
    print(f"[PlatformLens] Found {len(gaps)} guard gaps")

    # Phase 2 — LIT test audit
    print("[PlatformLens] Running LIT test audit...")
    lit_audit = audit_lit_tests(scan_path)
    print(f"[PlatformLens] {len(lit_audit['covered'])} tests with AIX coverage, "
          f"{len(lit_audit['uncovered'])} without")

    # Phase 3 — Bob layer (optional)
    if args.bob:
        print(f"[PlatformLens] Sending top {args.top} gaps to Bob...")
        gaps = bob_classify_gaps(gaps, top_n=args.top)

    # Phase 4 — Report
    write_markdown_report(gaps, lit_audit, args.platform, str(scan_path), output_path)

    # Also dump raw JSON for downstream tools
    json_path = output_path.with_suffix(".json")
    json_path.write_text(json.dumps(gaps, indent=2))
    print(f"[PlatformLens] Raw JSON → {json_path}")


if __name__ == "__main__":
    main()
