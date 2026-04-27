#!/bin/bash
# Install git pre-push hook for AI log submission
set -e

HOOK_FILE=".git/hooks/pre-push"

cat > "$HOOK_FILE" << 'EOF'
#!/bin/bash
# Submit AI logs to grading server before push
if command -v python >/dev/null 2>&1; then
  python scripts/submit_log.py
elif command -v python3 >/dev/null 2>&1; then
  python3 scripts/submit_log.py
elif [ -x ".venv/Scripts/python.exe" ]; then
  .venv/Scripts/python.exe scripts/submit_log.py
elif command -v powershell.exe >/dev/null 2>&1; then
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/submit_log.ps1
elif command -v pwsh >/dev/null 2>&1; then
  pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/submit_log.ps1
else
  echo "[ai-log] No Python or PowerShell runtime found - skipping submission." >&2
fi
exit 0  # Never block push
EOF

chmod +x "$HOOK_FILE"
echo "[ai-log] Git pre-push hook installed."

# Create .ai-log directory if not exists
mkdir -p .ai-log
touch .ai-log/.gitkeep

echo "[ai-log] Setup complete. Configure AI_LOG_SERVER in your .env file."
