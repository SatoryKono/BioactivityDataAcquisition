______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-09-08'

______________________________________________________________________

# Usability baseline protocol (operator dashboards)

Maps to scenarios in [operator-scenarios-s1-s6.md](operator-scenarios-s1-s6.md).

## Stopwatch protocol

1. Freeze the candidate SHA, runtime JSON hashes, full profile, UTC from/to,
   variables, 1366×768 viewport, theme and zoom. Owner approves the page goals,
   primary role, scenario fixtures and independent answer keys before measurement.
2. Record navigation start, first paint, stable data readiness and question shown
   timestamps separately. Start the understanding timer only when both the question
   and stable evidence are available. Also retain paint-to-first-answer time for
   historical comparisons; do not mix the two metrics.
3. Give only the question to the participant. Record prior exposure and assistance.
   Stop on the first independently scored correct answer. For Q3, require a safe
   explanation and arrival at the correct destination; record return separately.
   A wrong first click does not stop the timer. A timeout is a failed attempt with
   elapsed duration and null first-correct time, never an omitted observation.
4. Count mouse/keyboard activations as clicks; count variable changes, row expansion,
   search, hover and scroll as separate interactions. Record diagnostic edges,
   complete path, back-navigation, wrong first target and context loss on return.
5. Record participant type `HUMAN` or `AI_AGENT`, pseudonymous ID, experience,
   first/repeat attempt and reviewer. Browser/tool/model latency is not human
   time-to-first-insight. Astra sessions are reported separately and cannot silently
   replace the required human measurement.

## Required scenarios (21)

### Approved AI-only scope for RF-004

On 2026-09-08 the task owner chose “Принять только AI-проверку сценариев” for
#10167 and the operator component of #10185/#10171. Astra is `AI_AGENT`.
For this acceptance use `AI_SCENARIOS` with a candidate-bound, hashed owner-decision
receipt as specified in [regression acceptance](regression-acceptance.md).
Record `human_usability_status=NOT_MEASURED`, human sample size zero and null human
timing/success aggregates. The stopwatch procedure and 5–10 second target above
remain the human protocol; they are not applied to AI elapsed time.

For each AI task record the start/end timestamps and elapsed wall-clock seconds,
including tool/model latency, prior exposure, answer, observed evidence and reviewer
score against the answer key. Keep first and repeat attempts separate. Q3 passes
only after observing the destination and return context; an unobserved popup or a
link inferred from JSON is not a completed navigation. Record clicks/interactions,
diagnostic depth, back-navigation, context loss and dispositions as above.
AI success and elapsed median/max use their own sample sizes. No AI result is a
human comprehension measurement. The remaining regression gates are unchanged.

### Scenario inventory

Execute Q1–Q3 for each of the seven current dashboards in the linked scenario
guide. Use at least one first attempt per task, with first/repeat statistics kept
separate. One participant is a descriptive pilot, not population-level evidence.
All/single/multi variables, selected run inside/outside range, 900×768 and expanded
lower rows belong to the additional regression matrix; 21 tasks do not cover it.

The following old S1–S6 mapping is retained only for historical comparisons:

| ID | Goal | Entry board | Stop condition |
| --- | --- | --- | --- |
| S1 | What is broken now? | Overview/Fleet | Names degraded subsystem from Inputs/Status |
| S2 | Safe to resume/replay? | Trust | States resume safe/unsafe with basis |
| S3 | Which provider is failing? | Provider | Names provider from GLOBAL matrix/causes |
| S4 | DQ hard fail path | DQ | Separates Now vs Range evidence |
| S5 | Runtime blockers | Pipeline | Names blocker reason or VALID EMPTY+OK |
| S6 | Single-run identity | Run Explorer | Reads run_id identity without Prom labels |

## Score sheet fields

Store `operator-task-protocol.json`, `operator-observations.csv`,
`operator-metrics.json` and a layout report in a new immutable capture directory.
Each observation includes task/fixture/candidate/occurrence IDs, participant type,
attempt kind, timestamps, success, answer and answer-key evidence, reviewer,
first-correct seconds, clicks, interactions, diagnostic depth, path, row expansions,
variable changes, back-navigation, context loss, assistance and deviation disposition.

Report participant count, first/repeat sample sizes, success numerator/denominator,
median/max time and clicks/interactions/depth per task and overall. Null means
unmeasured; n=0 produces null aggregates, not 0% or 100%. Task Coverage is tasks
with a verified successful attempt / 21; success rate is successful / executed
attempts. Drill-down Coverage is reached context-preserving mandatory Q3 targets /
approved mandatory Q3 targets. Report failed and timed-out attempts too.

## Targets (not claims)

Task first insight target is 5–10 seconds; faster than 5 seconds is acceptable.
Explain every result over 10 seconds or failed/context-losing task with panel ID,
question, cause, proposed move/link and retest evidence. An owner-reviewed
disposition explains a miss but does not turn it into a measured target pass.
Re-measure after the relevant change and use the final candidate in #10185.
