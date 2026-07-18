# v1.6 Review Matrix

Status: DRAFT / REVIEW-GATED
Truth status: NOT DEPLOYED / NOT VALIDATED

## Purpose

Convert the review gates into an explicit review matrix before any merge, private beta, public waitlist, outreach, or launch.

| Gate | Owner Needed | Evidence Required | Merge Blocker | Launch Blocker |
|---|---|---|---|---|
| Repo-home decision | Founder / maintainer | Issue decision recorded | Yes | Yes |
| Static verification | Technical reviewer | Script or CI pass log | Yes | Yes |
| Secrets/private-data review | Technical reviewer | Scan result and manual review | Yes | Yes |
| Privacy review | Privacy/legal reviewer | Review notes and risk disposition | Yes | Yes |
| Child-safety review | Safety reviewer | Minor-flow checklist complete | Yes | Yes |
| Accessibility review | Accessibility reviewer | Keyboard, contrast, screen-reader pass notes | No | Yes |
| Security review | Security reviewer | No live secrets, no production endpoint exposure | Yes | Yes |
| No-send boundary | Product/security reviewer | Prototype and workflow review | Yes | Yes |
| False-hope risk review | Product/safety reviewer | Language review and mitigation notes | No | Yes |
| Launch experiment review | Founder / reviewer | Safety-braked experiment ledger | No | Yes |

## Required Before Merge

- Repo-home decision
- Static verification pass
- Secrets/private-data review
- Privacy review
- Child-safety review
- Security review
- No-send boundary review

## Required Before Private Beta

- All merge blockers
- Accessibility review
- False-hope risk review
- Private beta checklist approved

## Required Before Public Launch

- All private beta gates
- Incident response plan
- Data retention plan
- Real backend review
- Evidence ledger process
- Launch experiment safety brakes

## Boundary

A completed review matrix is governance evidence only. It is not proof of legal compliance, real-world safety, product-market fit, or viral growth.
