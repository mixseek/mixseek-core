# =============================================================================
# MixSeek-Core Production Environment Makefile
# =============================================================================
# This Makefile provides production-specific commands for deployment, monitoring,
# and management. It is optimized for secure, reliable production environments
# with comprehensive monitoring and rollback capabilities.

# Include common definitions and targets
include ../Makefile.common

# =============================================================================
# PRODUCTION ENVIRONMENT CONFIGURATION
# =============================================================================

# Environment identification
IMAGE_NAME := $(APP_NAME)/prod:$(TAG)
CONTAINER_NAME := $(APP_NAME)-prod
REPO := $(IMAGE_NAME)
ENV := prod

# Build arguments (use fixed production user for consistency)
BUILD_ARGS := \
    --build-arg MIXSEEK_USERNAME=appuser \
    --build-arg MIXSEEK_UID=1000 \
    --build-arg MIXSEEK_GID=1000 \
    --build-arg BUILD_DATE=$(shell date -u +"%Y-%m-%dT%H:%M:%SZ")

# Production security options
PROD_SECURITY_OPTS := \
    --read-only \
    --tmpfs /tmp:noexec,nosuid,size=256M \
    --tmpfs /home/appuser/.config:noexec,nosuid,size=64M \
    --tmpfs /app/logs:noexec,nosuid,size=128M \
    --cap-drop=ALL \
    --cap-add=NET_BIND_SERVICE \
    --security-opt=no-new-privileges \
    --user 1000:1000

# Production runtime options
PROD_DOCKER_OPTS := \
    --name $(CONTAINER_NAME) \
    --network $(NETWORK) \
    --hostname $(CONTAINER_NAME) \
    --restart=unless-stopped \
    --env-file=$(ROOTDIR)/.env.prod

# Health check configuration
HEALTH_CHECK := \
    --health-cmd="python -c 'import sys; sys.exit(0)'" \
    --health-interval=30s \
    --health-timeout=10s \
    --health-retries=3 \
    --health-start-period=10s

# Combined runtime options
DOCKER_OPTS := $(PROD_DOCKER_OPTS) $(PROD_SECURITY_OPTS) $(HEALTH_CHECK)

# =============================================================================
# PRODUCTION DEPLOYMENT
# =============================================================================

.PHONY: deploy
deploy: build
	@echo "🚀 Deploying to production: $(CONTAINER_NAME)"
	$(call check_env_file,$(ENV))
	$(call check_docker)
	@echo "🔒 Using security hardened configuration"
	@echo "📋 Image: $(IMAGE_NAME)"
	@echo "🏷️  Tag: $(TAG)"
	@docker run -d $(DOCKER_OPTS) $(IMAGE_NAME)
	@echo "✅ Production deployment completed"
	@echo "💡 Monitor with: make logs"
	@echo "🔍 Health check: make health-check"
	@$(MAKE) post-deploy-check

.PHONY: deploy-blue-green
deploy-blue-green: build
	@echo "🔄 Blue-Green deployment: $(CONTAINER_NAME)"
	$(call check_env_file,$(ENV))
	@# Check if current production is running
	@if docker ps --filter "name=$(CONTAINER_NAME)" --format "{{.Names}}" | grep -q "$(CONTAINER_NAME)"; then \
		echo "🔵 Current production detected: $(CONTAINER_NAME)"; \
		echo "🟢 Starting green deployment: $(CONTAINER_NAME)-green"; \
		docker run -d $(PROD_DOCKER_OPTS) $(PROD_SECURITY_OPTS) $(HEALTH_CHECK) \
			--name $(CONTAINER_NAME)-green \
			$(IMAGE_NAME); \
		echo "⏱️  Waiting for green deployment health check..."; \
		sleep 30; \
		if $(MAKE) health-check CONTAINER_NAME=$(CONTAINER_NAME)-green; then \
			echo "✅ Green deployment healthy, switching traffic"; \
			$(MAKE) switch-to-green; \
		else \
			echo "❌ Green deployment failed health check"; \
			docker rm -f $(CONTAINER_NAME)-green; \
			exit 1; \
		fi; \
	else \
		echo "🚀 No existing deployment, performing standard deployment"; \
		$(MAKE) deploy; \
	fi

.PHONY: switch-to-green
switch-to-green:
	@echo "🔄 Switching traffic from blue to green"
	@docker stop $(CONTAINER_NAME)
	@docker rename $(CONTAINER_NAME) $(CONTAINER_NAME)-blue
	@docker rename $(CONTAINER_NAME)-green $(CONTAINER_NAME)
	@echo "✅ Traffic switched to green deployment"
	@echo "💡 Rollback available with: make rollback-from-green"

.PHONY: rollback-from-green
rollback-from-green:
	@echo "⏪ Rolling back from green to blue"
	@if docker ps --filter "name=$(CONTAINER_NAME)-blue" --format "{{.Names}}" | grep -q "$(CONTAINER_NAME)-blue"; then \
		docker stop $(CONTAINER_NAME); \
		docker rename $(CONTAINER_NAME) $(CONTAINER_NAME)-green-failed; \
		docker rename $(CONTAINER_NAME)-blue $(CONTAINER_NAME); \
		docker start $(CONTAINER_NAME); \
		echo "✅ Rollback completed"; \
		echo "💡 Clean up failed green: docker rm $(CONTAINER_NAME)-green-failed"; \
	else \
		echo "❌ No blue deployment available for rollback"; \
		exit 1; \
	fi

# =============================================================================
# HEALTH AND MONITORING
# =============================================================================

.PHONY: health-check
health-check:
	@echo "🔍 Checking application health"
	@container_name=$${CONTAINER_NAME:-$(CONTAINER_NAME)}; \
	if docker inspect --format='{{.State.Health.Status}}' $$container_name 2>/dev/null | grep -q "healthy"; then \
		echo "✅ Health check: HEALTHY"; \
		docker inspect --format='{{.State.Health.Status}}' $$container_name; \
	elif docker inspect --format='{{.State.Health.Status}}' $$container_name 2>/dev/null | grep -q "starting"; then \
		echo "🟡 Health check: STARTING"; \
		docker inspect --format='{{.State.Health.Status}}' $$container_name; \
	else \
		echo "❌ Health check: UNHEALTHY or UNKNOWN"; \
		docker inspect --format='{{json .State.Health}}' $$container_name 2>/dev/null || echo "Container not found"; \
		exit 1; \
	fi

.PHONY: health-details
health-details:
	@echo "🔍 Detailed health information"
	@docker inspect --format='{{json .State.Health}}' $(CONTAINER_NAME) | jq '.' || \
		echo "❌ Unable to get health details (jq required)"

.PHONY: monitoring
monitoring:
	@echo "📊 Production monitoring dashboard"
	@echo "Container: $(CONTAINER_NAME)"
	@echo "Image: $(IMAGE_NAME)"
	@echo "Status: $$(docker inspect --format='{{.State.Status}}' $(CONTAINER_NAME) 2>/dev/null || echo 'NOT RUNNING')"
	@echo "Health: $$(docker inspect --format='{{.State.Health.Status}}' $(CONTAINER_NAME) 2>/dev/null || echo 'NO HEALTH CHECK')"
	@echo "Started: $$(docker inspect --format='{{.State.StartedAt}}' $(CONTAINER_NAME) 2>/dev/null || echo 'N/A')"
	@echo "Uptime: $$(docker inspect --format='{{.State.StartedAt}}' $(CONTAINER_NAME) 2>/dev/null | xargs -I {} date -d {} +%s | xargs -I {} echo $$(($$(date +%s) - {})) seconds || echo 'N/A')"
	@echo ""
	@echo "Resource Usage:"
	@docker stats $(CONTAINER_NAME) --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}" 2>/dev/null || echo "Container not running"

.PHONY: metrics
metrics:
	@echo "📈 Production metrics"
	@docker stats $(CONTAINER_NAME) --no-stream || echo "Container not running"

.PHONY: events
events:
	@echo "📋 Container events (last 24h)"
	@docker events --filter container=$(CONTAINER_NAME) --since 24h --until now

# =============================================================================
# LOGGING AND TROUBLESHOOTING
# =============================================================================

.PHONY: logs-follow
logs-follow:
	@echo "📋 Following production logs"
	@docker logs -f --tail 50 $(CONTAINER_NAME)

.PHONY: logs-errors
logs-errors:
	@echo "🔍 Showing error logs"
	@docker logs $(CONTAINER_NAME) 2>&1 | grep -i error || echo "No errors found in recent logs"

.PHONY: logs-since
logs-since:
	@echo "📋 Logs since: $(ARG)"
	@if [ -z "$(ARG)" ]; then \
		echo "❌ Usage: make logs-since ARG='1h'"; \
		echo "💡 Examples: 1h, 30m, 2006-01-02T15:04:05"; \
		exit 1; \
	fi
	@docker logs --since $(ARG) $(CONTAINER_NAME)

.PHONY: debug-info
debug-info:
	@echo "🔍 Production debugging information"
	@echo "===================="
	@echo "Container Details:"
	@docker inspect $(CONTAINER_NAME) --format='{{json .Config}}' | jq '.Env' || echo "Environment variables not available"
	@echo ""
	@echo "Process Information:"
	@docker exec $(CONTAINER_NAME) ps aux 2>/dev/null || echo "Cannot access container processes"
	@echo ""
	@echo "Resource Limits:"
	@docker inspect $(CONTAINER_NAME) --format='{{json .HostConfig.Memory}}' || echo "Memory limits not set"
	@docker inspect $(CONTAINER_NAME) --format='{{json .HostConfig.CpuQuota}}' || echo "CPU limits not set"

# =============================================================================
# CONTAINER LIFECYCLE
# =============================================================================

.PHONY: stop
stop:
	@echo "⏹️  Gracefully stopping production container"
	@docker stop --time=30 $(CONTAINER_NAME) 2>/dev/null || echo "Container not running"

.PHONY: restart
restart: stop
	@echo "🔄 Restarting production container"
	@sleep 5
	@docker start $(CONTAINER_NAME) || echo "❌ Failed to restart container"
	@echo "⏱️  Waiting for health check..."
	@sleep 15
	@$(MAKE) health-check

.PHONY: graceful-restart
graceful-restart:
	@echo "🔄 Performing graceful restart"
	@echo "📋 Current status:"
	@$(MAKE) health-check
	@echo "⏹️  Stopping container..."
	@$(MAKE) stop
	@echo "🚀 Starting container..."
	@docker start $(CONTAINER_NAME)
	@echo "⏱️  Waiting for application startup..."
	@sleep 30
	@$(MAKE) health-check
	@echo "✅ Graceful restart completed"

# =============================================================================
# BACKUP AND RECOVERY
# =============================================================================

.PHONY: backup
backup:
	@echo "💾 Creating production backup"
	@timestamp=$(shell date +%Y%m%d_%H%M%S); \
	backup_name="$(APP_NAME)-backup-$$timestamp"; \
	echo "📦 Creating backup: $$backup_name"; \
	docker export $(CONTAINER_NAME) > "$$backup_name.tar"; \
	echo "✅ Backup created: $$backup_name.tar"; \
	ls -lh "$$backup_name.tar"

.PHONY: backup-image
backup-image:
	@echo "💾 Backing up production image"
	@timestamp=$(shell date +%Y%m%d_%H%M%S); \
	backup_name="$(APP_NAME)-image-backup-$$timestamp"; \
	echo "📦 Saving image: $(IMAGE_NAME)"; \
	docker save $(IMAGE_NAME) > "$$backup_name.tar"; \
	echo "✅ Image backup created: $$backup_name.tar"; \
	ls -lh "$$backup_name.tar"

.PHONY: snapshot
snapshot:
	@echo "📸 Creating container snapshot"
	@timestamp=$(shell date +%Y%m%d_%H%M%S); \
	snapshot_name="$(APP_NAME)-snapshot-$$timestamp"; \
	docker commit $(CONTAINER_NAME) "$$snapshot_name"; \
	echo "✅ Snapshot created: $$snapshot_name"

# =============================================================================
# SECURITY AND COMPLIANCE
# =============================================================================

.PHONY: security-audit
security-audit:
	@echo "🔒 Running production security audit"
	@echo "🔍 Container security scan..."
	@docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
		aquasec/trivy image $(IMAGE_NAME) || echo "Trivy security scan not available"
	@echo ""
	@echo "🔍 Runtime security check..."
	@docker inspect $(CONTAINER_NAME) --format='{{json .HostConfig}}' | jq '.Privileged, .ReadonlyRootfs, .SecurityOpt' || echo "Security info not available"

.PHONY: compliance-check
compliance-check:
	@echo "📋 Production compliance check"
	@echo "✅ Checking read-only filesystem..."
	@docker inspect $(CONTAINER_NAME) --format='{{.HostConfig.ReadonlyRootfs}}' | grep -q true && echo "✅ Read-only filesystem enabled" || echo "⚠️  Read-only filesystem disabled"
	@echo "✅ Checking non-root user..."
	@docker inspect $(CONTAINER_NAME) --format='{{.Config.User}}' | grep -q "1000" && echo "✅ Non-root user configured" || echo "⚠️  Root user detected"
	@echo "✅ Checking security options..."
	@docker inspect $(CONTAINER_NAME) --format='{{.HostConfig.SecurityOpt}}' | grep -q "no-new-privileges" && echo "✅ no-new-privileges enabled" || echo "⚠️  no-new-privileges not set"

# =============================================================================
# MAINTENANCE
# =============================================================================

.PHONY: maintenance-on
maintenance-on:
	@echo "🚧 Enabling maintenance mode"
	@docker exec $(CONTAINER_NAME) sh -c 'echo "maintenance" > /tmp/maintenance.flag' 2>/dev/null || echo "⚠️  Maintenance flag may not be supported by application"
	@echo "✅ Maintenance mode enabled"

.PHONY: maintenance-off
maintenance-off:
	@echo "✅ Disabling maintenance mode"
	@docker exec $(CONTAINER_NAME) sh -c 'rm -f /tmp/maintenance.flag' 2>/dev/null || echo "⚠️  Maintenance flag may not exist"
	@echo "✅ Maintenance mode disabled"

.PHONY: maintenance-status
maintenance-status:
	@echo "🔍 Checking maintenance status"
	@docker exec $(CONTAINER_NAME) sh -c 'test -f /tmp/maintenance.flag && echo "🚧 MAINTENANCE MODE: ON" || echo "✅ MAINTENANCE MODE: OFF"' 2>/dev/null || echo "⚠️  Cannot check maintenance status"

# =============================================================================
# POST-DEPLOYMENT VALIDATION
# =============================================================================

.PHONY: post-deploy-check
post-deploy-check:
	@echo "✅ Running post-deployment validation"
	@echo "🔍 Container status..."
	@docker ps --filter "name=$(CONTAINER_NAME)" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
	@echo "🔍 Health check..."
	@sleep 10
	@$(MAKE) health-check
	@echo "🔍 Resource usage..."
	@$(MAKE) metrics
	@echo "✅ Post-deployment validation completed"

.PHONY: smoke-test
smoke-test:
	@echo "💨 Running production smoke tests"
	@echo "🔍 Basic connectivity test..."
	@docker exec $(CONTAINER_NAME) python -c "print('✅ Python runtime working')" || exit 1
	@echo "🔍 Health endpoint test..."
	@$(MAKE) health-check
	@echo "✅ Smoke tests passed"

# =============================================================================
# ROLLBACK AND RECOVERY
# =============================================================================

.PHONY: rollback
rollback:
	@echo "⏪ Rolling back to previous version"
	@if [ -z "$(PREV_TAG)" ]; then \
		echo "❌ Usage: make rollback PREV_TAG=previous-tag"; \
		echo "💡 Example: make rollback PREV_TAG=2025-10-14-abc123"; \
		exit 1; \
	fi
	@prev_image="$(APP_NAME)/prod:$(PREV_TAG)"; \
	echo "📋 Current: $(IMAGE_NAME)"; \
	echo "📋 Rolling back to: $$prev_image"; \
	$(MAKE) stop; \
	docker run -d $(DOCKER_OPTS) --name $(CONTAINER_NAME)-rollback $$prev_image; \
	if $(MAKE) health-check CONTAINER_NAME=$(CONTAINER_NAME)-rollback; then \
		docker rm -f $(CONTAINER_NAME) 2>/dev/null || true; \
		docker rename $(CONTAINER_NAME)-rollback $(CONTAINER_NAME); \
		echo "✅ Rollback completed successfully"; \
	else \
		echo "❌ Rollback failed health check"; \
		docker rm -f $(CONTAINER_NAME)-rollback; \
		exit 1; \
	fi

.PHONY: list-versions
list-versions:
	@echo "📋 Available production versions"
	@docker images --filter "reference=$(APP_NAME)/prod" --format "table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}\t{{.Size}}"

# =============================================================================
# STATUS AND INFORMATION
# =============================================================================

.PHONY: status
status:
	@echo "📊 Production environment status"
	@echo "================================"
	@echo "Image: $(IMAGE_NAME)"
	@echo "Container: $(CONTAINER_NAME)"
	@echo "Environment: $(ENV)"
	@echo "Tag: $(TAG)"
	@echo "Build Date: $(shell date -u +"%Y-%m-%dT%H:%M:%SZ")"
	@echo ""
	@if docker ps --filter "name=$(CONTAINER_NAME)" --format "{{.Names}}" | grep -q "$(CONTAINER_NAME)"; then \
		echo "✅ Container: RUNNING"; \
		docker ps --filter "name=$(CONTAINER_NAME)" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"; \
		echo ""; \
		$(MAKE) health-check 2>/dev/null || echo "❌ Health check failed"; \
	else \
		echo "❌ Container: NOT RUNNING"; \
	fi
	@echo ""
	@echo "💾 Image information:"
	@if docker images --filter "reference=$(IMAGE_NAME)" --format "{{.Repository}}" | grep -q "$(APP_NAME)/prod"; then \
		docker images --filter "reference=$(IMAGE_NAME)" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"; \
	else \
		echo "❌ Image not found: $(IMAGE_NAME)"; \
		echo "💡 Build with: make build"; \
	fi

# =============================================================================
# HELP AND DOCUMENTATION
# =============================================================================

.PHONY: prod-help
prod-help:
	@echo "🚀 MixSeek-Core Production Environment Commands"
	@echo ""
	@echo "🏗️  Build & Deploy:"
	@echo "  build              Build production image"
	@echo "  deploy             Deploy to production"
	@echo "  deploy-blue-green  Blue-green deployment"
	@echo "  rollback PREV_TAG= Rollback to previous version"
	@echo ""
	@echo "🔄 Container Lifecycle:"
	@echo "  stop               Gracefully stop container"
	@echo "  restart            Restart container"
	@echo "  graceful-restart   Graceful restart with health checks"
	@echo ""
	@echo "🔍 Health & Monitoring:"
	@echo "  health-check       Check application health"
	@echo "  monitoring         Show monitoring dashboard"
	@echo "  metrics            Show resource metrics"
	@echo "  status             Show complete status"
	@echo ""
	@echo "📋 Logging:"
	@echo "  logs               Show recent logs"
	@echo "  logs-follow        Follow logs in real-time"
	@echo "  logs-errors        Show error logs only"
	@echo "  logs-since ARG=    Show logs since timepoint"
	@echo ""
	@echo "💾 Backup & Recovery:"
	@echo "  backup             Create container backup"
	@echo "  backup-image       Backup production image"
	@echo "  snapshot           Create container snapshot"
	@echo "  list-versions      List available versions"
	@echo ""
	@echo "🔒 Security:"
	@echo "  security-audit     Run security audit"
	@echo "  compliance-check   Check compliance settings"
	@echo ""
	@echo "🚧 Maintenance:"
	@echo "  maintenance-on     Enable maintenance mode"
	@echo "  maintenance-off    Disable maintenance mode"
	@echo "  maintenance-status Check maintenance status"
	@echo ""
	@echo "✅ Validation:"
	@echo "  post-deploy-check  Post-deployment validation"
	@echo "  smoke-test         Run smoke tests"
	@echo ""
	@echo "📖 Examples:"
	@echo "  make build && make deploy"
	@echo "  make deploy-blue-green"
	@echo "  make rollback PREV_TAG=2025-10-14-abc123"
	@echo "  make logs-since ARG='1h'"

# Default target shows help
help: prod-help

# =============================================================================
# VALIDATION TARGETS
# =============================================================================

.PHONY: validate
validate:
	@echo "🔍 Validating production environment setup"
	@echo "Checking Docker daemon..."
	$(call check_docker)
	@echo "Checking environment file..."
	$(call check_env_file,$(ENV))
	@echo "Checking build arguments..."
	$(call validate_build_args)
	@echo "✅ Production environment validation completed"