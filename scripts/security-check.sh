#!/bin/bash
# Agent Security Extension

WORKSPACE="${WORKSPACE:-$HOME/.openclaw/workspace}"
SECURITY_DIR="$WORKSPACE/security"
LOG_FILE="$SECURITY_DIR/audit.log"

mkdir -p "$SECURITY_DIR"/{policies,audit,reports}

log_security() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$1] $2" >> "$LOG_FILE"
}

check_command() {
    local cmd="$1"
    local agent="${2:-unknown}"
    local blocked=("rm -rf /" "dd if=/dev/zero" ":(){ :|:& };:" ">>/dev/sda")
    
    for pattern in "${blocked[@]}"; do
        if echo "$cmd" | grep -q "$pattern"; then
            echo "🚫 BLOCKED: Dangerous command"
            log_security "CRITICAL" "Agent '$agent' attempted: $cmd"
            return 1
        fi
    done
    echo "✅ Command allowed"
    return 0
}

scan_code() {
    local file=$1
    local issues=0
    echo "🔒 Scanning $file..."
    
    # Check for dangerous patterns
    if grep -qE "eval\s*\(|exec\s*\(|os\.system|subprocess.*shell=True" "$file" 2>/dev/null; then
        echo "  ✗ Dangerous function detected"
        log_security "HIGH" "Dangerous pattern in $file"
        ((issues++))
    fi
    
    # Check for hardcoded secrets
    if grep -qE "API_KEY.*=.*[\"'][^\"']+[\"']|PASSWORD.*=.*[\"'][^\"']+[\"']" "$file" 2>/dev/null; then
        echo "  ⚠ Potential hardcoded secret"
        log_security "MEDIUM" "Possible secret in $file"
        ((issues++))
    fi
    
    return $issues
}

check_agent_perm() {
    local agent=$1
    local target=$2
    
    # Block access to sensitive paths
    local blocked=("/etc" "/usr" "~/.ssh" "~/.aws" "/root")
    for path in "${blocked[@]}"; do
        if [[ "$target" == *"$path"* ]]; then
            echo "🚫 POLICY: Agent cannot access $target"
            log_security "CRITICAL" "Agent '$agent' attempted access to $target"
            return 1
        fi
    done
    echo "✅ Access allowed"
    return 0
}

generate_report() {
    echo "SECURITY REPORT - $(date)"
    echo "======================="
    echo "Events logged: $(wc -l < "$LOG_FILE" 2>/dev/null || echo 0)"
    echo ""
    echo "Recent critical events:"
    grep "CRITICAL" "$LOG_FILE" 2>/dev/null | tail -5 || echo "None"
}

case "${1:-help}" in
    check-cmd) shift; check_command "$@" ;;
    scan) shift; scan_code "$@" ;;
    perm) shift; check_agent_perm "$@" ;;
    report) generate_report ;;
    audit) tail -20 "$LOG_FILE" 2>/dev/null || echo "No audit log" ;;
    *) echo "Usage: check-cmd|scan|perm|report|audit" ;;
esac
