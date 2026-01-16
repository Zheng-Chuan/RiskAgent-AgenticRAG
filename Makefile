.PHONY: install test lint check clean

install:
	pip install -e .

test:
	python -m unittest discover tests

lint:
	# 由于已移除 pylint，这里暂时为空，或可加入 pyright/mypy
	echo "No linter configured."

check: test

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -name '__pycache__' -exec rm -rf {} +
	find . -name '*.pyc' -exec rm -f {} +
