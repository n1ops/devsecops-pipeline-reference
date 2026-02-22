# Security Policy

## STRIDE Threat Model

### Overview

This document provides a STRIDE-based threat analysis for the DevSecOps Task API deployed on AWS ECS Fargate.

### Threat Analysis

| STRIDE Category | Threat | Mitigation | Status |
|----------------|--------|------------|--------|
| **Spoofing** | Unauthorized API access | JWT authentication with bcrypt password hashing | Implemented |
| **Spoofing** | Token forgery | HS256 JWT with configurable secret key via env var | Implemented |
| **Tampering** | SQL injection | SQLAlchemy ORM parameterized queries | Implemented |
| **Tampering** | Request body manipulation | Pydantic schema validation with field constraints | Implemented |
| **Tampering** | Container image tampering | ECR immutable tags + image scanning on push | Implemented |
| **Repudiation** | Untraceable API actions | CloudWatch logging with ECS log driver | Implemented |
| **Repudiation** | Unauthorized code changes | Branch protection + required pipeline checks | Recommended |
| **Information Disclosure** | Secret leakage in git | Gitleaks scanning in CI + `.gitleaks.toml` allowlist | Implemented |
| **Information Disclosure** | Dependency vulnerabilities | pip-audit SCA + Dependabot automated PRs | Implemented |
| **Information Disclosure** | Container OS CVEs | Trivy container scanning + slim base image | Implemented |
| **Denial of Service** | Resource exhaustion | Fargate task CPU/memory limits + ALB health checks | Implemented |
| **Denial of Service** | Unbounded request size | Pydantic field length constraints | Implemented |
| **Elevation of Privilege** | Container breakout | Non-root user in Dockerfile + Fargate isolation | Implemented |
| **Elevation of Privilege** | IAM over-permissioning | Least-privilege task role with scoped policies | Implemented |
| **Information Disclosure** | Hardcoded secrets in config | Secrets Manager injection at runtime; no secrets in image or env | Implemented |
| **Spoofing** | Unauthorized deployment | OIDC federation restricts deploys to `main` branch only | Implemented |

### Security Controls Matrix

| Control | Tool/Method | Pipeline Stage | Frequency |
|---------|------------|----------------|-----------|
| Secret scanning | Gitleaks | Stage 1 | Every push/PR |
| Static analysis (SAST) | Bandit | Stage 2 | Every push/PR |
| Dependency audit (SCA) | pip-audit | Stage 3 | Every push/PR |
| IaC scanning | Checkov | Stage 4 | Every push/PR |
| Unit tests | pytest | Stage 5 | Every push/PR |
| Container scanning | Trivy | Stage 6 | Every push/PR |
| SBOM generation | Syft | Stage 7 | Every push/PR |
| Dynamic analysis (DAST) | OWASP ZAP | Stage 8 | Every push/PR |
| Dependency updates | Dependabot | Automated PR | Weekly |
| Security gate | Custom logic | Stage 9 | Every push/PR |
| Secrets management | AWS Secrets Manager | Runtime injection | Continuous |
| Deployment gate | OIDC + environment protection | Stage 10 | Push to main |

### Accepted Risks

The following findings are intentionally present for scanner demonstration purposes:

1. **Hardcoded default SECRET_KEY** (Bandit B105) — overridden via AWS Secrets Manager in production (injected by ECS at container startup)
2. **`random.randint()` for JTI** (Bandit B311) — non-security-critical use (token tracking, not entropy)
3. **python-jose 3.3.0 CVEs** (pip-audit) — demonstrating SCA detection capabilities
4. **ALB without access logging** (Checkov CKV_AWS_91) — production would enable S3 logging
5. **HTTP listener without HTTPS** (Checkov CKV_AWS_2) — production would use ACM certificate
6. **ECR without KMS encryption** (Checkov CKV_AWS_136) — production would use CMK
7. **CloudWatch logs without KMS** (Checkov CKV_AWS_158) — production would use CMK
8. **Permissive CORS** (ZAP) — production would restrict origins

### Reporting Vulnerabilities

This is a portfolio/demonstration project. If you find a genuine security issue beyond the intentional findings listed above, please open an issue.
