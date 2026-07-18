# v1.5 Full Artifact Import Strategy

Status: DRAFT / REVIEW-GATED
Truth status: NOT DEPLOYED / NOT VALIDATED

## Goal

Define the safe route for importing the full APEX Dream Come True OS artifact set into GitHub without exposing private data, making launch claims, or enabling external outreach.

## Import Order

1. Keep PR #1 as draft.
2. Confirm repository home decision.
3. Review artifact package locally for secrets and private data.
4. Import documentation first.
5. Import prototype files second.
6. Import tests and ledgers third.
7. Import workflow last.
8. Run static checks.
9. Keep merge blocked until review gates pass.

## Artifact Classes

- Specifications
- Prototype HTML
- Static verification notes
- Evidence ledgers
- Review checklists
- Launch experiment ledgers
- Private beta planning documents

## Excluded Until Review

- Real user data
- Private child or family information
- Live email credentials
- Live API keys
- Live waitlist backend secrets
- External outreach automation
- Public launch materials that imply validation

## Merge Gates

- Repository home decision recorded
- Static verification complete
- Privacy review complete
- Safety review complete
- Accessibility review complete
- Security review complete
- No-send boundary confirmed

## Recommendation

Keep the current PR as the review anchor. Use v1.6 for implementation only after the repo-home and review-gate decisions are complete.
