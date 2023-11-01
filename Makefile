PYTHON = python3
PIP = pip3

.PHONY: init
init:
	$(PIP) install -r requirements.txt

.PHONY: run
run:
	$(PYTHON) runner.py

.PHONY: create_app
create_app:
	$(PYTHON) create_app.py

.PHONY: telegram_login
telegram_login:
	$(PYTHON) telegram_login.py

.PHONY: publish_queue
publish_queue:
	$(PYTHON) publish_queue.py

.PHONY: validate_config
validate_config:
	@$(PYTHON) -c 'import yaml;yaml.safe_load(open("config.yaml"))' > /dev/null && echo "\033[0;32mThe Config is correct\033[0m" || echo "\033[0;31mThe Config has an error\033[0m"

.PHONY: migrate_feed_queue
migrate_feed_queue:
	$(PYTHON) scripts/remove_scheme_from_urls_seen.py

.PHONY: test_janitor
test_janitor:
	$(PYTHON) test_janitor.py