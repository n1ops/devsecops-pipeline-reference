# Plan: Make the DevSecOps Pipeline Run on Any Repo You Push To

## The Goal

Right now the security pipeline only runs inside the `devsecops-pipeline-reference` repo. You want it so that **any project on your GitHub profile** automatically goes through this pipeline when you push code. You write code, push it, and the security checks + deploy happen without copying the entire pipeline into every repo.

## How This Works (The Concept)

GitHub has a feature called **reusable workflows**. Instead of copy-pasting a 400-line YAML file into every repo, you:

1. Keep the full pipeline in **one central repo** (this one — `devsecops-pipeline-reference`)
2. In each of your other project repos, add a **tiny caller file** (~20 lines) that says _"go run the pipeline from that other repo"_
3. The caller file passes a few project-specific settings (language, test command, etc.) as inputs

Think of it like a function call — the big pipeline is the function definition, and each repo just calls it with different arguments.

```
your-node-project/.github/workflows/security.yml  (20 lines — the caller)
        │
        │  "uses: n1ops/devsecops-pipeline-reference/.github/workflows/reusable-pipeline.yml@main"
        │  "with: language=node, test-command=npm test"
        │
        ▼
devsecops-pipeline-reference/.github/workflows/reusable-pipeline.yml  (the full pipeline)
```

---

## What You Need to Do (Step by Step)

### Step 1: Enable workflow sharing on this repo

Since `devsecops-pipeline-reference` is private, you need to allow your other repos to access its workflows.

1. Go to **github.com/n1ops/devsecops-pipeline-reference**
2. Click **Settings** → **Actions** → **General**
3. Under the **Access** section, select **"Accessible from repositories owned by the user account 'n1ops'"**
4. Click **Save**

> **Alternative:** If you make this repo **public**, this step is unnecessary — any repo can call workflows from public repos. Since this is a portfolio project, making it public is probably ideal anyway.

### Step 2: Create the reusable workflow

Create a new file in this repo at `.github/workflows/reusable-pipeline.yml`. This is a **parameterized version** of the current pipeline that accepts inputs like language, test command, etc.

The key difference from the current pipeline: the trigger changes from `on: push/pull_request` to `on: workflow_call` with inputs.

Here's the structure (Claude can build the full file tomorrow):

```yaml
name: Reusable DevSecOps Pipeline

on:
  workflow_call:
    inputs:
      # ── What language/stack is this project? ──
      language:
        description: "Programming language for CodeQL (python, javascript, go, java, etc.)"
        type: string
        required: true

      # ── How to install dependencies ──
      install-command:
        description: "Command to install project dependencies"
        type: string
        default: "pip install -r requirements.txt"

      # ── How to run tests ──
      test-command:
        description: "Command to run the test suite"
        type: string
        default: "pytest tests/ -v --tb=short"

      # ── SAST ──
      sast-command:
        description: "Command to run static analysis (leave empty to skip)"
        type: string
        default: ""

      # ── SCA ──
      sca-command:
        description: "Command to run dependency audit (leave empty to skip)"
        type: string
        default: ""

      # ── Does this project have Terraform? ──
      has-terraform:
        description: "Whether to run Checkov IaC scanning"
        type: boolean
        default: false

      terraform-directory:
        description: "Path to Terraform files"
        type: string
        default: "terraform/"

      # ── Does this project have a Dockerfile? ──
      has-docker:
        description: "Whether to build and scan a container image"
        type: boolean
        default: true

      # ── DAST ──
      app-start-command:
        description: "Command to start the app for DAST scanning (leave empty to skip DAST)"
        type: string
        default: ""

      app-port:
        description: "Port the app listens on for DAST"
        type: string
        default: "8000"

      # ── Image / Deploy ──
      image-name:
        description: "Docker image name"
        type: string
        default: "app"

      python-version:
        description: "Python version to use (if applicable)"
        type: string
        default: "3.11"

      node-version:
        description: "Node.js version to use (if applicable)"
        type: string
        default: "20"

    secrets:
      AWS_ROLE_ARN:
        required: false

# ... then the same jobs as the current pipeline, but using ${{ inputs.xxx }}
# instead of hardcoded values
```

### Step 3: In each of your project repos, add a caller workflow

For example, if you have a Node.js project:

**`your-node-project/.github/workflows/security.yml`**
```yaml
name: Security Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read
  security-events: write

jobs:
  security:
    uses: n1ops/devsecops-pipeline-reference/.github/workflows/reusable-pipeline.yml@main
    with:
      language: javascript
      install-command: "npm ci"
      test-command: "npm test"
      sast-command: "npx eslint --ext .js,.ts src/"
      sca-command: "npm audit --audit-level=high"
      has-terraform: false
      has-docker: true
      app-start-command: "npm start &"
      app-port: "3000"
      image-name: "my-node-app"
      node-version: "20"
    secrets: inherit
```

For a Python project:

**`your-python-project/.github/workflows/security.yml`**
```yaml
name: Security Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read
  security-events: write

jobs:
  security:
    uses: n1ops/devsecops-pipeline-reference/.github/workflows/reusable-pipeline.yml@main
    with:
      language: python
      install-command: "pip install -r requirements.txt"
      test-command: "pytest tests/ -v"
      sast-command: "bandit -r src/ -f sarif -o bandit-results.sarif"
      sca-command: "pip-audit -r requirements.txt"
      has-terraform: false
      has-docker: true
      app-start-command: "uvicorn app.main:app --host 0.0.0.0 --port 8000 &"
      app-port: "8000"
      image-name: "my-python-app"
      python-version: "3.11"
    secrets: inherit
```

That's it — ~20 lines per repo. The full pipeline logic lives in one place.

### Step 4: Keep the original pipeline too

The current `security-pipeline.yml` stays as-is for this repo. You'll have two workflow files:
- `security-pipeline.yml` — the original, runs on this repo directly
- `reusable-pipeline.yml` — the parameterized version other repos call

---

## What Each Stage Looks Like in the Reusable Version

Here's how the stages adapt based on inputs:

| Stage | Behavior |
|---|---|
| **Secret Detection** | Runs Gitleaks — no changes needed, works on any repo |
| **SAST** | Runs `inputs.sast-command` if provided, skips if empty |
| **CodeQL** | Uses `inputs.language` to configure CodeQL |
| **SCA** | Runs `inputs.sca-command` if provided, skips if empty |
| **IaC Scan** | Runs Checkov on `inputs.terraform-directory` if `inputs.has-terraform` is true |
| **Unit Tests** | Runs `inputs.test-command` after `inputs.install-command` |
| **Container Scan** | Builds and scans with Trivy if `inputs.has-docker` is true |
| **SBOM** | Generates SPDX + CycloneDX if `inputs.has-docker` is true |
| **DAST** | Starts app with `inputs.app-start-command`, runs ZAP against `localhost:inputs.app-port` — skips if no start command |
| **Security Gate** | Same pass/fail logic — works regardless of language |
| **Deploy** | Only runs if `AWS_ROLE_ARN` secret is provided and it's a push to main |

---

## Things to Know

### Secrets

- Each project repo that wants to **deploy** needs the `AWS_ROLE_ARN` secret configured (or its own deploy credentials)
- `secrets: inherit` passes all the calling repo's secrets through to the reusable workflow
- `GITHUB_TOKEN` is automatically available — no configuration needed

### Limitations

- A reusable workflow can accept a **maximum of 10 inputs** in the `with:` block — if you need more, group settings into a JSON string input
- The caller job **cannot** define its own `steps:` or `runs-on:` — those are defined inside the reusable workflow
- Reusable workflows can be **nested up to 10 levels deep**
- `env:` variables from the caller do **not** propagate — use `inputs` instead

### What stays the same across all repos

These tools are **language-agnostic** and require zero configuration changes:
- Gitleaks (secret detection)
- Checkov (IaC scanning)
- Trivy (container scanning)
- Syft (SBOM generation)
- OWASP ZAP (DAST)
- Security Gate (pass/fail logic)

### What changes per project

These need project-specific inputs:
- SAST tool and command (Bandit for Python, ESLint for JS, gosec for Go)
- SCA tool and command (pip-audit, npm audit, govulncheck)
- Test runner command
- App start command (for DAST)
- Language (for CodeQL)

---

## Order of Operations for Tomorrow

1. [ ] **Enable workflow sharing** on `devsecops-pipeline-reference` (Settings → Actions → Access)
2. [ ] **Create `reusable-pipeline.yml`** — parameterized version of the current pipeline with `on: workflow_call` and inputs
3. [ ] **Test it** by adding a 20-line caller workflow to one of your other repos (like `CoachPulse` or `terraform-project`)
4. [ ] Push to the other repo and verify the pipeline runs from the central repo
5. [ ] Once confirmed working, add the caller workflow to any other repos you want covered

---

## End Result

```
n1ops/devsecops-pipeline-reference          ← The central pipeline (source of truth)
    └── .github/workflows/
        ├── security-pipeline.yml           ← Runs on THIS repo (unchanged)
        └── reusable-pipeline.yml           ← Called by OTHER repos

n1ops/CoachPulse                            ← Any other project
    └── .github/workflows/
        └── security.yml                    ← 20-line caller file

n1ops/terraform-project                     ← Any other project
    └── .github/workflows/
        └── security.yml                    ← 20-line caller file

n1ops/some-future-project                   ← Any other project
    └── .github/workflows/
        └── security.yml                    ← 20-line caller file
```

Every push to any of these repos triggers the same pipeline. One place to maintain, one place to update, consistent security across everything.
