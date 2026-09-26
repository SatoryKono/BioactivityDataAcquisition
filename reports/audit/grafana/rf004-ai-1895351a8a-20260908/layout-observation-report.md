# RF-004 observed layout and navigation

Candidate 1895351a8a95f2ca451115be6639b10afba16e03. All 21 tasks were completed at 1366x768, dark theme, DPR 1 and viewport scale 1. Task coverage 21/21; Q3 destination and return 7/7. These are observed AI task metrics; full layout/accessibility release acceptance remains with RF-005 and Stream A.

Measured friction: Run Explorer panel 3013 required nested table scrolling and row expansion to reach the artifact link. Q2 took 232.261 s; Q3 took 474.778 s including a capture harness repair. No product layout change is justified by these mixed tool/model execution times alone. A future human study can test whether an earlier exact-run artifact link reduces search effort. No human timing target or layout PASS is inferred. DQ Q2 took 190.730 s including a scroll-target repair; the range cards correctly remained UNKNOWN.

Tool handling: the corrected capture harness brings the page to the foreground and bounds animation-frame waiting; scrolling uses the visible dashboard surface. Repair pauses and unsuccessful preliminary attempts remain in the bundle. No failed product finding was silently waived.
