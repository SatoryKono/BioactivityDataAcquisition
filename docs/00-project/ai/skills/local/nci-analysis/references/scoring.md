# NCI Scoring

## Category Scale

Each category is scored on a `1-5` scale:

- `1`: absent or negligible
- `2`: low presence
- `3`: moderate and notable
- `4`: strong
- `5`: pervasive or dominant

## Composite Factors

Use the category groups defined by the skill:

- Emotional Manipulation: categories `1-5`
- Suspicious Timing: categories `6-8`
- Uniform Messaging: categories `9-11`
- Tribal Division: categories `12-14`
- Missing Information: categories `15-20`

Unless a stricter calibration is introduced later, use an equal-weight average inside each factor.

## Factor Weights

- Emotional Manipulation: `25%`
- Suspicious Timing: `20%`
- Uniform Messaging: `20%`
- Tribal Division: `15%`
- Missing Information: `20%`

## Overall Score

1. Compute each composite factor on the `1-5` scale.
1. Compute the weighted average of the five factors.
1. Convert to `0-100`:

```text
overall_score = (weighted_avg - 1) * 25
```

## Severity Bands

- `0-25`: low manipulation risk
- `26-50`: moderate concern
- `51-75`: high manipulation patterns
- `76-100`: severe manipulation profile

## Deep Research Triggers

Trigger verification when any of the following is true:

- Overall score `> 40`
- Suspicious Timing `> 3`
- Authority Issues `> 3`
- Cherry-Picking `> 3`
- Historical Parallels `> 2`
