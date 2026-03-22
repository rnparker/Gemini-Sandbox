# Project: Gemini-Sandbox - Market Pulse Dashboard

## 1. Context & Persona
- **Owner:** Rob, CTO at Kootenay Savings Credit Union (KSCU).
- **Location:** Golden, BC (Mountain Time).
- **Operating Mode:** "Hobbyist Mentor" — Maintain high professional standards for code quality and documentation in an experimental sandbox.
- **Mission:** Modernizing data pipelines and visualization for credit union market intelligence, specifically focusing on the CVCU/KSCU post-merger integration landscape.

## 2. Technical Environment & Constraints
- **Host OS:** Windows.
- **Shell:** PowerShell 5.1 (Native). **STRICT CONSTRAINT:** Never use Bash syntax (no `&&`, `||`, or `export`). Use `;` for sequencing and `$env:VAR` for environment variables.
- **Language:** Python 3.10+.
- **CI/CD:** GitHub Actions (scheduled for 8:00 AM MT / 14:00 UTC).
- **Hosting:** GitHub Pages serving from the `/docs` directory.

## 3. Data Architecture
- **Wholesale Yields:** Bank of Canada Valet API.
  - **CAN 2Y:** `BD.CDN.2YR.DQ.YLD`
  - **CAN 5Y:** `BD.CDN.5YR.DQ.YLD`
- **Retail Rates:** Ratehub API.
  - **Schema:** Detailed parsing logic and JSON structure are defined in `@MORTGAGE_SPEC.md`.

## 4. Project Glossary & Logic
- **Yield Spread:** The difference between `CAN 2Y` and `CAN 5Y` bond yields.
- **Lending Margin:** Calculated as: `Best 5Y Fixed Rate` (from Ratehub) minus `CAN 5Y Bond Yield` (from BoC).
- **Inversion:** Any negative spread value. On dashboard charts, these must be visually distinct (e.g., **Red** line segments or points).

## 5. Coding & Governance Standards
- **Pull Requests (PR):** All code changes must be submitted via PR. Use feature branches (e.g., `feat/`, `fix/`).
- **Housekeeping:** After a successful merge, the feature branch must be deleted to maintain repository hygiene.
- **Validation:** Scripts must include "Sanity Checks" to validate API responses (e.g., flag rates > 15% or < 1% as anomalies).
- **Transparency:** The dashboard footer must include a "Last Updated" timestamp in Mountain Time.