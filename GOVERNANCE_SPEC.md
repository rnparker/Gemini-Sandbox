# Specification: Development Workflow & Governance

## 1. Objective
Ensure high professional standards, maintain repository hygiene, and enforce a consistent development lifecycle for the Market Pulse Dashboard project.

## 2. Branching Strategy
- **Main Branch (`main`):** Represents the stable, production-ready state. Direct commits to `main` are prohibited except for emergency hotfixes or automated data updates.
- **Feature Branches:** All work must be performed in dedicated branches.
  - Prefix: `feat/` for new features, `fix/` for bug fixes, `chore/` for maintenance.
  - Example: `feat/chart-annotations`.

## 3. Pull Request (PR) Process
All code changes must be submitted via PR.
1. **Creation:** Provide a clear title and detailed description of the changes.
2. **Review:** PRs should be verified via visual inspection (PR Previews) and automated tests.
3. **Iteration:** Update the PR with comments capturing changes made with each modification, not just the initial change.
4. **Merging:** Use "Squash and Merge" or "Rebase" to maintain a clean history.
5. **Housekeeping:** After a successful merge, the feature branch **must** be deleted immediately.

## 4. Issue Management
- **Tracking:** Every feature or bug should have a corresponding GitHub Issue.
- **Resolution:** PRs should include "Closes #IssueNumber" in the description to automate issue closure upon merging.
- **Finality:** Ensure all related issues are closed before concluding a task.

## 5. Automated Validation
- **Tests:** Scripts must include sanity checks for API responses.
- **CI/CD:** Every PR triggers a "PR Preview" workflow which:
  - Runs the full test suite.
  - Generates a live dashboard preview.
  - Performs a sample data fetch/AI analysis run.

## 6. Project Context
- **Mountain Time (MT):** All timestamps and "Last Updated" footers must use MT.
- **PowerShell:** Command execution must adhere to native PowerShell 5.1 syntax (e.g., `;` instead of `&&`).
- **Safety:** Credentials and API keys must never be logged or committed.
