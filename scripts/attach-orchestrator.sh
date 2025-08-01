#!/bin/bash
# Attach to the orchestrator tmux session

SESSION_NAME="${1:-team-mcp-demo}"

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "Attaching to orchestrator session '$SESSION_NAME'..."
    echo ""
    echo "Navigation:"
    echo "  Fast switching (no prefix needed):"
    echo "    F1 or Alt+1 - Switch to Leader"
    echo "    F2 or Alt+2 - Switch to Researcher"
    echo "    F3 or Alt+3 - Switch to Writer"
    echo ""
    echo "  Mouse support:"
    echo "    Click any pane to switch"
    echo "    Scroll to navigate history"
    echo ""
    echo "  Standard tmux navigation:"
    echo "    Ctrl+b, 1   - Switch to Leader"
    echo "    Ctrl+b, 2   - Switch to Researcher"
    echo "    Ctrl+b, 3   - Switch to Writer"
    echo "    Ctrl+b, arrows - Navigate between panes"
    echo ""
    echo "  Ctrl+b, d     - Detach from session"
    echo ""
    echo "Claude shortcuts (press '?' in any pane for full list)"
    echo ""
    sleep 2
    tmux attach -t "$SESSION_NAME"
else
    echo "Error: No orchestrator session found"
    echo ""
    echo "Available tmux sessions:"
    tmux ls 2>/dev/null || echo "  (none)"
    echo ""
    echo "Start the orchestrator first with:"
    echo "  python examples/team_mcp_demo_enhanced.py"
    exit 1
fi