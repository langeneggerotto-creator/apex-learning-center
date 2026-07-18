# v1.5 Static Check Plan

Status: DRAFT / REVIEW-GATED

## Purpose

Create a repeatable static verification plan before any merge or beta launch.

## Required Checks

- Required Dream OS files exist.
- STATUS contains NOT DEPLOYED.
- STATUS contains NOT VALIDATED.
- Prototype contains NO-SEND language.
- Prototype contains review gate language.
- Prototype does not include mailto sending automation.
- Prototype does not include fetch calls to production services.
- No API keys are committed.
- No private personal data is committed.
- No claims of guaranteed outcomes are present.

## Manual Verification Commands

These can be translated into GitHub Actions later:

```bash
test -f apex-dream-come-true-os/README.md
test -f apex-dream-come-true-os/STATUS.md
test -f apex-dream-come-true-os/prototype-index.html
grep -q "NOT DEPLOYED" apex-dream-come-true-os/STATUS.md
grep -q "NOT VALIDATED" apex-dream-come-true-os/STATUS.md
grep -q "NO-SEND" apex-dream-come-true-os/prototype-index.html
! grep -R "API_KEY" apex-dream-come-true-os
! grep -R "SECRET" apex-dream-come-true-os
```

## Boundary

Passing static checks does not prove legal compliance, privacy compliance, accessibility compliance, child safety, market validation, or viral adoption.
