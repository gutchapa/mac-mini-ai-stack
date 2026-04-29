# 🏫 School Admin Todo App

Complete task management for school administration. Built with workflow-first methodology.

## Features
- **Admin**: Create, edit, reassign, change dates, delete tasks
- **Staff**: Update status (pending → in_progress → completed/blocked), add comments
- **Dashboard**: Totals by status, assignee, overdue filter
- **Notifications**: Status changes, overdue tasks, reassignment alerts
- **Persistence**: localStorage

## Tech
- Single HTML file (no dependencies)
- Gemma 4 generated
- Workflow-driven development

## Workflow
22 nodes covering full lifecycle:
1. Task creation → validation → save → notify
2. Staff assignment → status updates → comments
3. Admin edit/reassign/date-change/delete
4. Dashboard → task list → search/filter

## Files
| File | Purpose |
|------|---------|
| `index.html` | The app |
| `workflow.json` | Structured workflow spec |
| `SYSTEM_PROMPT.md` | System prompt for coding agent |
| `workflow-visual.html` | Visual flowchart |
