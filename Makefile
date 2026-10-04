# urduofdani :: convenience targets (stdlib only, works with GNU make)
PY ?= python3

.PHONY: help test verify bench build full audit tiers docs check clean all

help:            ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

test:            ## run the test suite
	$(PY) run_tests.py

verify:          ## verify both shipped artifacts (8 checks each)
	$(PY) urduofdani.py verify
	$(PY) urduofdani.py verify -F

bench:           ## benchmark the shipped artifact
	$(PY) urduofdani.py bench -r 10

build:           ## rebuild the default database
	$(PY) urduofdani.py build --mode default -o urdu_database.txt.gz

full:            ## rebuild the unlimited database
	$(PY) urduofdani.py build --mode full -o urdu_database.full.txt.gz

tiers:           ## build + measure every tier
	$(PY) tools/measure_tiers.py

docs:            ## audit README/CONTRIBUTING (anchors, links, numbers, CLI)
	$(PY) tools/audit_docs.py

check:           ## prove the README table is not stale
	$(PY) tools/measure_tiers.py --check README.md

all: test verify docs check   ## everything CI runs

clean:           ## remove caches and stray exports
	rm -rf __pycache__ tests/__pycache__ tools/__pycache__ examples/__pycache__
	rm -f urdu_database.txt
