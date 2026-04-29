# 🗂️ Task Dependencies & Implementation Order

## Dependency Graph

```
PHASE 1 TASKS (Start Here!)
├── P1.1: Fix Dead Code (Normalizer)
│   └── Required by: P1.2, P2.2
├── P1.2: Add Analysis Field  ✓ (no dependencies)
├── P1.3: Centralize Patterns ← Highest Priority!
│   └── Required by: P2.1, P2.2
├── P1.4: Quality Gates        ✓ (depends on P1.3)
├── P1.5: Logging Framework    ✓ (no dependencies)
├── P1.6: Per-Page OCR Retry   ✓ (no dependencies)
└── P1.7: Robust Section Extract ✓ (no dependencies)

PHASE 2 TASKS (After P1 complete)
├── P2.1: Extractor Interface ← Depends on: P1.3
│   └── Required by: P2.3
├── P2.2: Report Type Scoring ← Depends on: P1.3
│   └── Required by: P2.4
├── P2.3: Error Recovery      ← Depends on: P2.1
├── P2.4: Separate Models     ← Depends on: P2.2, P1.2
├── P2.5: Config Management   ✓
├── P2.6: Unit Tests          ← Depends on: All of Phase 1
└── P2.7: Documentation       ← Depends on: All of Phase 1,2

PHASE 3 TASKS (After P2 complete)
├── P3.1: Metrics            ✓
├── P3.2: Distributed Tracing ✓
├── P3.3: Feature Flags       ✓
├── P3.4: Audit Trail         ✓
├── P3.5: Validation Engine   ✓
├── P3.6: Plugin System       ← Depends on: P2.4
└── P3.7: Benchmarking        ← Depends on: P3.1

PHASE 4 TASKS (After P3 complete)
├── P4.1: Database Storage    ✓
├── P4.2: API Endpoints       ← Depends on: P4.1
├── P4.3: Message Queue       ← Depends on: P4.2
├── P4.4: Docker/K8s          ← Depends on: P4.3
└── P4.5: Data Lake Export    ← Depends on: P4.1

PHASE 5 TASKS (After P4 complete)
├── P5.1: Alerting Rules      ← Depends on: P3.1
├── P5.2: CI/CD Pipeline      ← Depends on: P4.4
├── P5.3: Runbooks            ✓
├── P5.4: SLOs/SLIs           ← Depends on: P3.1
└── P5.5: Disaster Recovery   ← Depends on: P4.1
```

---

## Recommended Implementation Order (Day by Day)

### Week 1: Foundation (Phase 1)

**Day 1-2: Configuration & Patterns**
- [ ] P1.3: Centralize Regex Patterns to YAML ← START HERE
  - Unblock: P2.1, P2.2
  - Create: `config/extraction_patterns.yaml`
  - Impact: All future pattern changes don't require code edits

**Day 1 (Parallel): Quick Wins**
- [ ] P1.1: Fix Dead Code (Normalizer)
  - Quick: 2 hours
  - Impact: 10% accuracy improvement
- [ ] P1.5: Logging Framework
  - Quick: 3 hours
  - Impact: Observability for debugging
- [ ] P1.6: Per-Page OCR Retry
  - Quick: 2 hours
  - Impact: Better OCR quality

**Day 2-3: Core Improvements**
- [ ] P1.2: Add Analysis Field
  - Quick: 1 hour
  - Impact: Proper data structure
- [ ] P1.4: Quality Gates
  - Depends on: P1.3
  - Impact: Reliable success criteria
- [ ] P1.7: Robust Section Extract
  - Quick: 3 hours
  - Impact: Fewer false negatives

**Day 4: Testing & Validation**
- [ ] Run full test suite manually
- [ ] Benchmark accuracy before/after
- [ ] Update README with new fields/patterns

---

### Week 2: Architecture (Phase 2)

**Day 5-6: Pluggable Architecture**
- [ ] P2.1: Extractor Interface
  - Depends on: P1.3 ✓
  - Unblock: P2.3
  - Impact: Extensible design
- [ ] P2.5: Config Management
  - Quick: Create settings.py
  - Impact: Environment-based config

**Day 7-8: Detection & Models**
- [ ] P2.2: Report Type Scoring
  - Depends on: P1.3 ✓
  - Impact: Reliable type detection
- [ ] P2.4: Separate Models
  - Depends on: P2.2 ✓, P1.2 ✓
  - Impact: Clean separation of concerns

**Day 9-10: Error Handling**
- [ ] P2.3: Error Recovery & Retry
  - Depends on: P2.1 ✓
  - Impact: Higher success rate

**Day 11: Testing & Docs**
- [ ] P2.6: Unit Test Framework
  - Depends on: All Phase 1 ✓
  - Target: 70%+ coverage
- [ ] P2.7: Documentation
  - Update README, add ARCHITECTURE.md

---

### Week 3: Enterprise (Phase 3)

**Day 12-13: Observability**
- [ ] P3.1: Metrics
  - Quick: Prometheus setup
  - Impact: Health monitoring
- [ ] P3.2: Distributed Tracing
  - Quick: OpenTelemetry setup
  - Impact: Request flow visibility

**Day 14: Features**
- [ ] P3.3: Feature Flags
  - Quick: Lightweight implementation
  - Impact: Gradual rollouts
- [ ] P3.4: Audit Trail
  - Quick: Structured logging
  - Impact: Compliance

**Day 15-16: Extensibility**
- [ ] P3.5: Validation Rules Engine
  - Quick: YAML-based rules
  - Impact: Easy rule updates
- [ ] P3.6: Plugin System
  - Depends on: P2.4 ✓
  - Impact: New report types as plugins

**Day 17: Benchmarking**
- [ ] P3.7: Performance Benchmarks
  - Depends on: P3.1 ✓

---

### Week 4-5: Production (Phase 4)

**Day 18-19: Persistence**
- [ ] P4.1: Database Storage
  - PostgreSQL + SQLAlchemy
  - Impact: Persistent storage, versioning

**Day 20-21: API**
- [ ] P4.2: API Endpoints
  - Depends on: P4.1 ✓
  - FastAPI + OpenAPI
  - Impact: Programmatic access

**Day 22-23: Scaling**
- [ ] P4.3: Message Queue
  - Depends on: P4.2 ✓
  - RabbitMQ/Kafka
  - Impact: Distributed processing
- [ ] P4.4: Docker/K8s
  - Depends on: P4.3 ✓
  - Impact: Cloud deployment

**Day 24-25: Analytics**
- [ ] P4.5: Data Lake Export
  - Depends on: P4.1 ✓
  - Impact: Data warehouse integration

---

### Week 6: Operations (Phase 5)

**Day 26: Monitoring**
- [ ] P5.1: Alerting Rules
  - Depends on: P3.1 ✓
  - Impact: Proactive alerting
- [ ] P5.4: SLOs/SLIs
  - Depends on: P3.1 ✓
  - Impact: Service expectations

**Day 27-28: Deployment**
- [ ] P5.2: CI/CD Pipeline
  - Depends on: P4.4 ✓
  - GitHub Actions
  - Impact: Automated deployments

**Day 29: Documentation & Playbooks**
- [ ] P5.3: Runbooks
  - Impact: Incident response
- [ ] P5.5: Disaster Recovery
  - Depends on: P4.1 ✓
  - Impact: Business continuity

---

## Critical Path Analysis

**Longest Dependency Chain** (22 days):
```
P1.3 (Patterns)
  ↓
P2.1 (Extractor Interface)
  ↓
P2.3 (Error Recovery)
  ↓ (parallel: P2.2, P2.4)
P2.6 (Testing)
  ↓ (parallel: Phase 3)
P3.1 (Metrics)
  ↓
P4.1 (Database)
  ↓
P4.5 (Data Lake)
  ↓
P5.1 (Alerting)
  + Additional: P5.2, P5.3, P5.5
```

**Critical Decisions** (can't be parallelized):
1. Centralize patterns (P1.3) → Unblock P2.1, P2.2
2. Build extractor interface (P2.1) → Unblock P2.3
3. Set up database (P4.1) → Unblock P4.2, P4.3
4. Create API (P4.2) → Unblock P4.3

---

## Parallelization Opportunities

**Can run in parallel** (independent tasks):

**Phase 1**:
- P1.1 (Normalizer) ∥ P1.5 (Logging) ∥ P1.6 (OCR Retry)
- P1.2 (Analysis Field) ∥ P1.7 (Section Extract)

**Phase 2**:
- P2.5 (Config) ∥ P2.6 (Tests) - after Phase 1 ✓
- P2.3 (Error Recovery) ∥ P2.7 (Docs) - after their deps ✓

**Phase 3**:
- P3.1 ∥ P3.2 ∥ P3.3 ∥ P3.4 ∥ P3.5 (all independent)

**Phase 4**:
- P4.1 (DB) can start immediately (independent)
- P4.2 ∥ P4.3 (both need P4.1)
- P4.5 can start with P4.1

---

## Effort Estimation (with Parallelization)

**Sequential** (pure waterfall): 35 days

**Optimized** (with parallelization):
- Phase 1: 3 days (many parallel tasks)
- Phase 2: 5 days (some parallel tasks)
- Phase 3: 4 days (fully parallel)
- Phase 4: 5 days (some dependencies)
- Phase 5: 4 days (mostly parallel)

**Total**: ~18-20 days (4 weeks) with optimal parallelization

**With code review/testing**: 25-30 days (5-6 weeks)

---

## Risk Mitigation

**High Risk** (must get right first time):
- P1.3: Pattern centralization (breaks everything if wrong)
  - Mitigation: Create comprehensive unit tests
- P2.1: Extractor interface (affects all future code)
  - Mitigation: Design doc + review before implementation
- P4.1: Database schema (hard to migrate later)
  - Mitigation: Version control migrations, test restore

**Medium Risk** (can iterate):
- P2.6: Test coverage (can add tests gradually)
- P3.1-3.7: Enterprise features (can add incrementally)
- P4.2-4.5: API/deployment (can refactor later)

**Low Risk** (easy to fix):
- P1.1, P1.2: Dead code, field additions
- P1.5: Logging (can reconfigure)
- P5.1-5.5: Ops features (can improve over time)

---

## Success Metrics by Phase

**Phase 1 Success**:
- [ ] Normalizer actually called
- [ ] All patterns in YAML
- [ ] Quality gates enforced
- [ ] Structured logging in place
- [ ] No increase in extraction time
- [ ] No regression in accuracy

**Phase 2 Success**:
- [ ] New extractor can be added without touching old code
- [ ] Report type detection scored and documented
- [ ] Fallback chain works (text → OCR → error)
- [ ] All models properly separated
- [ ] 70%+ test coverage
- [ ] All configuration externalized

**Phase 3 Success**:
- [ ] Prometheus metrics exported
- [ ] Tracing shows full request path
- [ ] Feature flags work for gradual rollout
- [ ] Audit trail captures all changes
- [ ] Validation rules easily updatable
- [ ] Performance baseline established

**Phase 4 Success**:
- [ ] Reports persisted with versioning
- [ ] REST API fully functional
- [ ] Message queue processes 100+ jobs/minute
- [ ] Kubernetes deployments working
- [ ] Data exported to data lake daily

**Phase 5 Success**:
- [ ] Alerts firing correctly
- [ ] Deployments automated
- [ ] Incident runbooks tested
- [ ] SLO attainment tracked
- [ ] Backup/restore tested monthly

---

## Rollback Strategy

If something fails catastrophically:

**Phase 1**: 
- Rollback: Revert files to original, restart task
- Risk: Low (isolated changes)

**Phase 2**:
- Rollback: Keep old extractor classes alongside new ones
- Risk: Medium (affects core logic)
- Strategy: Feature flag to use old/new

**Phase 4+**:
- Rollback: Database migrations (backward-compatible), API versions
- Risk: High if data lost
- Strategy: Always test migrations with backups

---

## Weekly Sync Agenda Template

```markdown
## Week [N] Sync

**Completed**:
- [ ] Task X: ✅ Complete, met requirements
- [ ] Task Y: ✅ Complete, minor issues noted

**In Progress**:
- [ ] Task Z: ~60% complete, on track
- [ ] Task W: blocked by Task X (wait for unblock)

**Blockers**:
- [ ] Issue: [describe]
  - Mitigation: [plan]
  - ETA: [date]

**Next Week Goals**:
- [ ] Task A
- [ ] Task B
- [ ] Task C

**Metrics**:
- Code coverage: X%
- Test pass rate: Y%
- Extraction accuracy: Z%
```

---

## File Organization Hints

```
SDR_mapping/
├── config/                      ← P1.3, P1.4, P2.5
│   ├── extraction_patterns.yaml
│   ├── quality_gates.yaml
│   ├── report_formats.yaml
│   ├── settings.py
│   └── defaults.py
│
├── infrastructure/               ← P2.1, P2.2
│   ├── extractors/
│   │   ├── base_extractor.py
│   │   ├── pdf_text_extractor.py
│   │   └── pdf_ocr_extractor.py
│   └── detectors/
│       ├── format_registry.py
│       └── ...
│
├── domain/                       ← P2.4
│   ├── models.py
│   ├── khoj_osint_report.py
│   └── scaninfoga_report.py
│
├── utils/                        ← P1.5, P2.3
│   ├── logging.py
│   ├── retry.py
│   └── exceptions.py
│
├── storage/                      ← P4.1, P4.5
│   ├── models.py
│   ├── repository.py
│   └── data_lake.py
│
├── api/                          ← P4.2
│   ├── app.py
│   └── routes/
│
├── queue/                        ← P4.3
│   ├── producer.py
│   └── consumer.py
│
├── monitoring/                   ← P3.1, P5.1
│   ├── metrics.py
│   └── alerts.yaml
│
├── tests/                        ← P2.6
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
└── docs/                         ← P2.7
    ├── ARCHITECTURE.md
    ├── EXTRACTION_PATTERNS.md
    └── ...
```

---

**Next Step**: Start with **P1.3 (Centralize Patterns)** - it unblocks the most other tasks!
