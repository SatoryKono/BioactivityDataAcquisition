.PHONY: qa-arch-fast qa-debt quarantine-inspect quarantine-replay quarantine-purge release-lock

RUN ?= python3 -m
PIPELINE ?=
RUN_ID ?=

qa-arch-fast:
	$(RUN) pytest tests/architecture/ -m "not slow and not serial and not memory"

qa-debt:
	$(RUN) scripts.engineering.qa.check_quality_exemptions --trend-report on

quarantine-inspect:
	$(RUN) bioetl quarantine inspect --pipeline $(PIPELINE)

quarantine-replay:
	$(RUN) bioetl quarantine replay --pipeline $(PIPELINE)

quarantine-purge:
	$(RUN) bioetl quarantine purge --pipeline $(PIPELINE)

release-lock:
	$(RUN) bioetl lock release --pipeline $(PIPELINE) --run-id $(RUN_ID)
