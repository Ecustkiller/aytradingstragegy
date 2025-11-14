# Makefile - 常用命令快捷方式

.PHONY: help test lint format install clean

help:
	@echo "可用命令:"
	@echo "  make install     - 安装依赖"
	@echo "  make test        - 运行测试"
	@echo "  make test-cov    - 运行测试并生成覆盖率报告"
	@echo "  make lint        - 代码检查"
	@echo "  make format      - 代码格式化"
	@echo "  make clean       - 清理缓存文件"

install:
	pip install -r requirements.txt

test:
	pytest tests/unit/ -v

test-cov:
	pytest tests/unit/ --cov=modules --cov=aitrader_core --cov-report=html --cov-report=term

lint:
	flake8 modules/ aitrader_core/ --max-line-length=100 --extend-ignore=E203,W503

format:
	black modules/ aitrader_core/ --line-length=100
	isort modules/ aitrader_core/ --profile=black --line-length=100

clean:
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -r {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/ dist/ build/ *.egg-info

