PY ?= .venv/bin/python

.PHONY: all setup ingest build validate source test score app clean-processed

all:            ## download (cached) + build + validate
	$(PY) run_all.py

setup:          ## create the virtualenv and install dependencies
	python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

ingest:         ## run every ingest script only
	$(PY) run_all.py --skip-validate

build:          ## merge interim files -> data/processed
	$(PY) -m src.build.build_features

validate:       ## reports/validation_report.md + reports/maps/*.png
	$(PY) -m src.build.validate

source:         ## one source, e.g. make source S=peeringdb (then rebuild + validate)
	$(PY) run_all.py --only $(S)

test:
	$(PY) -m pytest -q tests

score:            ## exclusions + scores + robustness + sanity + trade-off
	$(PY) -m src.score.score

app:              ## streamlit demo (reads outputs/ only)
	.venv/bin/streamlit run app.py

clean-processed:  ## remove derived outputs (raw downloads are kept)
	rm -rf data/interim/*.parquet data/processed/* reports/maps/*.png reports/validation_report.md
