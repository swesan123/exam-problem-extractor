#!/bin/bash
# Script to create GitHub issues from markdown templates
# Requires GitHub CLI (gh) to be installed and authenticated

set -e

ISSUES_DIR=".github/ISSUES"
REPO=$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/')

echo "Creating GitHub issues for repository: $REPO"
echo ""

# Array of issue files in order
ISSUES=(
  "001-project-structure.md"
  "002-pydantic-models.md"
  "003-utility-functions.md"
  "004-ocr-service.md"
  "005-embedding-service.md"
  "006-retrieval-service.md"
  "007-generation-service.md"
  "008-ocr-route.md"
  "009-embed-route.md"
  "010-retrieve-route.md"
  "011-generate-route.md"
  "012-unit-tests.md"
  "013-integration-tests.md"
  "014-error-handling-logging.md"
  "015-production-readiness.md"
)

# Phase labels
declare -A PHASE_LABELS=(
  ["001"]="phase-1-foundation"
  ["002"]="phase-1-foundation"
  ["003"]="phase-1-foundation"
  ["004"]="phase-2-services"
  ["005"]="phase-2-services"
  ["006"]="phase-2-services"
  ["007"]="phase-2-services"
  ["008"]="phase-3-api"
  ["009"]="phase-3-api"
  ["010"]="phase-3-api"
  ["011"]="phase-3-api"
  ["012"]="phase-4-testing"
  ["013"]="phase-4-testing"
  ["014"]="phase-4-testing"
  ["015"]="phase-5-production"
)

# Extract issue number from filename
get_issue_num() {
  echo "$1" | sed 's/^0*\([0-9]*\)-.*/\1/'
}

# Extract title from markdown file
get_title() {
  head -n 1 "$1" | sed 's/^# Issue #//'
}

# Create labels if they don't exist
create_labels() {
  echo "Creating labels..."
  gh label create "phase-1-foundation" --color "0e8a16" --description "Phase 1: Foundation" --force 2>/dev/null || true
  gh label create "phase-2-services" --color "1d76db" --description "Phase 2: Core Services" --force 2>/dev/null || true
  gh label create "phase-3-api" --color "b60205" --description "Phase 3: API Layer" --force 2>/dev/null || true
  gh label create "phase-4-testing" --color "d93f0b" --description "Phase 4: Testing & Polish" --force 2>/dev/null || true
  gh label create "phase-5-production" --color "5319e7" --description "Phase 5: Production Readiness" --force 2>/dev/null || true
  gh label create "backend" --color "ededed" --description "Backend development" --force 2>/dev/null || true
  echo "Labels created."
  echo ""
}

# Create milestones if they don't exist
create_milestones() {
  echo "Creating milestones..."
  gh api repos/:owner/:repo/milestones -X POST -f title="Phase 1: Foundation" -f description="Foundation setup: project structure, models, utilities" 2>/dev/null || true
  gh api repos/:owner/:repo/milestones -X POST -f title="Phase 2: Core Services" -f description="Core service layer: OCR, embedding, retrieval, generation" 2>/dev/null || true
  gh api repos/:owner/:repo/milestones -X POST -f title="Phase 3: API Layer" -f description="API endpoints: routes and request handling" 2>/dev/null || true
  gh api repos/:owner/:repo/milestones -X POST -f title="Phase 4: Testing & Polish" -f description="Testing, error handling, and polish" 2>/dev/null || true
  gh api repos/:owner/:repo/milestones -X POST -f title="Phase 5: Production Ready" -f description="Production readiness and deployment" 2>/dev/null || true
  echo "Milestones created."
  echo ""
}

# Main function
main() {
  # Check if gh is installed
  if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed."
    echo "Install it from: https://cli.github.com/"
    exit 1
  fi

  # Check if authenticated
  if ! gh auth status &> /dev/null; then
    echo "Error: Not authenticated with GitHub CLI."
    echo "Run: gh auth login"
    exit 1
  fi

  # Create labels and milestones
  read -p "Create labels and milestones? (y/n) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    create_labels
    create_milestones
  fi

  # Create issues
  echo "Creating issues..."
  echo ""
  
  for issue_file in "${ISSUES[@]}"; do
    file_path="$ISSUES_DIR/$issue_file"
    
    if [ ! -f "$file_path" ]; then
      echo "Warning: $file_path not found, skipping..."
      continue
    fi
    
    issue_num=$(get_issue_num "$issue_file")
    title=$(get_title "$file_path")
    phase_label="${PHASE_LABELS[$issue_num]}"
    
    echo "Creating issue #$issue_num: $title"
    
    # Create issue with labels
    gh issue create \
      --title "$title" \
      --body-file "$file_path" \
      --label "$phase_label,backend" \
      --repo "$REPO"
    
    echo "✓ Created"
    echo ""
  done
  
  echo "All issues created successfully!"
}

main

