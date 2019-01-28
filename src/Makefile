#!/usr/bin/make

all: lint unit_test


.PHONY: clean
clean:
	@echo "Cleaning files"
	@if [ -d ./.tox ] ; then rm -r ./.tox ; fi
	@if [ -d ./.pytest_cache ] ; then rm -r ./.pytest_cache ; fi

.PHONY: apt_prereqs
apt_prereqs:
	@# Need tox, but don't install the apt version unless we have to (don't want to conflict with pip)
	@which tox >/dev/null || (sudo apt-get install -y python-pip && sudo pip install tox)

.PHONY: lint
lint: apt_prereqs
	@tox --notest
	@PATH=.tox/amulet/bin flake8 $(wildcard hooks reactive lib unit_tests tests)

.PHONY: unit_test
unittest: apt_prereqs
	@echo Starting unit tests
	@tox -e unit

functionaltest:
	@tox -e functional

