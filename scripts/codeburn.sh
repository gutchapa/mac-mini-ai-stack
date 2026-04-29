#!/bin/bash
# CODEBURN - Tool Usage Auditor
# Flags inappropriate use of external APIs when local tools suffice

WORKSPACE="${WORKSPACE:-$HOME/.openclaw/workspace}"
BURN_LOG="$WORKSPACE/memory/codeburn-violations.md"
mkdir -p "$WORKSPACE/memory"

log_burn() {
    local tool="$1"
    local reason="$2"
    local alternative="$3"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "## 🔥 CodeBurn Violation: $timestamp" >> "$BURN_LOG"
    echo "- **Tool Used:** $tool" >> "$BURN_LOG"
    echo "- **Violation:** $reason" >> "$BURN_LOG"
    echo "- **Should Have Used:** $alternative" >> "$BURN_LOG"
    echo "" >> "$BURN_LOG"
    
    echo "🔥 CODEBURN FLAGGED: $tool"
    echo "   Reason: $reason"
    echo "   Use instead: $alternative"
}

# Check if code_execution was used for simple math/calculations
check_code_execution() {
    local task="$1"
    local model="$2"
    local provider="$3"
    
    # Flag if used for simple calculations that could be done locally
    if echo "$task" | grep -qE "(calculate|math|speed|distance|formula|haversine|computation)"; then
        if [ "$provider" = "xai" ] || [ "$model" = "grok-4-1-fast" ]; then
            log_burn "code_execution ($model)" "Used xAI/Grok for calculations instead of local Python" "exec: python3 -c '...' or local bash math"
            return 1
        fi
    fi
    
    # Flag if used for file searches when exec/find would work
    if echo "$task" | grep -qE "(search|find|locate|list files)"; then
        if [ "$provider" = "xai" ] || [ "$model" = "grok-4-1-fast" ]; then
            log_burn "code_execution ($model)" "Used xAI/Grok for file operations" "exec: find /path -name '...'"
            return 1
        fi
    fi
    
    echo "✅ CodeBurn PASS - No tool violations detected"
    return 0
}

# Check web_search usage
check_web_search() {
    local query="$1"
    
    # Flag simple lookups that could use cached data or local files
    if echo "$query" | grep -qE "(nearby|location|coordinates|distance|petrol|restaurant)" && \
       [ -f "$WORKSPACE/.route_cache.json" ]; then
        log_burn "web_search" "Used external API when cached route data available" "Use cached .route_cache.json or local nearby.js"
        return 1
    fi
    
    echo "✅ CodeBurn PASS - web_search justified"
    return 0
}

# Audit a completed action
audit_action() {
    local action_type="$1"
    shift
    
    case "$action_type" in
        code_execution)
            check_code_execution "$@"
            ;;
        web_search)
            check_web_search "$@"
            ;;
        *)
            echo "Unknown action type: $action_type"
            return 0
            ;;
    esac
}

# Show burn report
show_burn_report() {
    echo "🔥 CODEBURN AUDIT REPORT"
    echo "========================"
    
    if [ ! -f "$BURN_LOG" ]; then
        echo "No violations recorded. Clean slate! ✅"
        return
    fi
    
    local violations=$(grep -c "## 🔥 CodeBurn Violation" "$BURN_LOG" 2>/dev/null || echo "0")
    echo "Total Violations: $violations"
    echo ""
    
    if [ "$violations" -gt 0 ]; then
        echo "Recent violations:"
        tail -20 "$BURN_LOG"
        echo ""
        echo "⚠️  Summary by tool:"
        grep "Tool Used:" "$BURN_LOG" | sort | uniq -c | sort -rn
    fi
}

# Main
case "${1:-}" in
    audit)
        shift
        audit_action "$@"
        ;;
    check-code-exec)
        shift
        check_code_execution "$@"
        ;;
    check-web)
        shift
        check_web_search "$@"
        ;;
    report)
        show_burn_report
        ;;
    *)
        echo "Usage: codeburn.sh audit <action_type> [args...]"
        echo "       codeburn.sh check-code-exec <task> <model> <provider>"
        echo "       codeburn.sh check-web <query>"
        echo "       codeburn.sh report"
        ;;
esac
