
# PlatformLens - AI-Assisted-Coverage-Tracker


> *Find what your platform can't see.*

Cross-platform codebases silently accumulate blind spots. Code gets wrapped in platform-specific guards, tests never get written, and functionality quietly disappears on certain targets.
Nobody notices until a customer does.

PlatformLens scans any C/C++ codebase and finds blind spots for eg. code that's been guarded out, tests that skip your platform, and functions that exist on one platform but not another.
An AI reasoning layer then explains *why* each gap exists and suggests what to do about it.

---

## What It Finds

**Code Gaps** — Code blocks conditionally excluded on your target platform via preprocessor guards. These compile fine everywhere else but are dead code on your platform.

**Test Gaps** — Source files with no corresponding test that runs on your target platform. The code ships, but nobody's verified it works.

**Coverage Gaps** — Functions and lines that are never exercised during test runs on your target platform, surfaced via `llvm-cov` integration.

**Symbol Gaps** *(roadmap)* — Functionality that exists in one platform's build but is entirely absent from another's.

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--path` | Repo, folder, or file to scan | required |
| `--platform` | Target platform to check | `aix` |
| `--output` | Output report filename | `platformlens_report.md` |
| `--bob` | Enable AI reasoning layer | off |
| `--top` | Number of gaps to send to AI | `10` |

---

## Why This Exists

Most coverage tools tell you *how much* is covered. PlatformLens tells you *why* something isn't covered on your specific platform, and what to do about it. The static analysis finds the gaps. The AI layer makes them actionable.
