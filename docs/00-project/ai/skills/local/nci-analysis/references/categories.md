# NCI Categories

This is a working reference for the 20-category NCI analysis used by `nci-analysis`.
It is intentionally lightweight and derived from the skill workflow so the links remain valid and the scoring model is operational.

## Category Set

| #   | Category                    | Composite Factor       | What To Look For                                                      |
| --- | --------------------------- | ---------------------- | --------------------------------------------------------------------- |
| 1   | Emotional vocabulary        | Emotional Manipulation | fear, outrage, panic, danger, shock framing                           |
| 2   | Urgency and scarcity        | Emotional Manipulation | "act now", "before it is too late", countdown language                |
| 3   | Threat amplification        | Emotional Manipulation | disproportionate danger framing, existential stakes                   |
| 4   | Shock and outrage framing   | Emotional Manipulation | wording designed to maximize disgust or anger                         |
| 5   | Absolutist certainty        | Emotional Manipulation | no nuance, totalizing certainty, "everyone knows" patterns            |
| 6   | Event-driven opportunism    | Suspicious Timing      | a narrative tied to a breaking event for leverage                     |
| 7   | Timeline compression        | Suspicious Timing      | selective timing that hides prior context or sequence                 |
| 8   | Agenda alignment            | Suspicious Timing      | publication timing that strongly serves a concurrent campaign         |
| 9   | Message repetition          | Uniform Messaging      | repeated claims or slogans across the same artifact                   |
| 10  | Sloganized framing          | Uniform Messaging      | catchphrases that compress complex issues into a line                 |
| 11  | Attribution asymmetry       | Uniform Messaging      | one side is "confirmed", the other is "claimed" or "alleged"          |
| 12  | Us-vs-them framing          | Tribal Division        | strong in-group versus out-group construction                         |
| 13  | Loyalty pressure            | Tribal Division        | "real patriots", betrayal framing, belonging tests                    |
| 14  | Dehumanization and contempt | Tribal Division        | vermin, infestation, animalization, contempt labels                   |
| 15  | Missing context             | Missing Information    | omitted background necessary for fair interpretation                  |
| 16  | Authority issues            | Missing Information    | weak credentials, appeals to dubious expertise                        |
| 17  | Source opacity              | Missing Information    | anonymous sourcing without justification, missing dates or provenance |
| 18  | Cherry-picking              | Missing Information    | only favorable data shown while relevant counterevidence is omitted   |
| 19  | Unsupported inference       | Missing Information    | causal leaps, certainty without adequate support                      |
| 20  | Historical parallel misuse  | Missing Information    | loaded historical comparison used without careful fit                 |

## Generic 1-5 Scoring Rubric

- `1`: little to no evidence of the pattern.
- `2`: weak or isolated signals.
- `3`: clear presence, but mixed with legitimate framing.
- `4`: strong repeated use of the pattern.
- `5`: dominant pattern shaping the whole artifact.

## Notes

- Score patterns, not personal intent.
- A single severe category does not automatically determine the overall result.
- When categories are borderline, prefer explicit evidence quotes and lower confidence.
