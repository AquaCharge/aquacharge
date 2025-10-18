# Cross-platform Makefile for Linux and Windows

# Detect operating system
ifeq ($(OS),Windows_NT)
    DETECTED_OS := Windows
    VENV_ACTIVATE := venv\Scripts\activate
    VENV_PYTHON := venv\Scripts\python
    VENV_PIP := venv\Scripts\pip
    PATH_SEP := \\
    MKDIR := mkdir
    RM := rmdir /s /q
else
    DETECTED_OS := $(shell uname -s)
    VENV_ACTIVATE := venv/bin/activate
    VENV_PYTHON := venv/bin/python
    VENV_PIP := venv/bin/pip
    PATH_SEP := /
    MKDIR := mkdir -p
    RM := rm -rf
endif

# Default directories (can be overridden)
FRONTEND_DIR ?= frontend
BACKEND_DIR ?= backend

.PHONY: test build lint install run docker ci


test:
	@echo "Running tests for frontend..."
	cd $(FRONTEND_DIR) && yarn test
	@echo "Running tests for backend..."
	cd $(BACKEND_DIR) && python -m unittest discover

build:
	@echo "Building frontend..."
	cd $(FRONTEND_DIR) && yarn build
	@echo "Building backend..."
	cd $(BACKEND_DIR) && python app.py build

lint:
	@echo "Linting frontend..."
	cd $(FRONTEND_DIR) && yarn lint
	@echo "Linting backend..."
	cd $(BACKEND_DIR) && flake8

install:
	@echo "Installing frontend dependencies..."
	cd $(FRONTEND_DIR) && yarn install
		@echo "Setting up Python virtual environment for backend..."
	cd $(BACKEND_DIR) && python3 -m venv venv || python -m venv venv
ifeq ($(OS),Windows_NT)
	@echo "Activating virtual environment and installing backend dependencies..."
	cd $(BACKEND_DIR) && $(VENV_ACTIVATE) && $(VENV_PIP) install -r requirements.txt
else
	@echo "Activating virtual environment and installing backend dependencies..."
	cd $(BACKEND_DIR) && . $(VENV_ACTIVATE) && $(VENV_PIP) install -r requirements.txt
endif

lint-format-backend:
ifeq ($(OS),Windows_NT)
	@echo "Activating virtual environment and installing backend dependencies..."
	cd $(BACKEND_DIR) && $(VENV_ACTIVATE) && $(VENV_PIP) install -r requirements.txt
else
	@echo "Activating virtual environment and installing backend dependencies..."
	cd $(BACKEND_DIR) && . $(VENV_ACTIVATE) && $(VENV_PIP) install -r requirements.txt
endif
	@echo "Linting backend..."
	cd $(BACKEND_DIR) && flake8

lint-fix-backend:
ifeq ($(OS),Windows_NT)
	@echo "Activating virtual environment and installing backend dependencies..."
	cd $(BACKEND_DIR) && $(VENV_ACTIVATE) && $(VENV_PIP) install -r requirements.txt
else
	@echo "Activating virtual environment and installing backend dependencies..."
	cd $(BACKEND_DIR) && . $(VENV_ACTIVATE) && $(VENV_PIP) install -r requirements.txt
endif
	@echo "Auto-formatting backend code with black..."
	cd $(BACKEND_DIR) && black .
	
lint-all-backend: lint-format-backend lint-fix-backend

ifeq ($(OS),Windows_NT)
run:
	@echo "Starting frontend and backend..."
	@echo "Frontend will run in background, backend in foreground"
	@echo "Press Ctrl+C to stop backend, then run 'taskkill /f /im node.exe' to stop frontend if needed"
	cd $(FRONTEND_DIR) && start /b yarn run dev
	cd $(BACKEND_DIR) && $(VENV_ACTIVATE) && $(VENV_PYTHON) app.py
else
run:
	@echo "Running frontend..."
	cd $(FRONTEND_DIR) && yarn run dev &
	@echo "Running backend..."
	cd $(BACKEND_DIR) && $(VENV_PYTHON) app.py
endif

docker:
	@echo "Building and starting Docker containers..."
	docker-compose up --build

docker-down:
	@echo "Stopping and removing Docker containers..."
	docker-compose down

ci:
	@echo "Running CI/CD pipeline locally with act..."
	act -W .github/workflows/branch.yml

test-backend:
	@echo "Running pytest for backend..."
ifeq ($(OS),Windows_NT)
	cd $(BACKEND_DIR) && $(VENV_ACTIVATE) && python -m pytest
else
	cd $(BACKEND_DIR) && . $(VENV_ACTIVATE) && python -m pytest
endif