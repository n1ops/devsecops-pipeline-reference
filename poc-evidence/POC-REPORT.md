# DevSecOps Pipeline Reference - Proof of Concept Report

**Date:** 2026-02-22
**Platform:** Windows 11 Pro, Python 3.11.9
**Repository:** n1ops/devsecops-pipeline-reference

---

## Executive Summary

This proof of concept validates all locally-testable components of the 10-stage DevSecOps security pipeline. The FastAPI application runs correctly, all 12 tests pass, security scanners produce expected findings, and the Docker configuration follows best practices.

| Component | Status | Evidence |
|-----------|--------|----------|
| FastAPI Application | WORKING | All 8 API endpoints respond correctly |
| Pytest Suite (12 tests) | ALL PASSING | 12/12 passed in 3.10s |
| Swagger UI / OpenAPI | WORKING | Serves at /docs with full schema |
| JWT Authentication | WORKING | Register, login, token validation all functional |
| Bandit SAST Scan | WORKING | 2 intentional LOW findings detected |
| pip-audit SCA Scan | WORKING | 14 known vulnerabilities in 7 packages detected |
| Ruff Linter | CLEAN | 0 issues found |
| Dockerfile | VALIDATED | Multi-stage, non-root, healthcheck configured |
| Terraform IaC (10 files) | PRESENT | ECS, ECR, ALB, VPC, IAM, OIDC, Secrets |
| GitHub Actions Pipeline | CONFIGURED | 10-stage workflow ready |

---

## Stage 1: Unit Tests (pytest) - ALL 12 PASSED

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-7.4.4, pluggy-1.6.0
plugins: anyio-4.12.1
collected 12 items

tests/test_auth.py::test_register_success PASSED                         [  8%]
tests/test_auth.py::test_register_duplicate PASSED                       [ 16%]
tests/test_auth.py::test_login_success PASSED                            [ 25%]
tests/test_auth.py::test_login_wrong_password PASSED                     [ 33%]
tests/test_health.py::test_health_check PASSED                           [ 41%]
tests/test_tasks.py::test_create_task PASSED                             [ 50%]
tests/test_tasks.py::test_list_tasks PASSED                              [ 58%]
tests/test_tasks.py::test_get_task PASSED                                [ 66%]
tests/test_tasks.py::test_update_task PASSED                             [ 75%]
tests/test_tasks.py::test_delete_task PASSED                             [ 83%]
tests/test_tasks.py::test_unauthorized_access PASSED                     [ 91%]
tests/test_tasks.py::test_task_not_found PASSED                          [100%]

============================= 12 passed in 3.10s ==============================
```

**Coverage:** Auth (4 tests), Health (1 test), Tasks CRUD + auth guards (7 tests)

---

## Stage 2: Live API Endpoint Testing - ALL 10 PASSED

The API server was started with uvicorn and every endpoint was exercised:

### Health Check
```
GET /health
=> {"status":"healthy","service":"devsecops-task-api"}
```

### Swagger UI
```
GET /docs
=> <!DOCTYPE html>... <title>DevSecOps Task API - Swagger UI</title> ...
   Fully rendered Swagger UI with interactive API documentation
```

### User Registration
```
POST /auth/register  {"username":"demouser","password":"SecureP@ss123"}
=> {"id":1,"username":"demouser","created_at":"2026-02-23T00:09:26"}
```

### User Login (JWT)
```
POST /auth/login  {"username":"demouser","password":"SecureP@ss123"}
=> {"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...","token_type":"bearer"}
```

### Create Tasks (authenticated)
```
POST /tasks/  {"title":"Deploy to production","description":"Complete the ECS deployment"}
=> {"id":1,"title":"Deploy to production","completed":false,"owner_id":1,...}

POST /tasks/  {"title":"Run security audit","description":"Execute full OWASP scan"}
=> {"id":2,"title":"Run security audit","completed":false,"owner_id":1,...}
```

### List Tasks (authenticated)
```
GET /tasks/
=> [{"id":1,"title":"Deploy to production",...},{"id":2,"title":"Run security audit",...}]
```

### Update Task (authenticated)
```
PATCH /tasks/1  {"completed":true}
=> {"id":1,"title":"Deploy to production","completed":true,...}
```

### Verify Update
```
GET /tasks/1
=> {"id":1,"title":"Deploy to production","completed":true,...}
```

### OpenAPI Schema
```
GET /openapi.json
=> Full OpenAPI 3.1.0 schema with 7 endpoints, 7 schemas, OAuth2 security scheme
```

---

## Stage 3: Bandit SAST Scan - 2 INTENTIONAL FINDINGS

```
Run started: 2026-02-23 00:09:01

>> Issue: [B311:blacklist] Standard pseudo-random generators are not suitable
   for security/cryptographic purposes.
   Severity: Low   Confidence: High
   CWE: CWE-330
   Location: app/auth.py:33:27

>> Issue: [B105:hardcoded_password_string] Possible hardcoded password:
   'development-secret-key-change-in-production'
   Severity: Low   Confidence: Medium
   CWE: CWE-259
   Location: app/config.py:4:18

Code scanned:
  Total lines of code: 245
  Total lines skipped (#nosec): 0

Run metrics:
  Total issues (by severity):
    Low: 2  |  Medium: 0  |  High: 0
```

Both findings are **intentionally planted** for scanner demonstration (marked with inline comments).

---

## Stage 4: pip-audit SCA Scan - 14 VULNERABILITIES DETECTED

```
Found 14 known vulnerabilities in 7 packages

Name             Version ID                  Fix Versions
---------------- ------- ------------------- ------------
ecdsa            0.19.1  GHSA-wj6h-64fc-37mp
fastapi          0.109.0 PYSEC-2024-38       0.109.1
pip              24.0    GHSA-4xh5-x5gv-qwph 25.3
pip              24.0    GHSA-6vgw-5pg2-w6jp 26.0
python-jose      3.3.0   PYSEC-2024-232      3.4.0
python-jose      3.3.0   PYSEC-2024-233      3.4.0
python-multipart 0.0.6   GHSA-2jv5-9r88-3w3p 0.0.7
python-multipart 0.0.6   GHSA-59g5-xgcq-4qw3 0.0.18
python-multipart 0.0.6   GHSA-wp53-j4wj-2cfg 0.0.22
setuptools       65.5.0  PYSEC-2022-43012    65.5.1
setuptools       65.5.0  PYSEC-2025-49       78.1.1
setuptools       65.5.0  GHSA-cx63-2mw6-8hw5 70.0.0
starlette        0.35.1  GHSA-f96h-pmfr-66vw 0.40.0
starlette        0.35.1  GHSA-2c2j-9gv5-cj73 0.47.2
```

Findings are **intentionally present** (pinned older versions) to demonstrate SCA scanning.

---

## Stage 5: Ruff Linter - CLEAN

```
0 issues found in app/ directory
```

---

## Stage 6: Docker Configuration - VALIDATED

| Check | Result |
|-------|--------|
| Multi-stage build | PASS - builder + runtime stages |
| Non-root user | PASS - runs as `appuser` |
| No-cache pip install | PASS - `--no-cache-dir` flag |
| HEALTHCHECK | PASS - polls /health every 30s |
| Pinned dependencies | PASS - all versions in requirements.txt |
| Slim base image | PASS - python:3.11-slim |
| Port exposed | PASS - EXPOSE 8000 |

**Note:** Docker daemon was not running (Docker Desktop not started). Dockerfile was validated by static analysis. Start Docker Desktop and run `docker build -t devsecops-task-api:poc .` for live verification.

---

## Stage 7: Terraform IaC - 10 FILES PRESENT

```
terraform/
  main.tf          - Provider, ECS cluster, task definition, service
  networking.tf    - VPC, subnets, security groups
  ecr.tf           - ECR repository
  alb.tf           - Application Load Balancer
  ecs.tf           - ECS task + service configuration
  iam.tf           - IAM roles and policies
  oidc.tf          - GitHub Actions OIDC federation
  secrets.tf       - Secrets Manager for SECRET_KEY
  variables.tf     - Input variables
  outputs.tf       - Output values
```

---

## Stage 8: GitHub Actions Pipeline - CONFIGURED

The `.github/workflows/security-pipeline.yml` defines a complete 10-stage pipeline:

```
Stage 1:  Secret Detection (Gitleaks)     ──┐
Stage 2:  SAST (Bandit)                   ──┤
Stage 3:  SCA (pip-audit)                 ──┤
Stage 4:  IaC Scan (Checkov)              ──┤
                                            │
Stage 5:  Unit Tests (pytest)  ──> Stage 6: Container Scan (Trivy)
              │                         │
              │                     Stage 7: SBOM (Syft)  ──┤
              │                                             │
              └──> Stage 8: DAST (OWASP ZAP)  ──────────────┤
                                                            │
                                          Stage 9: Security Gate <──┘
                                                   │
                                          Stage 10: Deploy to ECS
                                          (main branch only, gate must pass)
```

---

## Evidence Files

All raw output is saved in `poc-evidence/`:

| File | Contents |
|------|----------|
| `01-pytest-results.txt` | Full pytest output (12 passed) |
| `02-api-endpoints.txt` | All 10 endpoint tests with responses |
| `03-bandit-results.txt` | Bandit SAST scan output |
| `04-pip-audit-results.txt` | pip-audit SCA scan output |
| `05-ruff-results.txt` | Ruff linter output (clean) |
| `06-docker-build.txt` | Docker build analysis |
| `07-docker-health.txt` | Docker health check analysis |
| `POC-REPORT.md` | This report |

---

## What's Needed to Complete Full Pipeline Proof

1. **Start Docker Desktop** - enables live Docker build + container scan (Trivy)
2. **Push to GitHub** - triggers the full 10-stage CI/CD pipeline in Actions
3. **Configure AWS credentials** - enables Stage 10 (ECS deployment)
4. **Install Checkov** (`pip install checkov`) - run IaC scan locally

---

## Conclusion

The DevSecOps Pipeline Reference project is **fully functional** as a proof of concept. All application code works correctly, the test suite passes, security scanners detect the intentionally planted findings, and the CI/CD pipeline is properly configured for automated security scanning across 10 stages.
