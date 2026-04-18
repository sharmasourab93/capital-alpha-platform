# Capital Alpha Platform

Capital Alpha Platform is an architecture-first Python repository for a production-minded trading and investment intelligence system. The product goal is to provide a disciplined decision-support platform for market data ingestion, portfolio visibility, research workflows, recommendation pipelines, alerting, and execution-adjacent integrations.

This repository intentionally represents the public platform layer only. Proprietary alpha models, strategy logic, ranking systems, and private research processes are excluded.

## Table of Contents

- [Product Intent](#product-intent)
- [Repository Scope](#repository-scope)
- [System Goals](#system-goals)
- [Architecture Direction](#architecture-direction)
- [Target Capability Model](#target-capability-model)
- [Repository Status](#repository-status)
- [Technology Baseline](#technology-baseline)
- [Getting Started](#getting-started)
- [Planned Repository Shape](#planned-repository-shape)
- [Operating Principles](#operating-principles)
- [Delivery Roadmap](#delivery-roadmap)
- [Security and Compliance Notes](#security-and-compliance-notes)
- [Contributing](#contributing)
- [Disclaimer](#disclaimer)

## Product Intent

Most retail and semi-professional market tooling breaks down in one of four ways:

- data is fragmented across brokers, spreadsheets, scripts, and notes
- workflows are too manual to scale with discipline
- automation is too shallow to support repeatable decisions
- systems are overbuilt before the core operating loop is proven

Capital Alpha Platform exists to solve that with a lean, modular system that helps a user:

- ingest and normalize market, broker, and portfolio data
- run scans, backtests, and recurring research workflows
- generate structured recommendations and review queues
- monitor thesis drift, portfolio exposure, and execution outcomes
- surface alerts that support better capital allocation decisions

The intended outcome is not a black-box trading bot. It is a high-trust decision-support system with a human operator at the center.

## Repository Scope

This repository is meant to communicate system design quality, product thinking, and implementation direction for the platform layer.

### Included

- architecture and boundary definition
- backend application structure
- data ingestion patterns
- orchestration and scheduled workflow design
- broker and provider integration boundaries
- portfolio and recommendation service patterns
- alerting and dashboard-facing API direction
- infrastructure and deployment conventions

### Excluded

- proprietary trading strategies
- alpha-generation logic
- ranking formulas and conviction models
- private prompts, research heuristics, or scoring systems
- confidential datasets or live credentials

## System Goals

- Build a modular monolith before introducing service decomposition.
- Keep operating cost low during early product validation.
- Preserve a canonical source of truth for positions, market data, and research artifacts.
- Support both active trading workflows and longer-horizon investing workflows.
- Maintain local-to-cloud execution symmetry wherever possible.
- Design for auditability, reproducibility, and gradual hardening.

## Architecture Direction

The current architectural direction is a modular Python backend with clean domain boundaries and integration adapters around external systems.

```text
Operator / Dashboard / CLI
            |
            v
        API Layer
            |
            v
   Application and Domain Modules
   - market data
   - broker integration
   - portfolio state
   - strategy and backtest orchestration
   - investing research workflows
   - recommendations
   - alerts and notifications
            |
            v
    Persistence and Artifact Storage
    - relational system of record
    - object storage for raw payloads and documents
            |
            v
       External Providers
       - market data APIs
       - broker APIs
       - notification channels
       - optional AI-assisted tooling
```

### Design decisions

- Modular monolith first: fewer moving parts, faster iteration, easier testing.
- Deterministic core with AI-assisted edges: system-of-record data should not depend on LLM output.
- Explicit adapters at system boundaries: market data, brokers, notifications, and external research services should remain replaceable.
- Eventual operational maturity: scheduling, retries, observability, and audit trails should be designed in early even if implemented incrementally.

## Target Capability Model

### Trading workflows

- instrument and market data ingestion
- screening and signal preparation
- backtesting and evaluation support
- recommendation generation
- paper-trading and execution-adjacent review flows
- post-trade monitoring and feedback loops

### Investing workflows

- watchlists and company tracking
- filings, notes, and research artifact ingestion
- thesis tracking and review cadence
- conviction monitoring
- recommendation support for longer-horizon positions

### Shared platform capabilities

- identity and access boundaries
- job orchestration
- notification delivery
- audit logging
- portfolio analytics
- dashboard and API contracts

## Repository Status

This repository is currently in an early foundation stage.

- `pyproject.toml` exists with the initial Python package baseline.
- Application modules, infrastructure code, and implementation directories have not yet been built out.
- The README therefore documents the intended system shape and engineering standards the repo should grow into.

That is deliberate. A system-design-oriented product repo should be explicit about current maturity instead of overstating implementation status.

## Technology Baseline

Current baseline from the repository:

- Python `>=3.13`
- project metadata managed in `pyproject.toml`

Planned baseline as the platform evolves:

- `uv` for dependency and environment management
- Python service/application modules
- PostgreSQL as the primary canonical store
- object storage for raw payloads, documents, and derived artifacts
- background workers for sync, scans, alerts, and research jobs
- API surface for dashboards, automation, and operator tooling

## Getting Started

The repository is not yet feature-complete, but the local development baseline should follow this shape.

### Prerequisites

- Python 3.13+
- `uv` installed locally

### Initial setup

```bash
uv sync
```

If `uv` is not being used yet in your local environment, the current minimum viable setup is still simply installing against the Python version declared in `pyproject.toml`.

### Current state

There is no runnable application entrypoint yet. The next implementation milestone should establish:

- source layout
- environment configuration conventions
- local development commands
- testing baseline
- linting and formatting baseline

## Planned Repository Shape

The exact layout may evolve, but a clean direction for this repo is:

```text
capital-alpha-platform/
|-- pyproject.toml
|-- README.md
|-- src/
|   `-- capital_alpha/
|       |-- api/
|       |-- application/
|       |-- domain/
|       |-- infrastructure/
|       |-- integrations/
|       `-- jobs/
|-- tests/
|-- scripts/
|-- docs/
|   |-- architecture/
|   |-- adr/
|   `-- runbooks/
|-- infra/
`-- .github/
```

Recommended module boundaries:

- `domain`: core entities, policies, value objects, invariants
- `application`: use cases, orchestration, commands, queries
- `infrastructure`: persistence, queues, storage, observability
- `integrations`: provider-specific adapters and clients
- `api`: HTTP or internal service contracts
- `jobs`: scheduled and asynchronous workflows

## Operating Principles

- Human-in-the-loop by default.
- Prefer explicitness over hidden automation.
- Keep core financial state auditable.
- Separate proprietary alpha from reusable platform engineering.
- Start simple, but preserve clean seams for later scale.
- Document architectural decisions as the codebase grows.

## Delivery Roadmap

Suggested progression for this repository:

1. Establish package structure, configuration strategy, and developer tooling.
2. Implement foundational domain modules for market data, broker state, and portfolio views.
3. Add ingestion jobs, persistence models, and integration adapters.
4. Introduce recommendation, alerting, and dashboard-facing APIs.
5. Harden operations with tests, observability, runbooks, and deployment automation.

## Security and Compliance Notes

- Never commit real broker credentials, API tokens, or production secrets.
- Treat market, execution, and portfolio data as sensitive by default.
- Keep auditability in mind for recommendations, state transitions, and operator actions.
- If the system later handles regulated workflows, compliance controls must be formalized outside this README.

## Contributing

Contributions should preserve the repo's core direction:

- keep boundaries explicit
- avoid premature microservices
- prefer testable, deterministic workflows
- document significant architectural decisions
- do not add proprietary strategy logic to the public platform layer

As the implementation matures, this section should be expanded with:

- coding standards
- test commands
- pull request expectations
- architecture decision record requirements

## Disclaimer

This repository is for software engineering and system design purposes. It does not provide financial advice, investment advice, or execution guarantees. Any future production use of this platform should include appropriate operational controls, risk management, and legal review.
