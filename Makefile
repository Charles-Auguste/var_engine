clean:
	@bash -c 'delete_pycache() { \
	    for dir in "$$1"/*; do \
	        if [ -d "$$dir" ]; then \
	            if [ "$$(basename "$$dir")" = "__pycache__" ]; then \
	                rm -rf "$$dir"; \
	                echo "Deleted: $$dir"; \
	            else \
	                delete_pycache "$$dir"; \
	            fi; \
	        fi; \
	    done; \
	}; \
	delete_pycache .'

# Development workflow
#
dev_install:
	@poetry lock
	@poetry install
	@git config --local --unset core.hooksPath | true
	@git config --global --unset core.hooksPath | true
	@pre-commit install
	@.git/hooks/pre-commit

test:
	@coverage run --source=var_engine -m pytest -v tests && coverage report -m

# QA
qa_lines_count:
	@find ./ -name '*.py' -exec  wc -l {} \; | sort -n| awk \
        '{printf "%4s %s\n", $$1, $$2}{s+=$$0}END{print s}'
	@echo ''

qa_check_code:
	@python -m ruff check .

format_code:
	@isort .
	@black .

# Production deploy tools ( Used by CI )
#
install: clean wheel
	@pip3 install -U dist/*.whl --cache-dir /pip_cache

wheel: clean
	@poetry build

# Test run
compute_var:
	@var_engine var_study var_engine/data/template/example.xlsx -ed 2025-02-10 -sd 2022-12-31