#!/usr/bin/env python3
"""
Create GitHub issues from markdown templates using GitHub REST API.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

import requests


def get_github_token() -> str:
    """Extract GitHub token from MCP config."""
    mcp_config_path = Path.home() / ".cursor" / "mcp.json"
    with open(mcp_config_path, "r") as f:
        mcp_config = json.load(f)
        auth_header = mcp_config["mcpServers"]["github"]["headers"]["Authorization"]
        # Handle both "Bearer ghp_..." and "ghp_..." formats
        token = auth_header.replace("Bearer ", "").replace("ghp_", "ghp_")
        return token


def get_repo_info() -> str:
    """Get repository owner/name from git remote."""
    try:
        repo_url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"], text=True
        ).strip()
        if ":" in repo_url:
            repo = repo_url.split(":")[1].replace(".git", "")
        elif "github.com" in repo_url:
            repo = repo_url.split("github.com/")[1].replace(".git", "")
        else:
            raise ValueError("Could not parse repository URL")
        return repo
    except Exception as e:
        print(f"Error getting repo info: {e}")
        sys.exit(1)


def extract_title_and_body(file_path: Path) -> tuple[str, str]:
    """Extract title and body from markdown issue file."""
    content = file_path.read_text()
    lines = content.split("\n")

    # Extract title (first line after # Issue #)
    title = ""
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("# Issue #"):
            title = line.replace("# Issue #", "").strip()
            body_start = i + 1
            break

    # Body is everything after the title
    body = "\n".join(lines[body_start:]).strip()

    return title, body


def create_issue(
    token: str, repo: str, title: str, body: str, labels: List[str]
) -> Optional[Dict]:
    """Create a GitHub issue using REST API."""
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = {
        "title": title,
        "body": body,
        "labels": labels,
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        return response.json()
    else:
        print(f"Error creating issue '{title}': {response.status_code}")
        print(response.text)
        return None


def get_phase_label(issue_num: str) -> str:
    """Get phase label based on issue number."""
    num = int(issue_num)
    if num <= 3:
        return "phase-1-foundation"
    elif num <= 7:
        return "phase-2-services"
    elif num <= 11:
        return "phase-3-api"
    elif num <= 14:
        return "phase-4-testing"
    else:
        return "phase-5-production"


def ensure_labels_exist(token: str, repo: str):
    """Create labels if they don't exist."""
    labels = [
        {"name": "phase-1-foundation", "color": "0e8a16", "description": "Phase 1: Foundation"},
        {"name": "phase-2-services", "color": "1d76db", "description": "Phase 2: Core Services"},
        {"name": "phase-3-api", "color": "b60205", "description": "Phase 3: API Layer"},
        {"name": "phase-4-testing", "color": "d93f0b", "description": "Phase 4: Testing & Polish"},
        {"name": "phase-5-production", "color": "5319e7", "description": "Phase 5: Production Readiness"},
        {"name": "backend", "color": "ededed", "description": "Backend development"},
    ]

    url = f"https://api.github.com/repos/{repo}/labels"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    for label in labels:
        # Try to create label (will fail if exists, which is fine)
        response = requests.post(url, headers=headers, json=label)
        if response.status_code in [201, 422]:  # 422 = already exists
            continue
        else:
            print(f"Warning: Could not create label {label['name']}: {response.status_code}")


def main():
    """Main function to create all issues."""
    issues_dir = Path(__file__).parent
    issue_files = sorted(issues_dir.glob("0*.md"))

    if not issue_files:
        print("No issue files found!")
        sys.exit(1)

    token = get_github_token()
    repo = get_repo_info()

    print(f"Repository: {repo}")
    print(f"Found {len(issue_files)} issue files\n")

    # Ensure labels exist
    print("Creating labels...")
    ensure_labels_exist(token, repo)
    print("Labels ready.\n")

    # Create issues
    created = []
    failed = []

    for issue_file in issue_files:
        # Extract issue number from filename
        match = re.match(r"0*(\d+)-", issue_file.name)
        if not match:
            print(f"Skipping {issue_file.name} (could not parse issue number)")
            continue

        issue_num = match.group(1)
        title, body = extract_title_and_body(issue_file)
        phase_label = get_phase_label(issue_num)
        labels = [phase_label, "backend"]

        print(f"Creating issue #{issue_num}: {title}...")
        result = create_issue(token, repo, title, body, labels)

        if result:
            created.append((issue_num, result["number"], result["html_url"]))
            print(f"✓ Created as issue #{result['number']}: {result['html_url']}\n")
        else:
            failed.append((issue_num, title))
            print(f"✗ Failed\n")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Created: {len(created)} issues")
    if created:
        print("\nCreated issues:")
        for num, gh_num, url in created:
            print(f"  #{gh_num}: {url}")
    if failed:
        print(f"\nFailed: {len(failed)} issues")
        for num, title in failed:
            print(f"  Issue #{num}: {title}")


if __name__ == "__main__":
    main()

