# Makefile for AquaCharge

# Variables
FRONTEND_DIR=frontend
BACKEND_DIR=backend

# Targets
.PHONY: test build lint install run

test:
	@echo "Running tests for frontend..."
	cd $(FRONTEND_DIR) && yarn test
	@echo "Running tests for backend..."
	cd $(BACKEND_DIR) && python -m unittest discover

build:
	@echo "Building frontend..."
	cd $(FRONTEND_DIR) && yarn build
	@echo "Building backend..."
	cd $(BACKEND_DIR) && python setup.py build

lint:
	@echo "Linting frontend..."
	cd $(FRONTEND_DIR) && yarn lint
	@echo "Linting backend..."
	cd $(BACKEND_DIR) && flake8

install:
	@echo "Installing frontend dependencies..."
	cd $(FRONTEND_DIR) && yarn install
	@echo "Setting up Python virtual environment for backend..."
	cd $(BACKEND_DIR) && python3 -m venv venv
	@echo "Activating virtual environment and installing backend dependencies..."
	cd $(BACKEND_DIR) && ./venv/bin/pip install -r requirements.txt

run:
	@echo "Running frontend..."
	cd $(FRONTEND_DIR) && yarn run dev &
	@echo "Running backend..."
	cd $(BACKEND_DIR) && ./venv/bin/python app.py