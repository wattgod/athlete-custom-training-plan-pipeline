# Gravel God training-plan pipeline — developer commands.
# Run from the repo root.

SCRIPTS := athletes/scripts
PY := python3

.PHONY: help test acceptance preflight clean-acctest

help:
	@echo "make test        — full unit + guard suite (fast; acceptance auto-skips)"
	@echo "make acceptance  — end-to-end ORDER ACCEPTANCE: real pipeline + PDF per golden order"
	@echo "make preflight   — everything (test + acceptance). Run before trusting a batch of orders."
	@echo "make clean-acctest — remove acceptance scratch athletes + deliveries"

# Fast layer: unit tests + every content/PDF/compliance guard.
test:
	cd $(SCRIPTS) && PYTHONPATH=$(CURDIR) $(PY) -m pytest . -q --ignore=test_order_acceptance.py

# The send-worthy contract: each golden order runs the REAL pipeline and the
# deliverable must pass every coherence check (volume, facts, PDF, fueling...).
acceptance:
	cd $(SCRIPTS) && PYTHONPATH=$(CURDIR) GG_RUN_ACCEPTANCE=1 $(PY) -m pytest test_order_acceptance.py -q

# One command to trust the pipeline. This is the gate to run before sending
# a batch of plans.
preflight: test acceptance
	@echo ""
	@echo "✓ PREFLIGHT PASSED — the pipeline produces send-worthy plans."

clean-acctest:
	rm -rf athletes/acc-* athletes/acctest-* "$$HOME/.gg-acctest-delivery"
