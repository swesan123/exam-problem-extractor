# GitHub Issues for Exam Problem Extractor

This directory contains structured issue templates based on the technical design document. These issues are organized by implementation phase and can be used to track development progress.

## Issue List

### Phase 1: Foundation
1. **[Issue #1: Project Structure and Configuration Setup](./001-project-structure.md)**
2. **[Issue #2: Pydantic Models for All Endpoints](./002-pydantic-models.md)**
3. **[Issue #3: Utility Functions Implementation](./003-utility-functions.md)**

### Phase 2: Core Services
4. **[Issue #4: OCR Service Implementation](./004-ocr-service.md)**
5. **[Issue #5: Embedding Service Implementation](./005-embedding-service.md)**
6. **[Issue #6: Retrieval Service Implementation](./006-retrieval-service.md)**
7. **[Issue #7: Generation Service Implementation](./007-generation-service.md)**

### Phase 3: API Layer
8. **[Issue #8: OCR Route Endpoint Implementation](./008-ocr-route.md)**
9. **[Issue #9: Embed Route Endpoint Implementation](./009-embed-route.md)**
10. **[Issue #10: Retrieve Route Endpoint Implementation](./010-retrieve-route.md)**
11. **[Issue #11: Generate Route Endpoint Implementation](./011-generate-route.md)**

### Phase 4: Testing & Polish
12. **[Issue #12: Unit Tests for Services](./012-unit-tests.md)**
13. **[Issue #13: Integration Tests for Routes](./013-integration-tests.md)**
14. **[Issue #14: Error Handling and Logging Setup](./014-error-handling-logging.md)**

### Phase 5: Production Readiness
15. **[Issue #15: Production Readiness and Health Checks](./015-production-readiness.md)**

## How to Use These Issues

### Option 1: Create Issues Manually
1. Copy the content from each issue file
2. Create a new GitHub issue
3. Paste the content as the issue description
4. Add appropriate labels (e.g., `phase-1`, `backend`, `enhancement`)

### Option 2: Use GitHub CLI
If you have GitHub CLI installed, you can create issues programmatically:

```bash
# Create all issues from the templates
for file in .github/ISSUES/*.md; do
  gh issue create --title "$(head -n 1 $file | sed 's/# Issue #//')" --body-file "$file"
done
```

### Option 3: Use GitHub API
You can use the GitHub REST API to create issues programmatically from these templates.

## Issue Dependencies

Some issues depend on others being completed first:

- **Issue #2** depends on **Issue #1** (project structure)
- **Issue #3** can be done in parallel with **Issue #2**
- **Issues #4-7** (services) depend on **Issues #1-3** (foundation)
- **Issues #8-11** (routes) depend on **Issues #4-7** (services) and **Issue #2** (models)
- **Issues #12-13** (tests) depend on all previous issues
- **Issue #14** can be done incrementally alongside other issues
- **Issue #15** depends on all previous issues

## Labels Recommendation

Consider adding these labels to your GitHub repository:
- `phase-1-foundation`
- `phase-2-services`
- `phase-3-api`
- `phase-4-testing`
- `phase-5-production`
- `backend`
- `enhancement`
- `documentation`

## Milestones

You can create milestones for each phase:
- **Milestone 1: Foundation** (Issues #1-3)
- **Milestone 2: Core Services** (Issues #4-7)
- **Milestone 3: API Layer** (Issues #8-11)
- **Milestone 4: Testing & Polish** (Issues #12-14)
- **Milestone 5: Production Ready** (Issue #15)

## Notes

- Each issue includes acceptance criteria that should be checked off as work progresses
- Issues reference specific sections of the DESIGN.md document
- Issues are designed to be self-contained and actionable
- Feel free to break down large issues into smaller sub-issues if needed

