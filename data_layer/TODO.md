# 4-Day Hackathon TODO Plan

**Theme:** Capital Alpha Data Layer v1  
**Mode:** REST-first  
**Daily capacity:** 6 hours  
**Structure:** 3 blocks × 2 hours

## End goal by Day 4

You must finish with:

- Data Layer architecture fixed
- Platform vs Brain boundaries fixed
- Broker abstraction fixed
- One REST broker adapter working
- One canonical market data model working
- One end-to-end ingestion path working
- CloudFormation baseline ready
- Core tests + docs ready

---

# Day 1 — Architecture and contracts

## Goal
Lock the design. No drift. No blind coding.

## Block 1 — System boundary
- [ ] Define what belongs to **Data Layer**
- [ ] Define what belongs to **Platform**
- [ ] Define what belongs to **Brain**
- [ ] Define what is **out of scope**

## Block 2 — Core flow
- [ ] Define input trigger
- [ ] Define broker REST fetch flow
- [ ] Define normalization flow
- [ ] Define output path: **persist first**
- [ ] Define consumer access path

## Block 3 — Contracts and diagrams
- [ ] Define canonical market data contract
- [ ] Define broker abstraction contract
- [ ] Draw architecture diagram
- [ ] Draw sequence/data flow diagram
- [ ] Write 3–5 ADR decisions

## End-of-day output
- [ ] Architecture diagram complete
- [ ] Data flow diagram complete
- [ ] Canonical model draft complete
- [ ] Broker abstraction draft complete
- [ ] Scope fixed

## Hard stop
Do **not** code implementation before this is done.

---

# Day 2 — Code skeleton and abstractions

## Goal
Build the backbone correctly.

## Block 1 — Repo and package structure
- [ ] Create project structure
- [ ] Create modules:
  - [ ] `interfaces`
  - [ ] `adapters`
  - [ ] `models`
  - [ ] `services`
  - [ ] `storage`
  - [ ] `config`
  - [ ] `tests`

## Block 2 — Contracts and models
- [ ] Create broker interface
- [ ] Create adapter base structure
- [ ] Create canonical market data schema/model
- [ ] Create raw broker response model
- [ ] Create request/response envelope

## Block 3 — Runtime skeleton
- [ ] Set up config/env loading
- [ ] Set up logging skeleton
- [ ] Set up service orchestration layer
- [ ] Stub future websocket extension point
- [ ] Make app runnable locally

## End-of-day output
- [ ] Clean code skeleton ready
- [ ] Contracts implemented
- [ ] Canonical models ready
- [ ] Config/bootstrap ready
- [ ] Logging base ready

## Hard stop
Do **not** implement multiple brokers.

---

# Day 3 — One real working REST path

## Goal
Make one vertical slice work end-to-end.

## Block 1 — Broker adapter
- [ ] Pick **one broker**
- [ ] Pick **one use case**
  - [ ] quote fetch
  - or
  - [ ] OHLC fetch
- [ ] Implement REST call
- [ ] Handle auth/config/timeouts

## Block 2 — Normalization and output
- [ ] Map broker response to canonical model
- [ ] Implement persistence path
- [ ] Add success/failure logs
- [ ] Handle bad/malformed payloads

## Block 3 — End-to-end run
- [ ] Create one entry point
  - [ ] service call
  - or
  - [ ] simple API
  - or
  - [ ] CLI
- [ ] Run full flow
- [ ] Validate saved output
- [ ] Capture weak spots for refactor

## End-of-day output
- [ ] One broker adapter working
- [ ] One normalized output working
- [ ] One end-to-end REST path working
- [ ] Logs visible
- [ ] Main architectural weak spots identified

## Hard stop
Do **not** start websocket implementation.

---

# Day 4 — Cloud baseline, tests, hardening, docs

## Goal
Make the work credible and reusable.

## Block 1 — CloudFormation baseline
- [ ] Create base CloudFormation template
- [ ] Define parameters and outputs
- [ ] Add minimum resources:
  - [ ] IAM role/policy
  - [ ] storage resource
  - [ ] logging group
  - [ ] compute placeholder if needed

## Block 2 — Tests
- [ ] Unit test canonical model validation
- [ ] Unit test normalization logic
- [ ] Unit test broker adapter behavior
- [ ] Integration test one REST flow
- [ ] Failure-path test:
  - [ ] timeout
  - [ ] malformed payload
  - [ ] empty response

## Block 3 — Hardening and docs
- [ ] Refactor obvious design/code smells
- [ ] Write README
- [ ] Document architecture decisions
- [ ] Write next backlog:
  - [ ] websocket support
  - [ ] queue/event publishing
  - [ ] more brokers
  - [ ] observability expansion

## End-of-day output
- [ ] CloudFormation baseline ready
- [ ] Core tests ready
- [ ] Code cleaned
- [ ] README ready
- [ ] Backlog for Hackathon 2 ready

## Hard stop
Do **not** chase polish beyond the core flow.

---

# Priority order

If time slips, protect in this order:

1. **Architecture**
2. **Canonical contract**
3. **Broker abstraction**
4. **One working REST path**
5. **Cloud baseline**
6. **Tests**
7. **Docs**

---

# Success checklist

Hackathon is successful only if all are true:

- [ ] I can explain the Data Layer architecture clearly
- [ ] I have one broker abstraction in place
- [ ] I have one REST adapter working
- [ ] I have one canonical internal data model
- [ ] I have one real end-to-end ingestion flow
- [ ] I have a CloudFormation baseline
- [ ] I have core tests
- [ ] I have a clean backlog for the next sprint

---

# One-line focus for each day

- **Day 1:** Design the right system
- **Day 2:** Build the right skeleton
- **Day 3:** Make one path work
- **Day 4:** Make it credible and repeatable
