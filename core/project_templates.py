"""Built-in project skeletons.

Creating a template makes a new project directory. It does not copy an
existing project or its data.
"""

from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path
from typing import Any

TEMPLATES: dict[str, dict[str, str]] = {
    "book": {
        "README.md": """# {{name}}

> {{description}}

- Type: book / monograph / popular science
- Owner: {{owner}}
- Status: planning

## Goal

## Audience

## Success criteria

## Milestones

- [ ] Theme and audience
- [ ] Outline
- [ ] Source collection
- [ ] Draft chapters
- [ ] Review and revision
- [ ] Publication
""",
        "OUTLINE.md": """# Outline · {{name}}

## Part I

### Chapter 1

## Part II

### Chapter 2
""",
        "SOURCES.md": """# Sources · {{name}}

| ID | Source | Type | Notes |
|---|---|---|---|
| S1 | | paper / book / interview | |
""",
        "TASKS.md": """# Tasks · {{name}}

- [ ] Define thesis
- [ ] Build chapter outline
- [ ] Collect primary sources
- [ ] Draft chapter 1
- [ ] Review and revise
""",
        "project.yaml": """code: {{code}}
name: {{name}}
type: book
status: planning
description: {{description}}
template: book
created: {{date}}
""",
    },
    "research": {
        "README.md": """# {{name}}

> {{description}}

- Type: research
- Owner: {{owner}}
- Status: planning

## Question

## Why it matters

## Evidence standard

## Milestones

- [ ] Literature / background
- [ ] Methods and samples
- [ ] Pilot experiment
- [ ] Stage result
- [ ] Weekly review
- [ ] Output: paper / patent / product
""",
        "QUESTIONS.md": """# Research questions · {{name}}

## Primary question

## Secondary questions

## Hypotheses

## Falsification criteria
""",
        "METHODS.md": """# Methods · {{name}}

## Instruments / samples

## Procedure

## Controls

## Measurement and uncertainty
""",
        "WEEKLY.md": """# Weekly review · {{name}}

## Week of {{date}}

### Progress

### Evidence

### Problems

### Next actions
""",
        "EVIDENCE.md": """# Evidence log · {{name}}

| Claim | Evidence | Source | Status |
|---|---|---|---|
| | | | candidate |
""",
        "OUTPUTS.md": """# Outputs · {{name}}

- [ ] Paper
- [ ] Patent
- [ ] Product / prototype
- [ ] Dataset
""",
        "project.yaml": """code: {{code}}
name: {{name}}
type: research
status: planning
description: {{description}}
template: research
created: {{date}}
""",
    },
    "opc": {
        "README.md": """# {{name}}

> {{description}}

- Type: OPC 180-day project
- Owner: {{owner}}
- Status: active

## 180-day goal

## Weekly operating rhythm

- Monday: set goal
- Friday: review evidence, risks, next action

## Milestones

- [ ] Day 30 checkpoint
- [ ] Day 60 checkpoint
- [ ] Day 90 checkpoint
- [ ] Day 120 checkpoint
- [ ] Day 180 final delivery
""",
        "GOALS.md": """# Goals · {{name}}

## North-star outcome

## Stage goals

| Stage | Goal | Evidence |
|---|---|---|
| 0-30 | | |
| 31-60 | | |
| 61-90 | | |
| 91-120 | | |
| 121-180 | | |
""",
        "WEEKLY.md": """# Weekly review · {{name}}

## Week of {{date}}

### Delivered

### Evidence

### Risks

### Decision / next action
""",
        "RISKS.md": """# Risks · {{name}}

| Risk | Impact | Mitigation | Owner |
|---|---|---|---|
| | | | |
""",
        "FINAL.md": """# Final delivery · {{name}}

## Outcome

## Evidence

## What changed

## Next
""",
        "project.yaml": """code: {{code}}
name: {{name}}
type: opc
status: active
description: {{description}}
template: opc
created: {{date}}
""",
    },
}


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:60] or "project"


def list_templates() -> list[dict[str, Any]]:
    return [
        {"name": name, "files": sorted(files), "description": {
            "book": "book / monograph workflow",
            "research": "research project lifecycle",
            "opc": "180-day OPC operating cadence",
        }[name]}
        for name, files in TEMPLATES.items()
    ]


def create(
    template: str,
    target: str | Path,
    *,
    code: str = "",
    name: str = "",
    owner: str = "owner",
    description: str = "",
) -> dict[str, Any]:
    if template not in TEMPLATES:
        raise ValueError(f"unknown template: {template}")
    destination = Path(target).expanduser()
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("target directory must be empty or missing")
    destination.mkdir(parents=True, exist_ok=True)
    project_name = name.strip() or destination.name
    project_code = code.strip() or _slug(project_name)
    values = {
        "name": project_name,
        "code": project_code,
        "owner": owner,
        "description": description.strip(),
        "date": _dt.date.today().isoformat(),
    }
    for relative, body in TEMPLATES[template].items():
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            body.replace("{{name}}", values["name"])
            .replace("{{code}}", values["code"])
            .replace("{{owner}}", values["owner"])
            .replace("{{description}}", values["description"])
            .replace("{{date}}", values["date"]),
            encoding="utf-8",
        )
    return {"ok": True, "template": template, "code": project_code, "path": str(destination), "files": sorted(TEMPLATES[template])}
