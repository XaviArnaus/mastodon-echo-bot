PYTHON = python
PIP = pip

.PHONY: init
init:
	$(PIP) install -r requirements.txt

.PHONY: run
run:
	$(PYTHON) runner.py

.PHONY: create_app
create_app:
	$(PYTHON) create_app.py