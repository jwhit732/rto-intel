# RTO Intel — BMAD Project Kickstart Package

## What This Is

Pre-built BMAD planning artifacts for building an AI-powered RTO intelligence pipeline. These documents are designed to feed directly into the BMAD Method workflow with Claude Code.

## Documents Included

| File | BMAD Phase | Purpose |
|------|-----------|---------|
| `project-brief.md` | Phase 1 (Analysis) | Problem statement, vision, sources, constraints |
| `PRD.md` | Phase 2 (Planning) | Requirements, user stories, epic breakdown, data model |
| `architecture.md` | Phase 3 (Solutioning) | Tech stack, system design, component design, execution flow |
| `project-context.md` | Cross-cutting | Implementation rules and conventions for all agents |

## How To Use With BMAD

### Setup (10 minutes)

```bash
# 1. Create your project directory
mkdir rto-intel && cd rto-intel

# 2. Install BMAD
npx bmad-method install
# Select: BMad Method module
# Select: Claude Code as your AI tool

# 3. Copy these files into the BMAD output directory
cp project-brief.md _bmad-output/planning-artifacts/
cp PRD.md _bmad-output/planning-artifacts/
cp architecture.md _bmad-output/planning-artifacts/
cp project-context.md _bmad-output/
```

### Recommended BMAD Workflow

Since the planning documents are already created, you can skip most of Phases 1-3 and jump ahead. But I recommend these validation steps:

#### Step 1: Validate Architecture (15 min)
```
# In Claude Code, fresh chat:
/bmad-bmm-check-implementation-readiness
```
This runs the Architect agent's validation to check that PRD, Architecture, and project context are coherent. Fix any gaps it identifies.

#### Step 2: Generate Epics & Stories (20 min)
```
# In Claude Code, fresh chat:
/bmad-bmm-create-epics-and-stories
```
The PM agent will use the PRD and Architecture to create detailed story files with acceptance criteria. The epic breakdown in the PRD gives it a head start.

#### Step 3: Sprint Planning (5 min)
```
# In Claude Code, fresh chat:
/bmad-bmm-sprint-planning
```
Creates `sprint-status.yaml` to track progress.

#### Step 4: Build! (The Weekend)
For each story, repeat in fresh chats:
```
/bmad-bmm-create-story    # SM agent creates the story file
/bmad-bmm-dev-story        # DEV agent implements it
/bmad-bmm-code-review      # DEV agent reviews (recommended)
```

### Suggested Build Order

**Saturday Morning — Epic 1: Foundation**
- Story 1.1: Project scaffolding
- Story 1.2: Prospect spreadsheet parser
- Story 1.3: TGA API client (TEST THE API FIRST! `scripts/test_api.py`)
- Story 1.4: SQLite database
- Story 1.5: Baseline initialisation

**Saturday Afternoon — Epic 2: Change Detection**
- Stories 2.1-2.5: Diff engine and event generation

**Saturday Evening — Epic 3: AI Analysis**
- Stories 3.1-3.3: Claude integration and prompt engineering

**Sunday Morning — Epic 5: Delivery**
- Stories 5.1-5.5: Email digest, Make.com integration, Google Sheets

**Sunday Afternoon — Epic 4 & 6: Stretch Goals**
- Training package monitoring
- ASQA news monitoring
- End-to-end testing and polish

### Critical First Step on Saturday

Before building anything, validate that the REST API actually works:

```bash
curl -s "https://training.gov.au/api/organisation/52127" | python -m json.tool
```

If this returns JSON data for "Scope Training Australia", the REST API is open and you're good to go. If it returns a 401 or error, fall back to the SOAP API approach documented in the architecture.

## Pre-Requisites

- Node.js 20+ (for BMAD installer)
- Python 3.11+
- Claude Code CLI
- Anthropic API key
- Make.com account (free tier)
- Your prospect spreadsheet (CSV with RTO codes)
