#!/bin/bash
# SOUL Enforcement Layer - Real-time compliance checking
SOUL_FILE="/home/dell/.openclaw/workspace/SOUL.md"
VIOLATION_LOG="/home/dell/.openclaw/workspace/memory/soul-violations.md"

log_violation() {
    local principle="$1"
    local action="$2"
    local override="$3"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "## Violation: $timestamp" >> "$VIOLATION_LOG"
    echo "- **Principle:** $principle" >> "$VIOLATION_LOG"
    echo "- **Action:** $action" >> "$VIOLATION_LOG"
    echo "- **Override:** $override" >> "$VIOLATION_LOG"
    echo "" >> "$VIOLATION_LOG"
}

check_action() {
    local action="$1"
    local violations=()
    local action_lower=$(echo "$action" | tr '[:upper:]' '[:lower:]')
    
    echo "🔍 SOUL-EL Checking: $action"
    
    # Check 1: Creating code/scripts without CrewAI
    if echo "$action_lower" | grep -qE "(write|create|build|make).*(script|python|code|file)" && \
       ! echo "$action_lower" | grep -qE "(crewai|crew|agent|task|ollama|adapter)"; then
        violations+=("USE CREWAI ORCHESTRATION")
    fi
    
    # Check 2: Claiming done without testing
    if echo "$action_lower" | grep -qE "(done|complete|finished|ready)" && \
       ! echo "$action_lower" | grep -qE "(test|verify|check|validate|confirmed)"; then
        violations+=("DO COMPLETE AND THOROUGH WORK")
    fi
    
    # Check 3: Doing work agents should do
    if echo "$action_lower" | grep -qE "(i will|i'll|let me).*(write|create|build|code)" && \
       ! echo "$action_lower" | grep -qE "(agent|dispatch|delegate|crew)"; then
        violations+=("DELEGATE TO AGENTS")
    fi
    
    # Check 4: Intervening in CrewAI review process
    if echo "$action_lower" | grep -qE "(intervene|override|manual).*(review|process|agent)"; then
        violations+=("DO NOT INTERVENE IN CREWAI REVIEW")
    fi
    
    # Check 5: Claiming success without a Receipt
    if echo "$action_lower" | grep -qE "(done|complete|success|finished|ready)"; then
        if ! echo "$action_lower" | grep -qE "(ls -l|head|cat|receipt|evidence|proof)"; then
            violations+=("PROVIDE VERIFICATION RECEIPT (ls -l + head)")
        fi
    fi
    
    if [ ${#violations[@]} -eq 0 ]; then
        echo "✅ PASS - No SOUL.md violations"
        return 0
    else
        echo "🚨 SOUL-EL VIOLATION DETECTED"
        echo ""
        echo "Violated principles:"
        for v in "${violations[@]}"; do echo "  • $v"; done
        echo ""
        echo "⚠️ MANDATORY: Call 'ask_user' tool now to request an override."
        echo "Question: \"SOUL-EL Violation: ${violations[*]}. Action: $action. Override?\""
        echo "Options: [1] OVERRIDE, [2] CORRECT, [3] UPDATE SOUL"
        echo ""
        return 1
    fi
}

export -f check_action
export -f log_violation