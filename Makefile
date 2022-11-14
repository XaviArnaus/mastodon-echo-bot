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

.PHONY: validate_config
validate_config:
	@$(PYTHON) -c 'import yaml;yaml.safe_load(open("config.yaml"))' > /dev/null && echo "\033[0;32mThe Config is correct\033[0m" || echo "\033[0;31mThe Config has an error\033[0m"