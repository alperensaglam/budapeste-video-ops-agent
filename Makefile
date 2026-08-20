# GÖZCÜ — Makefile
#
# Kanonik görev koşucusu tasks.py'dir (saf Python, platformdan bağımsız).
# Bu Makefile sadece Linux/macOS/Colab/Kaggle kolaylığı için ona delege eder.
# Windows'ta make yoktur; oradaki komut:  python tasks.py <hedef>

PYTHON ?= python
TASKS  := $(PYTHON) tasks.py

.PHONY: help setup lint fmt test cov check schema-check license-check \
        demo record-cassettes profiles clean

help:            ## Görev listesi
	@$(TASKS) --list

setup:           ## Sanal ortam + bağımlılıklar
	@$(TASKS) setup $(EXTRAS)

lint:            ## ruff + mypy
	@$(TASKS) lint

fmt:             ## Otomatik biçimlendirme
	@$(TASKS) fmt

test:            ## Testler (cpu-dev, GPU gerekmez)
	@$(TASKS) test

cov:             ## Kapsam raporu (hedef %70)
	@$(TASKS) cov

schema-check:    ## Sözleşme kararlılığı
	@$(TASKS) schema-check

license-check:   ## AGPL / non-commercial avı
	@$(TASKS) license-check

check:           ## PR öncesi tek komut: lint + test + schema + license
	@$(TASKS) check

demo:            ## Uçtan uca demo (SCENARIO=empty_video|context_switch|tool_failure)
	@$(TASKS) demo $(SCENARIO)

record-cassettes: ## GPU'da kaset üret (GOZCU_PROFILE=colab-t4)
	@$(TASKS) record-cassettes

profiles:        ## Donanım profillerini listele
	@$(TASKS) profiles

clean:           ## Üretilmiş dosyaları sil
	@$(TASKS) clean
