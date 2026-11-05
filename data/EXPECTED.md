# Expected output for `data/board.csv` (today = 2026-11-06, threshold = 3 days)

"Movement" = the later of `stage_entered_date` and `last_contact_date`.

## Stalled (24)
C001, C002, C003, C005, C006, C007, C011, C014, C015, C019, C020, C021, C022, C023, C028,
C029, C032, C034, C035, C037, C040, C041, C042, C046

## Not stalled (16): moved within the last 3 days
C004, C010, C012, C013, C016, C017, C018, C024, C025, C030, C031, C033, C036, C038, C039, C043

## Ignored (4): closed
C008, C009, C026, C027 (Hired / Rejected)

## Data problems (2): reported, not ranked
- C044: missing `stage_entered_date`
- C045: unknown stage `Onsite`

## Edge cases and what should happen
| ID | Case | Expected |
|---|---|---|
| C001 | Offer, 6 days quiet, competing offer in notes | Top of rules ranking; AI should keep or raise it |
| C002 | Offer at exactly 3 days | Flagged (boundary is inclusive) |
| C003 | Final, candidate asked a question 4 days ago, we never replied | Top 2 (owe-reply bonus) |
| C004 | Old stage date but contacted yesterday | Not flagged (contact resets the clock) |
| C005 / C006 | Same stage, same days, same base score | Tie in rules; AI breaks it from notes |
| C007 | No contact logged | Uses stage date, flagged at 17 days |
| C012 | Candidate waiting on us, but only 2 days | Not flagged (under threshold) |
| C021 | Applied but CTO referral | Low base score; AI should nudge up |
| C028 | 22 days at Applied, over salary band | Capped day credit; AI may nudge down |
| C044 / C045 | Bad data | Listed under data problems, never silently dropped |
