COMPOSE_DEV = docker compose -f docker-compose.yml -f .devcontainer/docker-compose.yml
COMPOSE_LLAMA = docker compose -f servers/llama/docker-compose.yml
COMPOSE_VIRTUOSO = docker compose -f servers/virtuoso/docker-compose.yml

define app_run
	@if [ -f /.dockerenv ]; then \
		$(1); \
	else \
		docker cp .env "$$(docker compose ps -q app)":/app/.env && \
		docker compose exec app $(1); \
	fi
endef


# URLs
VIRTUOSO_ENDPOINT = http://virtuoso:8890/sparql


# Init
.PHONY: init-data
init-data: ## Download DBLP-QuAD dataset and schema
	$(call app_run, uv run scripts/init_data.py)

.PHONY: init-config
init-config: ## Generate default config files and schemas in config/
	$(call app_run, uv run scripts/init_config.py)

# Demo
.PHONY: demo
demo: ## Run the Streamlit demo
	$(call app_run, dblp-kgqa)

# LLM (local)

.PHONY: llm-cpu
llm-cpu: ## Start local llama-server on CPU (reads model/ctx from services.yml)
	uv run servers/llama/start.py cpu

.PHONY: llm-gpu
llm-gpu: ## Start local llama-server on GPU (reads model/ctx from services.yml)
	uv run servers/llama/start.py gpu

.PHONY: llm-down
llm-down: ## Stop local llama-server (cpu + gpu profiles)
	$(COMPOSE_LLAMA) --profile cpu --profile gpu down

# LLM (RunPod)

.PHONY: runpod-start
runpod-start: ## Start RunPod llama-server (reads model/ctx from services.yml)
	$(call app_run, python servers/runpod/runpod_llm.py start)

.PHONY: runpod-stop
runpod-stop: ## Stop RunPod pod
	$(call app_run, python servers/runpod/runpod_llm.py stop)

.PHONY: runpod-status
runpod-status: ## Check RunPod pod status and health
	$(call app_run, python servers/runpod/runpod_llm.py status)

.PHONY: runpod-url
runpod-url: ## Print RunPod base_url for services.yml
	$(call app_run, python servers/runpod/runpod_llm.py url)

.PHONY: gcloud-auth
gcloud-auth: ## Run ADC login + set quota project from .env (gcloud is baked into the image)
	$(call app_run, sh -c 'set -a && . /app/.env && set +a && gcloud auth application-default login && gcloud auth application-default set-quota-project $$GOOGLE_CLOUD_PROJECT')

# Experiment

.PHONY: dev-up
dev-up: ## Start dev containers standalone (CLI workflow, no VS Code devcontainer)
	$(COMPOSE_DEV) up -d

.PHONY: dev-down
dev-down: virtuoso-down ## Stop dev containers (removes dev volumes, keeps virtuoso volume)
	$(COMPOSE_DEV) down -v

.PHONY: virtuoso-init
virtuoso-init: ## Load DBLP dump into Virtuoso
	uv run servers/virtuoso/init.py

.PHONY: virtuoso-up
virtuoso-up: ## Start Virtuoso SPARQL endpoint
	$(COMPOSE_VIRTUOSO) up -d
	@echo ""
	@echo ">> Virtuoso is up. Set the following endpoint in config/experiment.yml:"
	@echo ">> $(VIRTUOSO_ENDPOINT)"
	@echo ""

.PHONY: virtuoso-down
virtuoso-down: ## Stop Virtuoso (keeps volume)
	$(COMPOSE_VIRTUOSO) down

# Data
.PHONY: experiment
experiment: ## Run main experiment pipeline
	$(call app_run, uv run src/dblp_kgqa/experiment/main.py)

# Help
.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
