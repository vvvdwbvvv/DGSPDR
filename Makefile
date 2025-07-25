.PHONY: checkstyle

checkstyle:
	python3 -m ruff check .; ruff_check_status=$$?; \
	python3 -m ruff format --check .; ruff_format_stastus=$$?; \
	python3 -m ruff check . --fix; \
	python3 -m ruff format .; \
	if [ $$ruff_check_status -ne 0 ] || [ $$ruff_format_status -ne 0 ]; then \
		exit 1; \
	fi
