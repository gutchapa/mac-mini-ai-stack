#!/bin/bash
# Agent Status Updater
# Use this to set agent status from within tasks

WORKSPACE="${WORKSPACE:-$HOME/.openclaw/workspace}"
OBS_DIR="$WORKSPACE/observability"

# Create dirs
mkdir -p "$OBS_DIR"/{agents/{coder,researcher,planner,executor,reviewer},logs,metrics}

update_agent() {
    local agent=$1
    local status=$2  # active, idle, error
    local task=$3
    local details=$4
    
    local agent_dir="$OBS_DIR/agents/$agent"
    mkdir -p "$agent_dir"
    
    # Write status JSON
    cat > "$agent_dir/status.json" << EOF
{
  "agent": "$agent",
  "status": "$status",
  "current_task": "$task",
  "details": "$details",
  "since": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "updated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
    
    # Log activity
    echo "[$(date '+%H:%M:%S')] $agent: $status - $task" >> "$OBS_DIR/logs/activity.log"
    
    echo "✅ Updated $agent: $status"
}

log_activity() {
    local message=$1
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $message" >> "$OBS_DIR/logs/activity.log"
}

update_metrics() {
    local metric=$1
    local value=$2
    
    local metrics_file="$OBS_DIR/metrics/daily.json"
    
    # Create file if not exists
    if [ ! -f "$metrics_file" ]; then
        echo '{"date": "'$(date +%Y-%m-%d)'", "tasks_total": 0, "success_rate": "0%", "avg_latency_ms": 0}' > "$metrics_file"
    fi
    
    # Update using jq if available, else skip
    if command -v jq >/dev/null 2>&1; then
        jq ".$metric = $value" "$metrics_file" > "$metrics_file.tmp" && mv "$metrics_file.tmp" "$metrics_file"
    fi
}

# CLI usage
case "${1:-}" in
    update)
        update_agent "$2" "$3" "$4" "$5"
        ;;
    log)
        log_activity "$2"
        ;;
    metric)
        update_metrics "$2" "$3"
        ;;
    *)
        echo "Usage:"
        echo "  $0 update <agent> <status> <task> [details]"
        echo "  $0 log '<message>'"
        echo "  $0 metric <name> <value>"
        echo ""
        echo "Examples:"
        echo "  $0 update coder active 'fixing-bug-123' 'Working on null pointer'"
        echo "  $0 log 'Task completed successfully'"
        echo "  $0 metric tasks_total 42"
        ;;
esac