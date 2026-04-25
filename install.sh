#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REQUEST_MCP_REPO_URL:-https://github.com/micaelmalta/request-mcp}"
REF="${REQUEST_MCP_REF:-main}"
SKILLS_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
SKILL_NAME="${REQUEST_MCP_SKILL_NAME:-request-mcp}"
DEST_DIR="$SKILLS_DIR/$SKILL_NAME"
ARCHIVE_URL="${REPO_URL%/}/archive/${REF}.tar.gz"

TMP_DIR="$(mktemp -d)"
ARCHIVE_PATH="$TMP_DIR/request-mcp.tar.gz"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

download() {
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$ARCHIVE_URL" -o "$ARCHIVE_PATH"
  elif command -v wget >/dev/null 2>&1; then
    wget -q "$ARCHIVE_URL" -O "$ARCHIVE_PATH"
  else
    echo "Error: curl or wget is required." >&2
    exit 1
  fi
}

echo "Installing request-mcp skill from $REPO_URL@$REF"
mkdir -p "$SKILLS_DIR"
download
tar -xzf "$ARCHIVE_PATH" -C "$TMP_DIR"

shopt -s nullglob
EXTRACTED_DIRS=("$TMP_DIR"/*)
shopt -u nullglob

if [ "${#EXTRACTED_DIRS[@]}" -ne 1 ] || [ ! -d "${EXTRACTED_DIRS[0]}" ]; then
  echo "Error: expected archive to contain exactly one project directory." >&2
  exit 1
fi

SRC_DIR="${EXTRACTED_DIRS[0]}"
if [ ! -f "$SRC_DIR/SKILL.md" ]; then
  echo "Error: downloaded project does not contain SKILL.md." >&2
  exit 1
fi

rm -rf "$DEST_DIR"
mv "$SRC_DIR" "$DEST_DIR"

echo "Installed request-mcp skill to $DEST_DIR"
echo "To install another branch or tag, run: REQUEST_MCP_REF=your-branch-or-tag ./install.sh"
