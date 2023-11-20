PYTHON = python3
POETRY ?= poetry

ifeq ($(OS), Darwin)
	OPEN := open
else
	OPEN := xdg-open
endif

.PHONY: init
init:
	$(POETRY) install

.PHONY: update
update:
	$(POETRY) lock
	$(POETRY) install

.PHONY: yapf
yapf:
	$(POETRY) run yapf -r --diff .

.PHONY: flake8
flake8:
	$(POETRY) run flake8 . \
		--select=E9,F63,F7,F82 \
		--show-source \
		--statistics
	# Full linter run.
	$(POETRY) run flake8 --max-line-length=96 --exclude storage .

.PHONY: format
format:
	make flake8; make yapf

.PHONY: do-yapf
do-yapf:
	$(POETRY) run yapf -i -r .

# .PHONY: test
# test:
# 	$(POETRY) run pytest

.PHONY: coverage
coverage:
	$(POETRY) run pytest --cov-report html:coverage \
		--cov=src \
		tests/
	$(OPEN) coverage/index.html

# From this line, all targets are deprecated and will be removed in the next version
# Use instead:
#
# bin/jan [command]
#
# ...where [command] equals to the following targets:
#
#	Command (and subcommand)	Makefile target
#	-------------------------------------------
#	echo run					run
#	mastodon create_app			create_app
#	mastodon publish_queue		publish_queue
#	mastodon test				publish_test
#	janitor test				janitor_test
#	telegram_login				telegram_login
#	validate_config				validate_config
#

.PHONY: run
run:
	@echo "\033[1;33mDEPRECATED target: Use bin/jan shell script instead\033[0m"
	$(POETRY) run python runner.py

.PHONY: create_app
create_app:
	@echo "\033[1;33mDEPRECATED target: Use bin/jan shell script instead\033[0m"
	$(POETRY) run python create_app.py

.PHONY: telegram_login
telegram_login:
	@echo "\033[1;33mDEPRECATED target: Use bin/jan shell script instead\033[0m"
	$(POETRY) run python telegram_login.py

.PHONY: publish_queue
publish_queue:
	@echo "\033[1;33mDEPRECATED target: Use bin/jan shell script instead\033[0m"
	$(POETRY) run python publish_queue.py

.PHONY: publish_test
publish_test:
	@echo "\033[1;33mDEPRECATED target: Use bin/jan shell script instead\033[0m"
	$(POETRY) run python publish_test.py

.PHONY: validate_config
validate_config:
	@echo "\033[1;33mDEPRECATED target: Use bin/jan shell script instead\033[0m"
	@$(PYTHON) -c 'import yaml;yaml.safe_load(open("config.yaml"))' > /dev/null && echo "\033[0;32mThe Config is correct\033[0m" || echo "\033[0;31mThe Config has an error\033[0m"

.PHONY: migrate_feed_queue
migrate_feed_queue:
	@echo "\033[1;33mDEPRECATED target: Use bin/jan shell script instead\033[0m"
	$(POETRY) run python scripts/remove_scheme_from_urls_seen.py

.PHONY: test_janitor
test_janitor:
	@echo "\033[1;33mDEPRECATED target: Use bin/jan shell script instead\033[0m"
	$(POETRY) run python test_janitor.py