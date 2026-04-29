# 🎯 SDR_mapping Production Readiness Checklist

**Status**: 🔴 **BETA** (0% → 100% Complete)  
**Last Updated**: April 24, 2026  
**Owner**: Development Team

---

## 📋 QUICK REFERENCE

| Phase | Priority | Effort | Impact | Status |
|-------|----------|--------|--------|--------|
| **Phase 1: Quick Wins** | 🔴 Critical | 2-3 days | HIGH | ⏳ TODO |
| **Phase 2: Core Refactoring** | 🔴 Critical | 5-7 days | HIGH | ⏳ TODO |
| **Phase 3: Enterprise Features** | 🟡 High | 7-10 days | MEDIUM | ⏳ TODO |
| **Phase 4: Production Deployment** | 🟡 High | 5-7 days | MEDIUM | ⏳ TODO |
| **Phase 5: Monitoring & Ops** | 🟡 Medium | 3-5 days | MEDIUM | ⏳ TODO |

**Estimated Total**: 25-35 days (6-8 weeks with testing & review)

---

# 🚀 PHASE 1: QUICK WINS (2-3 days)

## ✅ P1.1: Fix Dead Code - Call Normalizer in Extractors

**Priority**: 🔴 CRITICAL  
**Effort**: 2 hours  
**Status**: ⏳ TODO

**Problem**: `normalizer.py` exists but is never called. Could improve accuracy by 10%+

**Tasks**:
- [ ] In `extractor/text_extractor.py`: Import and call `normalize_raw_text()` after PDF text extraction
- [ ] In `extractor/ocr_extractor.py`: Import and call `normalize_raw_text()` after OCR text extraction
- [ ] Add unit tests to verify normalization is applied
- [ ] Benchmark accuracy improvement

**Files to Change**:
```
extractor/text_extractor.py
extractor/ocr_extractor.py
```

**Code Pattern**:
```python
# After: full_text = pdfplumber.extract_text()
# Add: from extractor.normalizer import normalize_raw_text
full_text = normalize_raw_text(full_text)
```

---

## ✅ P1.2: Add Analysis Field to Schema

**Priority**: 🔴 CRITICAL  
**Effort**: 1 hour  
**Status**: ⏳ TODO

**Problem**: Analysis results computed but stored as JSON string in warnings (data loss)

**Tasks**:
- [ ] Add `analysis: Dict[str, Any]` field to `SDRReport` model in `models/schema.py`
- [ ] Update `pipeline.py` to store analysis in proper field instead of warnings
- [ ] Remove analysis from warnings string
- [ ] Update README with analysis field documentation

**Files to Change**:
```
models/schema.py
pipeline.py
```

**Code Pattern**:
```python
# In models/schema.py
class SDRReport(BaseModel):
    # ... existing fields ...
    analysis: Optional[Dict[str, Any]] = None  # ← Add this
    
# In pipeline.py
analysis = analyze_sdr_patterns(report)
report.analysis = analysis  # ← Instead of: warnings.append(...)
```

---

## ✅ P1.3: Centralize Regex Patterns to YAML

**Priority**: 🔴 CRITICAL  
**Effort**: 1 day  
**Status**: ⏳ TODO

**Problem**: 20+ regex patterns hardcoded across files; unmaintainable and fragile

**Tasks**:
- [ ] Create `config/extraction_patterns.yaml` with all regex patterns
- [ ] Create pattern loader class `config/pattern_loader.py`
- [ ] Update `extractor/text_extractor.py` to use pattern loader
- [ ] Update `extractor/detector.py` to use pattern loader
- [ ] Add pattern versioning (version: "1.0", author, date)
- [ ] Create `config/patterns_v1.yaml` with current patterns
- [ ] Document how to add/update patterns

**Files to Create**:
```
config/__init__.py
config/pattern_loader.py
config/extraction_patterns.yaml
config/patterns_v1.yaml
```

**Files to Change**:
```
extractor/text_extractor.py
extractor/detector.py
```

**YAML Structure Example**:
```yaml
version: "1.0"
author: "Initial Team"
created: "2026-04-24"
patterns:
  khoj_osint:
    phone:
      regex: '\+?91?[\s\-]?(\d{10})'
      flags: "IGNORECASE"
      confidence: 0.95
    operator:
      regex: 'operator\s*[:\-]?\s*(.+)'
      flags: "IGNORECASE"
      confidence: 0.85
    name:
      regex: '(?:Name|Full Name|Customer Name)\s*[:\-]?\s*([A-Za-z\s]+)'
      flags: "IGNORECASE"
      confidence: 0.80
```

---

## ✅ P1.4: Implement Quality Gates

**Priority**: 🟡 HIGH  
**Effort**: 4 hours  
**Status**: ⏳ TODO

**Problem**: Success criteria undefined; "0 warnings" ≠ good extraction

**Tasks**:
- [ ] Create `config/quality_gates.yaml` with validation rules
- [ ] Create `quality/quality_gate.py` with QualityGate class
- [ ] Implement `QualityGate.validate()` method
- [ ] Update `analyzer/sdr_analyzer.py` to use quality gates
- [ ] Update `pipeline.py` to apply quality gates before marking successful
- [ ] Document quality thresholds

**Files to Create**:
```
quality/__init__.py
quality/quality_gate.py
config/quality_gates.yaml
```

**Files to Change**:
```
analyzer/sdr_analyzer.py
pipeline.py
```

**Quality Gates**:
- `phone_number`: required=True, format valid, min_confidence=0.90
- `operator`: required=False, min_confidence=0.80
- `aliases`: required=False, min_count=1
- `completeness`: required=True, min_score=0.70

---

## ✅ P1.5: Add Proper Logging Framework

**Priority**: 🟡 HIGH  
**Effort**: 3 hours  
**Status**: ⏳ TODO

**Problem**: Only print statements; no structured logging

**Tasks**:
- [ ] Create `utils/logging.py` with logging configuration
- [ ] Replace all `print()` calls with `logger.info/warning/error`
- [ ] Add context to log messages (pdf_path, phone_number, etc.)
- [ ] Create log file output to `logs/` directory
- [ ] Add log level configuration via environment variable
- [ ] Document logging setup

**Files to Create**:
```
utils/__init__.py
utils/logging.py
logs/.gitkeep
```

**Files to Change**:
```
main.py
pipeline.py
extractor/detector.py
extractor/text_extractor.py
extractor/ocr_extractor.py
analyzer/sdr_analyzer.py
```

**Logging Pattern**:
```python
import logging
logger = logging.getLogger("sdr_mapper")

# Instead of: print(f"[text] Processing {pdf_path}")
logger.info("pdf_extraction_started", extra={"pdf_path": pdf_path, "method": "text"})

# Instead of: print(f"[error] Failed: {e}")
logger.error("pdf_extraction_failed", exc_info=True, extra={"pdf_path": pdf_path})
```

---

## ✅ P1.6: Fix Retry Logic (Per-Page OCR)

**Priority**: 🟡 MEDIUM  
**Effort**: 2 hours  
**Status**: ⏳ TODO

**Problem**: Retries entire document at higher DPI instead of per-page

**Tasks**:
- [ ] Refactor `ocr_extractor.py` to track per-page confidence separately
- [ ] Implement per-page retry logic (only reprocess low-confidence pages)
- [ ] Add configurable DPI levels (200, 300, 400)
- [ ] Add max retry attempts limit
- [ ] Test with various PDF quality levels

**Files to Change**:
```
extractor/ocr_extractor.py
config/defaults.py (add OCR settings)
```

**Logic**:
```python
# Old: if avg_conf < 0.60 → retry ALL pages at 300 DPI
# New: for each page: if page_conf < 0.60 → retry ONLY that page at 300 DPI
```

---

## ✅ P1.7: Fix Section Extraction Robustness

**Priority**: 🟡 HIGH  
**Effort**: 3 hours  
**Status**: ⏳ TODO

**Problem**: Section extraction fragile; fails if headers slightly different

**Tasks**:
- [ ] Refactor `_extract_section()` to be more robust
- [ ] Add fuzzy matching for section headers (vs exact regex)
- [ ] Add fallback behavior when start pattern not found
- [ ] Add early termination if end pattern missing (don't extract to EOF)
- [ ] Add tests for edge cases

**Files to Change**:
```
extractor/text_extractor.py
```

**Improvements**:
```python
# Old: exact regex match only
# New: fuzzy match + fallback patterns

def _extract_section_robust(text, start_pattern, end_patterns, fallback_end_char=None):
    # 1. Try exact regex
    # 2. Try fuzzy match
    # 3. If fail, return None (don't extract to EOF)
    # 4. Add timeout (don't extract > 1000 chars)
```

---

**Phase 1 Summary**:
- ✅ Remove dead code debt
- ✅ Fix data loss issues  
- ✅ Improve maintainability (centralize patterns)
- ✅ Improve reliability (quality gates, logging)
- ✅ Improve robustness (retry logic, section extraction)

**Success Criteria**:
- [ ] Normalizer called in all extraction paths
- [ ] Analysis field properly structured
- [ ] All patterns in YAML config
- [ ] Quality gates enforced
- [ ] Structured logging implemented
- [ ] Per-page OCR retry working
- [ ] Section extraction handles edge cases

---

# 🔧 PHASE 2: CORE REFACTORING (5-7 days)

## ✅ P2.1: Create Extractor Plugin Interface

**Priority**: 🔴 CRITICAL  
**Effort**: 1 day  
**Status**: ⏳ TODO

**Problem**: Tight coupling between PDF type detection and extraction

**Tasks**:
- [ ] Create `infrastructure/extractors/base_extractor.py` with abstract base class
- [ ] Create `infrastructure/extractors/pdf_text_extractor.py` (refactored from text_extractor.py)
- [ ] Create `infrastructure/extractors/pdf_ocr_extractor.py` (refactored from ocr_extractor.py)
- [ ] Create `infrastructure/extractors/__init__.py` with extractor registry
- [ ] Update `pipeline.py` to use extractor chain instead of if/else
- [ ] Add extensibility for new extractors (HTML, JSON, CSV in future)

**Files to Create**:
```
infrastructure/__init__.py
infrastructure/extractors/__init__.py
infrastructure/extractors/base_extractor.py
infrastructure/extractors/pdf_text_extractor.py
infrastructure/extractors/pdf_ocr_extractor.py
```

**Files to Change**:
```
pipeline.py
main.py
```

**Architecture**:
```python
# base_extractor.py
from abc import ABC, abstractmethod

class Extractor(ABC):
    @abstractmethod
    def can_process(self, pdf_path: str) -> bool:
        """Check if this extractor can handle the file"""
        pass
    
    @abstractmethod
    def extract(self, pdf_path: str) -> SDRReport:
        """Extract SDR report"""
        pass

# Registry
EXTRACTORS = [
    PDFTextExtractor(),
    PDFOCRExtractor(),
]

# Usage in pipeline.py
for extractor in EXTRACTORS:
    if extractor.can_process(pdf_path):
        report = extractor.extract(pdf_path)
        break
else:
    raise UnsupportedFormatError(f"No extractor for {pdf_path}")
```

---

## ✅ P2.2: Formalize Report Type Detection with Scoring

**Priority**: 🟡 HIGH  
**Effort**: 1 day  
**Status**: ⏳ TODO

**Problem**: Report type detection order-dependent; no scoring mechanism

**Tasks**:
- [ ] Create `config/report_formats.yaml` with format fingerprints
- [ ] Create `infrastructure/detectors/format_registry.py` with scoring logic
- [ ] Refactor `detector.py` to use registry instead of hardcoded checks
- [ ] Implement weighted scoring (fingerprints with weights)
- [ ] Add min_score threshold
- [ ] Add confidence to returned report type
- [ ] Document how to add new report formats

**Files to Create**:
```
infrastructure/detectors/__init__.py
infrastructure/detectors/format_registry.py
config/report_formats.yaml
```

**Files to Change**:
```
extractor/detector.py
models/schema.py (add report_type_confidence)
```

**YAML Structure**:
```yaml
formats:
  khoj_osint:
    fingerprints:
      - keyword: "OSINT Report"
        weight: 0.8
      - keyword: "Operator Details"
        weight: 0.7
      - keyword: "UPI/VPA Accounts"
        weight: 0.6
    min_score: 1.0
    
  scaninfoga:
    fingerprints:
      - keyword: "Scaninfoga"
        weight: 1.0
      - keyword: "Security Score"
        weight: 0.6
    min_score: 0.6
```

---

## ✅ P2.3: Implement Error Recovery & Retry

**Priority**: 🟡 HIGH  
**Effort**: 1 day  
**Status**: ⏳ TODO

**Problem**: Single failure = total loss; no fallback strategy

**Tasks**:
- [ ] Create `utils/exceptions.py` with custom exception hierarchy
- [ ] Create `utils/retry.py` with retry decorator
- [ ] Implement fallback extractor chain (if text fails, try OCR)
- [ ] Add partial recovery (extract some fields before crash)
- [ ] Add retry with exponential backoff for transient errors
- [ ] Update pipeline to use error recovery

**Files to Create**:
```
utils/exceptions.py
utils/retry.py
```

**Files to Change**:
```
pipeline.py
extractor/text_extractor.py
extractor/ocr_extractor.py
```

**Exception Hierarchy**:
```python
class SDRProcessingError(Exception):
    def __init__(self, stage, pdf_path, cause, recoverable=False):
        self.stage = stage  # "detection", "extraction", "validation"
        self.pdf_path = pdf_path
        self.cause = cause
        self.recoverable = recoverable

class DetectionError(SDRProcessingError):
    def __init__(self, pdf_path, cause):
        super().__init__("detection", pdf_path, cause, recoverable=False)

class ExtractionError(SDRProcessingError):
    def __init__(self, pdf_path, cause):
        super().__init__("extraction", pdf_path, cause, recoverable=True)
```

**Retry Logic**:
```python
@retry(max_attempts=3, backoff=exponential(1, 2))
def extract_with_fallback(pdf_path):
    try:
        return PDFTextExtractor().extract(pdf_path)
    except ExtractionError as e:
        logger.warning(f"Text extraction failed, trying OCR", extra={"error": str(e)})
        return PDFOCRExtractor().extract(pdf_path)
```

---

## ✅ P2.4: Separate Models by Report Type

**Priority**: 🟡 MEDIUM  
**Effort**: 1 day  
**Status**: ⏳ TODO

**Problem**: Mixing khoj + scaninfoga fields in single SDRReport (violates SRP)

**Tasks**:
- [ ] Create `domain/khoj_osint_report.py` with KhojOSINTReport model
- [ ] Create `domain/scaninfoga_report.py` with ScaninfogaReport model
- [ ] Create `domain/sdr_report_factory.py` to create correct type
- [ ] Keep SDRReport as base/union type
- [ ] Update extractors to return specific types
- [ ] Update analyzer to handle both types
- [ ] Add type checking in validation

**Files to Create**:
```
domain/__init__.py
domain/khoj_osint_report.py
domain/scaninfoga_report.py
domain/sdr_report_factory.py
```

**Files to Change**:
```
models/schema.py (keep as base + union)
extractor/text_extractor.py (return typed report)
extractor/ocr_extractor.py (return typed report)
analyzer/sdr_analyzer.py (handle both types)
```

**Architecture**:
```python
# Base model
class SDRReport(BaseModel):
    source_file: str
    report_type: str
    extraction_method: str
    warnings: List[str] = []

# Type-specific models
class KhojOSINTReport(SDRReport):
    phone_number: str
    operator_details: OperatorDetails
    aliases: List[str]
    
class ScaninfogaReport(SDRReport):
    phone_number: str
    personal_details: PersonalDetails
    security_scores: SecurityScores

# Union type
SDRReportType = Union[KhojOSINTReport, ScaninfogaReport]
```

---

## ✅ P2.5: Create Configuration Management

**Priority**: 🟡 HIGH  
**Effort**: 1 day  
**Status**: ⏳ TODO

**Problem**: Hardcoded settings; no config file or environment variable support

**Tasks**:
- [ ] Create `config/settings.py` with Settings class (Pydantic)
- [ ] Create `.env.example` with environment variables
- [ ] Support `.env` file loading
- [ ] Support environment variables override
- [ ] Create `config/defaults.py` with default values
- [ ] Make all CLI args configurable via settings
- [ ] Document configuration options

**Files to Create**:
```
config/settings.py
.env.example
```

**Files to Change**:
```
main.py
pipeline.py
extractor/ocr_extractor.py
```

**Settings Structure**:
```python
# config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Extraction settings
    ocr_dpi: int = 200
    ocr_workers: int = 4
    max_workers: int = 4
    force_ocr: bool = False
    
    # Quality settings
    min_quality_score: float = 0.70
    min_phone_confidence: float = 0.90
    
    # Retry settings
    max_retry_attempts: int = 3
    retry_backoff_factor: float = 2.0
    
    # Storage settings
    output_dir: str = "output"
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Usage:
settings = Settings()
ocr_workers = settings.ocr_workers
```

**`.env.example`**:
```
OCR_DPI=200
OCR_WORKERS=4
MAX_WORKERS=4
MIN_QUALITY_SCORE=0.70
LOG_LEVEL=INFO
OUTPUT_DIR=output
```

---

## ✅ P2.6: Implement Unit Test Framework

**Priority**: 🟡 HIGH  
**Effort**: 1.5 days  
**Status**: ⏳ TODO

**Problem**: No automated tests; only manual testing

**Tasks**:
- [ ] Create `tests/` directory structure
- [ ] Create `tests/unit/test_extractors.py`
- [ ] Create `tests/unit/test_detectors.py`
- [ ] Create `tests/unit/test_validators.py`
- [ ] Create `tests/integration/test_khoj_pipeline.py`
- [ ] Create `tests/integration/test_scaninfoga_pipeline.py`
- [ ] Create test fixtures (sample PDFs)
- [ ] Add pytest configuration
- [ ] Set up coverage reporting
- [ ] Add GitHub Actions CI/CD

**Files to Create**:
```
tests/__init__.py
tests/conftest.py
tests/unit/__init__.py
tests/unit/test_detectors.py
tests/unit/test_extractors.py
tests/unit/test_validators.py
tests/unit/test_analyzers.py
tests/integration/__init__.py
tests/integration/test_khoj_pipeline.py
tests/integration/test_scaninfoga_pipeline.py
tests/fixtures/__init__.py
tests/fixtures/sample_khoj_report.pdf
tests/fixtures/sample_scaninfoga_report.pdf
tests/fixtures/expected_outputs/
pytest.ini
.github/workflows/ci.yml
```

**Test Example**:
```python
# tests/unit/test_detectors.py
def test_detect_khoj_osint_report():
    text = "OSINT Report - 9560978030\nOperator: Airtel\nCircle: Delhi"
    report_type, confidence = detect_report_type(text)
    
    assert report_type == "khoj_osint"
    assert confidence >= 0.80

def test_detect_scaninfoga_report():
    text = "Comprehensive Intelligence Report\nSecurity Score: 85\nCIBIL Score: 750"
    report_type, confidence = detect_report_type(text)
    
    assert report_type == "scaninfoga"
    assert confidence >= 0.60

# tests/integration/test_khoj_pipeline.py
@pytest.mark.integration
def test_khoj_full_extraction():
    pdf_path = "tests/fixtures/sample_khoj_report.pdf"
    report = process_single(pdf_path)
    
    assert report.report_type == "khoj_osint"
    assert report.phone_number == "9560978030"
    assert len(report.aliases) > 0
    assert report.quality_score > 0.80
```

---

## ✅ P2.7: Update README & Documentation

**Priority**: 🟡 MEDIUM  
**Effort**: 1 day  
**Status**: ⏳ TODO

**Problem**: Documentation exists but incomplete for production features

**Tasks**:
- [ ] Update `README.md` with new architecture
- [ ] Create `docs/ARCHITECTURE.md` (detailed system design)
- [ ] Create `docs/CONFIGURATION.md` (settings & environment variables)
- [ ] Create `docs/EXTRACTION_PATTERNS.md` (how to add patterns)
- [ ] Create `docs/ADDING_FORMATS.md` (how to add new report types)
- [ ] Create `docs/API.md` (programmatic usage)
- [ ] Create `docs/TROUBLESHOOTING.md` (common issues)
- [ ] Add deployment guide

**Files to Create**:
```
docs/ARCHITECTURE.md
docs/CONFIGURATION.md
docs/EXTRACTION_PATTERNS.md
docs/ADDING_FORMATS.md
docs/API.md
docs/TROUBLESHOOTING.md
docs/DEPLOYMENT.md
```

---

**Phase 2 Summary**:
- ✅ Pluggable architecture (add extractors/formats easily)
- ✅ Smart report type detection (scored, not order-dependent)
- ✅ Error recovery (fallback chains, retry logic)
- ✅ Proper models (no mixing concerns)
- ✅ Configuration management (environment-based)
- ✅ Test coverage (automated testing)
- ✅ Documentation (complete, clear, helpful)

**Success Criteria**:
- [ ] New extractor can be added without touching existing code
- [ ] Report type detection documented, scored, testable
- [ ] Fallback chain works (text → OCR → error)
- [ ] Models properly separated by report type
- [ ] All config in settings, not hardcoded
- [ ] 70%+ unit test coverage
- [ ] All major use cases documented

---

# 📊 PHASE 3: ENTERPRISE FEATURES (7-10 days)

## ✅ P3.1: Add Metrics & Monitoring

**Priority**: 🟡 HIGH  
**Effort**: 2 days  
**Status**: ⏳ TODO

**Problem**: No metrics; can't monitor system health

**Tasks**:
- [ ] Add Prometheus metrics
- [ ] Track extraction duration
- [ ] Track extraction quality score
- [ ] Track extraction errors (by type, stage)
- [ ] Track batch processing throughput
- [ ] Expose metrics endpoint
- [ ] Create Grafana dashboard
- [ ] Set up alerting rules

**Files to Create**:
```
monitoring/__init__.py
monitoring/metrics.py
monitoring/dashboards.json
```

**Metrics to Track**:
```python
extraction_duration = Histogram(
    'sdr_extraction_duration_seconds',
    'Time to extract a report',
    buckets=[1, 2, 5, 10, 30, 60]
)

extraction_quality = Gauge(
    'sdr_extraction_quality_score',
    'Quality score of extracted data'
)

extraction_errors = Counter(
    'sdr_extraction_errors_total',
    'Total extraction errors',
    labelnames=['error_type', 'stage']
)

batch_throughput = Counter(
    'sdr_batch_processing_total',
    'Total PDFs processed in batch',
    labelnames=['status']
)
```

---

## ✅ P3.2: Implement Distributed Tracing

**Priority**: 🟡 MEDIUM  
**Effort**: 1.5 days  
**Status**: ⏳ TODO

**Problem**: Can't trace request flow through system

**Tasks**:
- [ ] Integrate OpenTelemetry
- [ ] Add trace spans to extraction pipeline
- [ ] Add trace spans to validation
- [ ] Add trace spans to analysis
- [ ] Set up Jaeger backend
- [ ] Create trace visualization

**Files to Create**:
```
tracing/__init__.py
tracing/tracer.py
tracing/config.py
```

**Trace Structure**:
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("extract_sdr_report") as span:
    span.set_attribute("pdf.path", pdf_path)
    span.set_attribute("pdf.size_mb", file_size)
    
    with tracer.start_as_current_span("detect_pdf_type"):
        pdf_type = detect_pdf_type(pdf_path)
        span.set_attribute("pdf.type", pdf_type)
    
    with tracer.start_as_current_span("extract_content"):
        report = extract_content(pdf_path, pdf_type)
        span.set_attribute("report.type", report.report_type)
    
    with tracer.start_as_current_span("validate_report"):
        validation = validate_quality(report)
        span.set_attribute("quality.score", validation.score)
    
    return report
```

---

## ✅ P3.3: Add Feature Flags

**Priority**: 🟡 MEDIUM  
**Effort**: 1 day  
**Status**: ⏳ TODO

**Problem**: Can't gradually roll out new features or A/B test

**Tasks**:
- [ ] Create `features/feature_flags.py` with flag system
- [ ] Support percentage-based rollout (5%, 25%, 100%)
- [ ] Support user-based targeting
- [ ] Create feature flag admin UI (basic)
- [ ] Document flag lifecycle
- [ ] Add metrics for flag usage

**Files to Create**:
```
features/__init__.py
features/feature_flags.py
features/flags.yaml
```

**Feature Flags Example**:
```yaml
flags:
  use_new_extraction_engine:
    enabled: true
    percentage: 5  # 5% of traffic
    description: "New extraction engine with better accuracy"
    rollout_plan:
      - date: 2026-04-25
        percentage: 5
      - date: 2026-05-01
        percentage: 25
      - date: 2026-05-08
        percentage: 100
    
  ocr_per_page_retry:
    enabled: true
    percentage: 100
    description: "OCR retry logic at page level"
```

**Usage**:
```python
if is_feature_enabled("use_new_extraction_engine"):
    report = NewExtractionEngine.extract(pdf_path)
else:
    report = extract_sdr_report(pdf_path)
```

---

## ✅ P3.4: Add Audit Trail & Data Lineage

**Priority**: 🟡 MEDIUM  
**Effort**: 1.5 days  
**Status**: ⏳ TODO

**Problem**: Can't track what changed, who did it, why

**Tasks**:
- [ ] Create `audit/__init__.py`
- [ ] Create audit logger for all extraction events
- [ ] Track extraction engine version
- [ ] Track pattern version used
- [ ] Track extraction duration
- [ ] Track quality score
- [ ] Store audit logs to file/database
- [ ] Create audit report queries

**Files to Create**:
```
audit/__init__.py
audit/audit_logger.py
audit/models.py
```

**Audit Log Structure**:
```python
@dataclass
class AuditEntry:
    timestamp: datetime
    pdf_path: str
    pdf_checksum: str
    pdf_size_bytes: int
    
    # Processing info
    extraction_engine_version: str
    extraction_patterns_version: str
    extractor_type: str  # "text" or "ocr"
    
    # Results
    report_type: str
    phone_number: str  # masked if PII
    quality_score: float
    extracted_fields_count: int
    missing_fields: List[str]
    
    # Metadata
    duration_seconds: float
    success: bool
    error_message: Optional[str]
    user_id: Optional[str]
    
    # Lineage
    patterns_used: List[str]
    normalization_applied: bool
```

---

## ✅ P3.5: Add Data Validation Rules Engine

**Priority**: 🟡 HIGH  
**Effort**: 1.5 days  
**Status**: ⏳ TODO

**Problem**: Validation logic hardcoded; can't easily add new rules

**Tasks**:
- [ ] Create `validation/rule_engine.py` with pluggable validation
- [ ] Create `validation/rules.py` with built-in rules
- [ ] Create `validation/rules.yaml` with rule definitions
- [ ] Support field-level validation
- [ ] Support cross-field validation
- [ ] Support severity levels (error, warning, info)
- [ ] Create rule registry

**Files to Create**:
```
validation/__init__.py
validation/rule_engine.py
validation/rules.py
validation/rules.yaml
```

**Rule Definition Example**:
```yaml
rules:
  phone_number_format:
    severity: error
    message: "Invalid phone number format"
    condition: "matches_regex(phone_number, '^\\d{10}$')"
    
  email_validity:
    severity: error
    message: "Email address invalid"
    condition: "all(email_addresses, is_valid_email)"
    
  minimum_fields_filled:
    severity: warning
    message: "Less than 70% of fields filled"
    condition: "data_completeness >= 0.70"
    
  upi_has_at_sign:
    severity: warning
    message: "UPI account format looks wrong"
    condition: "all(upi_accounts, '@' in upi_id)"
```

---

## ✅ P3.6: Add Report Type Extensibility

**Priority**: 🟡 MEDIUM  
**Effort**: 1 day  
**Status**: ⏳ TODO

**Problem**: Adding new report type requires code changes

**Tasks**:
- [ ] Create `domain/report_type_registry.py`
- [ ] Create `domain/report_type.py` base class
- [ ] Create `domain/khoj_osint_type.py` (register via decorator)
- [ ] Create `domain/scaninfoga_type.py` (register via decorator)
- [ ] Support plugins for new types
- [ ] Document how to add new report type

**Files to Create**:
```
domain/report_type_registry.py
domain/report_type.py
```

**Pattern**:
```python
# domain/report_type.py
class ReportType(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def get_schema(self) -> Type[BaseModel]:
        pass
    
    @abstractmethod
    def extract_fields(self, text: str) -> Dict:
        pass

# domain/khoj_osint_type.py
@register_report_type("khoj_osint")
class KhojOSINTType(ReportType):
    @property
    def name(self):
        return "khoj_osint"
    
    def get_schema(self):
        return KhojOSINTReport
    
    def extract_fields(self, text):
        return _extract_khoj_osint_fields(text)
```

---

## ✅ P3.7: Add Performance Benchmarking

**Priority**: 🟡 LOW  
**Effort**: 1 day  
**Status**: ⏳ TODO

**Problem**: Can't track performance degradation

**Tasks**:
- [ ] Create `benchmarks/benchmark_suite.py`
- [ ] Benchmark extraction time by report type
- [ ] Benchmark extraction time by PDF size
- [ ] Benchmark OCR at different DPI levels
- [ ] Benchmark validation time
- [ ] Create benchmark report generator
- [ ] Track performance over time (git history)

**Files to Create**:
```
benchmarks/__init__.py
benchmarks/benchmark_suite.py
benchmarks/results/
```

---

**Phase 3 Summary**:
- ✅ Visibility: Metrics, tracing, audit trails
- ✅ Gradual rollout: Feature flags
- ✅ Quality: Advanced validation rules
- ✅ Extensibility: Plugin-based report types
- ✅ Performance: Benchmarking infrastructure

---

# ☁️ PHASE 4: PRODUCTION DEPLOYMENT (5-7 days)

## ✅ P4.1: Database Storage

**Priority**: 🔴 CRITICAL  
**Effort**: 2 days  
**Status**: ⏳ TODO

**Problem**: Output only to JSON files; no persistence, versioning, or querying

**Tasks**:
- [ ] Design PostgreSQL schema for reports
- [ ] Create migration system (Alembic)
- [ ] Create ORM models (SQLAlchemy)
- [ ] Create `storage/report_repository.py`
- [ ] Implement save/get/list operations
- [ ] Add versioning (track report changes)
- [ ] Add indexing for common queries
- [ ] Create backup strategy

**Files to Create**:
```
storage/__init__.py
storage/models.py
storage/repository.py
migrations/
```

**Schema Example**:
```sql
CREATE TABLE reports (
    id UUID PRIMARY KEY,
    phone_number VARCHAR(20) NOT NULL,
    report_type VARCHAR(50) NOT NULL,
    extraction_method VARCHAR(20),
    source_file VARCHAR(255),
    data JSONB NOT NULL,
    quality_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    version INT DEFAULT 1,
    INDEX (phone_number),
    INDEX (report_type),
    INDEX (created_at)
);

CREATE TABLE report_versions (
    id UUID PRIMARY KEY,
    report_id UUID REFERENCES reports(id),
    version INT,
    data JSONB,
    created_at TIMESTAMP,
    UNIQUE(report_id, version)
);
```

---

## ✅ P4.2: API Endpoint

**Priority**: 🟡 HIGH  
**Effort**: 2 days  
**Status**: ⏳ TODO

**Problem**: Only CLI interface; can't use programmatically

**Tasks**:
- [ ] Create FastAPI application
- [ ] Create `/api/v1/extract` endpoint (single PDF)
- [ ] Create `/api/v1/batch` endpoint (multiple PDFs)
- [ ] Create `/api/v1/reports/{id}` endpoint (get report)
- [ ] Create `/api/v1/reports` endpoint (list reports)
- [ ] Add authentication/authorization
- [ ] Add rate limiting
- [ ] Create OpenAPI documentation
- [ ] Add webhook support for async processing

**Files to Create**:
```
api/__init__.py
api/app.py
api/routes/__init__.py
api/routes/extraction.py
api/routes/reports.py
api/schemas.py
```

**Endpoints**:
```python
# POST /api/v1/extract
# Body: {"pdf_url": "s3://bucket/report.pdf"}
# Response: {"report_id": "uuid", "status": "processing"}

# GET /api/v1/reports/{id}
# Response: {"id": "uuid", "report_type": "khoj_osint", "data": {...}}

# POST /api/v1/batch
# Body: {"pdf_urls": [...], "webhook_url": "..."}
# Response: {"batch_id": "uuid", "count": 10}
```

---

## ✅ P4.3: Message Queue (RabbitMQ/Kafka)

**Priority**: 🟡 MEDIUM  
**Effort**: 1.5 days  
**Status**: ⏳ TODO

**Problem**: Batch processing blocks; not scalable to thousands of PDFs

**Tasks**:
- [ ] Set up message queue (RabbitMQ or Kafka)
- [ ] Create `queue/producer.py` to submit jobs
- [ ] Create `queue/consumer.py` to process jobs
- [ ] Implement job retry logic
- [ ] Implement dead letter queue for failed jobs
- [ ] Create job status tracking
- [ ] Add priority queue support
- [ ] Docker compose for local dev

**Files to Create**:
```
queue/__init__.py
queue/producer.py
queue/consumer.py
queue/models.py
docker-compose.dev.yml
```

**Job Model**:
```python
@dataclass
class ProcessingJob:
    id: str
    pdf_url: str
    priority: int = 1
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict] = None
    error: Optional[str] = None
    status: str = "pending"  # pending, processing, completed, failed
```

---

## ✅ P4.4: Docker & Kubernetes

**Priority**: 🟡 HIGH  
**Effort**: 1.5 days  
**Status**: ⏳ TODO

**Problem**: Can't deploy to production; local development only

**Tasks**:
- [ ] Create `Dockerfile` for SDR processor
- [ ] Create `docker-compose.yml` for local dev (API, queue, DB, cache)
- [ ] Create Kubernetes manifests
- [ ] Create deployment strategy (rolling updates)
- [ ] Add health checks
- [ ] Add resource limits
- [ ] Create Helm chart
- [ ] Add auto-scaling config

**Files to Create**:
```
Dockerfile
docker-compose.yml
k8s/deployment.yaml
k8s/service.yaml
k8s/configmap.yaml
k8s/secret.yaml
k8s/hpa.yaml
helm/Chart.yaml
helm/values.yaml
helm/templates/
```

**Dockerfile Example**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## ✅ P4.5: Data Lake Export

**Priority**: 🟡 MEDIUM  
**Effort**: 1 day  
**Status**: ⏳ TODO

**Problem**: Data only in local DB; can't use for analytics

**Tasks**:
- [ ] Create `storage/data_lake.py`
- [ ] Export reports to S3/GCS daily
- [ ] Export to Parquet format for analytics
- [ ] Create data catalog metadata
- [ ] Set up access controls (IAM)
- [ ] Document data schema

**Files to Create**:
```
storage/data_lake.py
storage/export.py
```

**Export Job**:
```python
def export_to_data_lake():
    """Daily export of reports to data lake"""
    
    # Get all reports from yesterday
    reports = db.get_reports(
        created_at__gte=datetime.now() - timedelta(days=1),
        created_at__lt=datetime.now()
    )
    
    # Convert to Parquet
    df = pd.DataFrame([r.to_dict() for r in reports])
    parquet_file = f"s3://data-lake/sdr_reports/{datetime.now().date()}.parquet"
    df.to_parquet(parquet_file)
    
    # Update data catalog
    update_data_catalog(parquet_file, schema=ReportSchema())
```

---

**Phase 4 Summary**:
- ✅ Persistent storage with versioning
- ✅ API for programmatic access
- ✅ Distributed processing at scale
- ✅ Container orchestration
- ✅ Analytics-ready data export

---

# 🔍 PHASE 5: MONITORING & OPERATIONS (3-5 days)

## ✅ P5.1: Alerting Rules

**Priority**: 🟡 MEDIUM  
**Effort**: 1 day  
**Status**: ⏳ TODO

**Problem**: Can't proactively detect issues

**Tasks**:
- [ ] Create alert: High extraction failure rate (>5%)
- [ ] Create alert: Low average quality score (<70%)
- [ ] Create alert: High latency (extraction >60s)
- [ ] Create alert: Queue backed up (>1000 jobs)
- [ ] Create alert: Database disk usage >80%
- [ ] Create alert: OCR confidence consistently low
- [ ] Set up Slack/PagerDuty integration
- [ ] Document alert runbooks

**Files to Create**:
```
monitoring/alerts.yaml
monitoring/runbooks/
```

**Alert Example**:
```yaml
alerts:
  - name: HighExtractionFailureRate
    condition: |
      rate(sdr_extraction_errors_total[5m]) / rate(sdr_extraction_total[5m]) > 0.05
    duration: 5m
    severity: critical
    message: "SDR extraction failure rate > 5% for past 5 minutes"
    
  - name: LowQualityScore
    condition: avg(sdr_extraction_quality_score) < 0.70
    duration: 10m
    severity: warning
    message: "Average extraction quality < 70%"
```

---

## ✅ P5.2: Deployment Pipeline

**Priority**: 🟡 MEDIUM  
**Effort**: 1.5 days  
**Status**: ⏳ TODO

**Problem**: Manual deployment; error-prone

**Tasks**:
- [ ] Create GitHub Actions CI pipeline
- [ ] Automate testing on PR
- [ ] Automate docker build
- [ ] Automate image push to registry
- [ ] Create staging deployment
- [ ] Create production deployment (manual approval)
- [ ] Add smoke tests
- [ ] Add rollback capability

**Files to Create**:
```
.github/workflows/ci.yml
.github/workflows/deploy.yml
.github/workflows/tests.yml
```

**CI Workflow**:
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: pytest --cov=. --cov-report=xml
      - run: python -m black --check .
      - run: python -m flake8 .

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: docker/build-push-action@v4
        with:
          push: true
          tags: gcr.io/${{ secrets.GCP_PROJECT }}/sdr-processor:${{ github.sha }}
```

---

## ✅ P5.3: Runbooks & Documentation

**Priority**: 🟡 MEDIUM  
**Effort**: 1 day  
**Status**: ⏳ TODO

**Problem**: No playbooks for common incidents

**Tasks**:
- [ ] Create runbook: High failure rate troubleshooting
- [ ] Create runbook: Low quality score debugging
- [ ] Create runbook: Database recovery
- [ ] Create runbook: Message queue backlog clearing
- [ ] Create runbook: Graceful degradation
- [ ] Create runbook: Rollback procedure
- [ ] Document escalation path

**Files to Create**:
```
monitoring/runbooks/high_failure_rate.md
monitoring/runbooks/low_quality_score.md
monitoring/runbooks/database_recovery.md
monitoring/runbooks/queue_backlog.md
INCIDENT_RESPONSE.md
```

**Runbook Template**:
```markdown
# High Extraction Failure Rate

## Alert Condition
Extraction failure rate > 5% for 5+ minutes

## Immediate Actions
1. Check if specific report type affected
   - Query: SELECT report_type, count(*) FROM failures WHERE created_at > now() - '5m' GROUP BY report_type
2. Check if specific error type
   - Query: SELECT error_type, count(*) FROM failures WHERE created_at > now() - '5m' GROUP BY error_type
3. Check OCR confidence (if OCR-related)
   - Query: SELECT avg(ocr_confidence) FROM extractions WHERE extraction_method='ocr' AND created_at > now() - '5m'

## Investigation
- [ ] Check pattern version (may have broken patterns)
- [ ] Check if new PDFs with unusual format
- [ ] Check resource usage (CPU/memory)
- [ ] Check message queue lag

## Resolution Options
1. Rollback to previous extractor version
2. Disable problematic pattern
3. Scale up worker pool
4. Switch to alternative extraction method

## Post-Incident
- [ ] Root cause analysis
- [ ] Add regression tests
- [ ] Update patterns/detection
```

---

## ✅ P5.4: SLOs & SLIs

**Priority**: 🟡 MEDIUM  
**Effort**: 1 day  
**Status**: ⏳ TODO

**Problem**: No defined service expectations

**Tasks**:
- [ ] Define extraction availability SLO (99.5%)
- [ ] Define extraction latency SLI (p95 < 10s)
- [ ] Define quality SLI (avg quality > 80%)
- [ ] Define data consistency SLI
- [ ] Create SLI dashboard
- [ ] Track SLO attainment

**SLOs**:
```
Extraction Service SLOs:
- Availability: 99.5% (22.3 hours downtime/month allowed)
- Extraction Success Rate: 98% (successful extractions / total attempts)
- Quality Score: Avg >= 80% (quality_score field)
- Latency p95: < 10 seconds (extraction_duration_seconds)
- Latency p99: < 30 seconds
```

---

## ✅ P5.5: Disaster Recovery

**Priority**: 🟡 HIGH  
**Effort**: 1 day  
**Status**: ⏳ TODO

**Problem**: No recovery strategy for data loss

**Tasks**:
- [ ] Set up daily database backups
- [ ] Set up backup to S3
- [ ] Test restore procedure (weekly)
- [ ] Document RTO/RPO
- [ ] Create failover procedure
- [ ] Document disaster recovery plan

**Files to Create**:
```
ops/backup.sh
ops/restore.sh
ops/disaster_recovery.md
```

**RTO/RPO**:
- RTO (Recovery Time Objective): 1 hour
- RPO (Recovery Point Objective): 1 hour (daily backups)

---

**Phase 5 Summary**:
- ✅ Proactive alerting
- ✅ Automated deployments
- ✅ Clear incident playbooks
- ✅ Defined SLOs
- ✅ Disaster recovery plan

---

# 📈 PROGRESS TRACKING

## Overall Progress
```
Phase 1: ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 0%
Phase 2: ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 0%
Phase 3: ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 0%
Phase 4: ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 0%
Phase 5: ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 0%
────────────────────────────────────────────────────
Total:  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 0%
```

## Completion Target
- **Start Date**: April 24, 2026
- **Target Date**: June 2, 2026 (6 weeks)
- **Phase 1 Target**: April 26, 2026 (2 days)
- **Phase 2 Target**: May 3, 2026 (9 days)
- **Phase 3 Target**: May 13, 2026 (10 days)
- **Phase 4 Target**: May 20, 2026 (7 days)
- **Phase 5 Target**: May 27, 2026 (7 days)

---

# ✅ QUALITY GATES

Before marking complete:

**Code Quality**:
- [ ] All Python code passes black formatting
- [ ] All code passes flake8 linting
- [ ] Cyclomatic complexity < 10 for all functions
- [ ] Test coverage >= 80%
- [ ] Zero security vulnerabilities (bandit scan)

**Documentation**:
- [ ] All public functions have docstrings
- [ ] README is up-to-date
- [ ] Architecture document exists
- [ ] API documentation complete (OpenAPI)
- [ ] Runbooks written for key scenarios

**Testing**:
- [ ] Unit tests pass (pytest)
- [ ] Integration tests pass
- [ ] Performance benchmarks baseline established
- [ ] Manual testing on sample PDFs

**Production Readiness**:
- [ ] All hardcoded values in config
- [ ] All secrets in environment variables
- [ ] Logging configured and tested
- [ ] Monitoring setup verified
- [ ] Backup/restore tested

**Performance**:
- [ ] Single extraction: < 10 seconds (text), < 30 seconds (OCR)
- [ ] Batch throughput: > 1000 PDFs/hour
- [ ] OCR accuracy: > 95% confidence average
- [ ] Memory usage: < 2GB per worker
- [ ] Database query response: < 100ms

---

# 🎓 LESSONS LEARNED TEMPLATE

After completing each phase, fill this out:

```markdown
## Phase [N] Retrospective

**What Went Well**:
- 

**What Could Be Better**:
- 

**What We Learned**:
- 

**Changes for Next Phase**:
- 

**Time Estimate vs Actual**:
- Estimated: X days
- Actual: Y days
- Variance: +/- Z%
```

---

# 📞 ESCALATION PATH

If blocked:
1. **Technical**: Post in #sdr-mapper-dev Slack channel
2. **Design**: Schedule sync with architects
3. **Deployment**: Contact DevOps team
4. **Data**: Contact data governance team

---

**Last Updated**: April 24, 2026 by Copilot
**Next Review**: After Phase 1 completion
