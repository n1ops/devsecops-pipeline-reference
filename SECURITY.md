# Security Policy

## STRIDE Threat Model

### Overview

This document provides a STRIDE-based threat analysis for the DevSecOps Task API deployed on AWS ECS Fargate.

### Threat Analysis

| STRIDE Category | Threat | Mitigation | Status |
|---|---|---|---|
| **Spoofing** | Unauthorized API access | JWT auth with bcrypt password hashing | Implemented |
| **Spoofing** | Token forgery | HS256 JWT with iss/aud/jti claims; secret via Secrets Manager | Implemented |
| **Spoofing** | User enumeration via timing | Dummy bcrypt verify on non-existent user lookups | Implemented |
| **Spoofing** | User enumeration via error messages | Generic "Invalid username or password" on all login failures | Implemented |
| **Spoofing** | Algorithm confusion (`alg: none`) | Explicit algorithm allowlist in `jwt.decode()` | Implemented |
| **Spoofing** | Unauthorized deployment | OIDC federation restricts deploy to `main` branch only | Implemented |
| **Tampering** | SQL injection | SQLAlchemy ORM parameterized queries | Implemented |
| **Tampering** | Mass assignment | Explicit allowlist of updatable fields in PATCH handler | Implemented |
| **Tampering** | Request body manipulation | Pydantic schema validation with field constraints | Implemented |
| **Tampering** | Container image tampering | ECR immutable tags + scan-on-push + single-build provenance | Implemented |
| **Repudiation** | Untraceable API actions | Structured logging to CloudWatch with request IDs | Implemented |
| **Repudiation** | Unauthorized code changes | CODEOWNERS + branch protection + required pipeline | Implemented |
| **Information Disclosure** | Secret leakage in git | Gitleaks scanning with full history | Implemented |
| **Information Disclosure** | Stack trace leakage | Generic 500 handler; docs hidden in production | Implemented |
| **Information Disclosure** | Password hash in response | Response schema explicitly excludes hashed_password | Implemented |
| **Information Disclosure** | Dependency CVEs | pip-audit + Dependabot automated PRs | Implemented |
| **Information Disclosure** | Container OS CVEs | Trivy scanning + slim base image | Implemented |
| **Information Disclosure** | Network traffic visibility | VPC Flow Logs to KMS-encrypted CloudWatch | Implemented |
| **Information Disclosure** | Hardcoded secrets in config | Secrets Manager injection at runtime; startup rejects default secret | Implemented |
| **Denial of Service** | Resource exhaustion | Fargate CPU/memory limits + per-endpoint rate limiting | Implemented |
| **Denial of Service** | Unbounded request body | 1MB body size limit (Content-Length + streaming byte counter) | Implemented |
| **Denial of Service** | Brute force login | Account lockout after 5 attempts + rate limiting (5/min) | Implemented |
| **Elevation of Privilege** | Container breakout | Non-root user, read-only FS, all capabilities dropped, Fargate isolation | Implemented |
| **Elevation of Privilege** | IAM over-permissioning | Least-privilege: task role CloudWatch write-only; deploy role scoped to ECR+ECS | Implemented |
| **Elevation of Privilege** | IDOR / cross-user access | Row-level ownership filter on all task queries | Implemented |

### Security Controls Matrix

| Control | Tool/Method | Pipeline Stage | Frequency |
|---|---|---|---|
| Secret scanning | Gitleaks | Stage 1 | Every push/PR |
| Static analysis (SAST) | Bandit | Stage 2 | Every push/PR |
| Semantic code analysis | CodeQL | Stage 2b | Every push/PR |
| Dependency audit (SCA) | pip-audit | Stage 3 | Every push/PR |
| IaC scanning | Checkov | Stage 4 | Every push/PR |
| Unit & security tests | pytest (73 tests) | Stage 5 | Every push/PR |
| Container scanning | Trivy | Stage 6 | Every push/PR |
| SBOM generation | Syft (SPDX + CycloneDX) | Stage 7 | Every push/PR |
| Dynamic analysis (DAST) | OWASP ZAP | Stage 8 | Every push/PR |
| Security gate | Custom pass/fail logic | Stage 9 | Every push/PR |
| Deployment | OIDC + ECS rolling update | Stage 10 | Push to main |
| Dependency updates | Dependabot | Automated PR | Weekly |
| Secrets management | AWS Secrets Manager | Runtime injection | Continuous |
| Log encryption | KMS with auto-rotation | Infrastructure | Continuous |
| Network monitoring | VPC Flow Logs | Infrastructure | Continuous |
| WAF protection | AWS WAFv2 (3 managed rule groups) | Infrastructure | Continuous |
| Alarm notifications | CloudWatch Alarms + SNS | Infrastructure | Continuous |

### Accepted Risks

The following low-severity findings are intentionally present for scanner demonstration purposes:

1. **Hardcoded default SECRET_KEY** (Bandit B105) — overridden via AWS Secrets Manager in production; startup crashes if default key is used outside debug mode
2. **ECR without KMS encryption** (Checkov CKV_AWS_136) — uses AES-256 server-side encryption by default; CMK adds cost without meaningful security benefit for this use case
3. **OS package CVEs in base image** (Trivy) — slim-bookworm base minimizes attack surface; remaining CVEs tracked via Dependabot

### Remediated Findings (previously accepted)

The following findings were originally planted for scanner demonstration and have since been fully remediated:

| Finding | Remediation |
|---|---|
| HTTP listener without HTTPS (CKV_AWS_2) | ACM certificate + HTTPS listener with TLS 1.3 policy (conditional on `domain_name`) |
| CloudWatch logs without KMS (CKV_AWS_158) | KMS key with auto-rotation applied to all log groups |
| ALB without access logging (CKV_AWS_91) | S3 bucket with encryption, public access block, and 90-day lifecycle |
| Permissive CORS | Wildcard origins only in debug; `allow_credentials=false` when `*` |

### Reporting Vulnerabilities

This is a portfolio/demonstration project. If you find a genuine security issue beyond the accepted risks listed above, please open an issue.
