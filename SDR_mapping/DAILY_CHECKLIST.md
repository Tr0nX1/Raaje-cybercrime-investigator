# 📅 Quick Working Checklist (Print & Use)

> Print this and check off items as you complete them!

---

## 🔴 PHASE 1: QUICK WINS (Days 1-4)

### P1.1: Fix Dead Code - Normalizer ⏳ TODO
**File**: `extractor/text_extractor.py`, `extractor/ocr_extractor.py`  
**Effort**: 2 hours

- [ ] Add import: `from extractor.normalizer import normalize_raw_text`
- [ ] In `extract_text_pdf()`: after pdfplumber extract, add `full_text = normalize_raw_text(full_text)`
- [ ] In `extract_ocr_pdf()`: after OCR readtext, add `full_text = normalize_raw_text(full_text)`
- [ ] Test extraction accuracy before/after
- [ ] Commit with message: `feat: call normalizer in extraction paths`

**PR Check**:
- [ ] Tests pass
- [ ] Accuracy improved (benchmark)

---

### P1.2: Add Analysis Field ⏳ TODO
**File**: `models/schema.py`, `pipeline.py`  
**Effort**: 1 hour

- [ ] Open `models/schema.py`
- [ ] Find `class SDRReport(BaseModel):`
- [ ] Add field: `analysis: Optional[Dict[str, Any]] = None`
- [ ] In `pipeline.py` line ~45, change:
  - FROM: `report.warnings.append(f"Analysis: {json.dumps(analysis, indent=2)}")`
  - TO: `report.analysis = analysis`
- [ ] Test: Extract PDF, verify `report.analysis` is dict (not string)
- [ ] Commit: `feat: add analysis field to SDRReport`

**PR Check**:
- [ ] Analysis is structured (Dict), not string
- [ ] to_dict() serializes correctly
- [ ] README updated

---

### P1.3: Centralize Patterns to YAML 🚀 CRITICAL ⏳ TODO
**Files**: Create `config/extraction_patterns.yaml`, `config/pattern_loader.py`  
**Effort**: 1 day

**Create Files**:
- [ ] Create `config/__init__.py` (empty)
- [ ] Create `config/extraction_patterns.yaml` (see template below)
- [ ] Create `config/pattern_loader.py` (see template below)

**extraction_patterns.yaml Template**:
```yaml
version: "1.0"
author: "Initial Migration"
created: "2026-04-24"

patterns:
  detection:
    khoj_osint_indicators:
      - "OSINT Report"
      - "Operator Details"
      - "UPI/VPA Accounts"
    scaninfoga_indicators:
      - "Scaninfoga"
      - "Security Score"
      - "CIBIL Score"
  
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
    # ... (add all other patterns from text_extractor.py)
  
  scaninfoga:
    phone:
      regex: 'Investigating Number:\s*\+?(\d+)'
      flags: "IGNORECASE"
      confidence: 0.95
    # ... (add all other patterns from text_extractor.py)
```

**pattern_loader.py Template**:
```python
import yaml
from pathlib import Path
from typing import Dict, Any

class PatternLoader:
    def __init__(self, config_file="config/extraction_patterns.yaml"):
        self.config_file = Path(config_file)
        self.patterns = self._load_patterns()
    
    def _load_patterns(self) -> Dict[str, Any]:
        with open(self.config_file) as f:
            return yaml.safe_load(f)
    
    def get_pattern(self, category: str, name: str) -> str:
        """Get pattern regex by category and name"""
        return self.patterns["patterns"][category][name]["regex"]
    
    def get_confidence(self, category: str, name: str) -> float:
        """Get confidence score for pattern"""
        return self.patterns["patterns"][category][name].get("confidence", 0.80)

# Singleton
_loader = None

def get_pattern_loader():
    global _loader
    if _loader is None:
        _loader = PatternLoader()
    return _loader
```

**Refactor extraction**:
- [ ] In `extractor/text_extractor.py`:
  - Add: `loader = get_pattern_loader()`
  - Replace hardcoded regex with: `loader.get_pattern("khoj_osint", "phone")`
- [ ] In `extractor/detector.py`:
  - Replace hardcoded strings with pattern lookups
- [ ] Test: Extraction still works, patterns applied correctly
- [ ] Commit: `refactor: centralize regex patterns to YAML config`

**PR Check**:
- [ ] All patterns moved to YAML
- [ ] No hardcoded patterns remain in code
- [ ] Tests pass
- [ ] Extraction accuracy unchanged

---

### P1.4: Quality Gates ⏳ TODO
**Files**: `config/quality_gates.yaml`, `quality/quality_gate.py`, update `analyzer/sdr_analyzer.py`  
**Effort**: 4 hours

**Create Files**:
- [ ] Create `quality/__init__.py` (empty)
- [ ] Create `quality/quality_gate.py`:

```python
from dataclasses import dataclass
from typing import Callable, Any

@dataclass
class QualityGate:
    name: str
    required: bool
    validator: Callable
    min_score: float = 0.0
    
    def validate(self, report) -> tuple[bool, str]:
        """Returns (passed, reason)"""
        try:
            result = self.validator(report)
            if not result and self.required:
                return False, f"{self.name} validation failed"
            return True, ""
        except Exception as e:
            if self.required:
                return False, f"{self.name}: {str(e)}"
            return True, ""

# Built-in validators
def has_valid_phone(report):
    return report.phone_number and len(report.phone_number) >= 10

def meets_completeness(report, threshold=0.70):
    completeness = calculate_completeness(report)
    return completeness >= threshold

# ... add more validators
```

- [ ] Create `config/quality_gates.yaml`:

```yaml
quality_gates:
  phone_number:
    required: true
    min_confidence: 0.90
  
  operator:
    required: false
    min_confidence: 0.80
  
  completeness:
    required: true
    min_score: 0.70
```

**Update pipeline**:
- [ ] In `pipeline.py`, after extraction:
  - Add quality gate validation
  - Mark as successful only if all required gates pass
- [ ] Update success criteria (don't use "0 warnings")
- [ ] Test: Verify quality gates enforced
- [ ] Commit: `feat: add quality gates framework`

**PR Check**:
- [ ] Quality gates prevent bad data
- [ ] Clear pass/fail criteria
- [ ] Tests verify gate behavior

---

### P1.5: Logging Framework ⏳ TODO
**File**: `utils/logging.py`, update all other files  
**Effort**: 3 hours

**Create**:
- [ ] Create `utils/__init__.py` (empty)
- [ ] Create `utils/logging.py`:

```python
import logging
import os
from pythonjsonlogger import jsonlogger

def setup_logging(log_level=None):
    log_level = log_level or os.getenv("LOG_LEVEL", "INFO")
    
    logger = logging.getLogger("sdr_mapper")
    logger.setLevel(log_level)
    
    # File handler (JSON)
    os.makedirs("logs", exist_ok=True)
    file_handler = logging.FileHandler("logs/sdr_mapper.log")
    file_handler.setFormatter(jsonlogger.JsonFormatter())
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '[%(levelname)s] %(name)s: %(message)s'
    ))
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()
```

**Replace print statements**:
- [ ] In `main.py`: Replace `print()` with `logger.info()`
- [ ] In `pipeline.py`: Replace `print()` with `logger.info/warning`
- [ ] In `extractor/detector.py`: Replace `print()` with `logger.debug`
- [ ] In `extractor/text_extractor.py`: Replace `print()` with `logger.debug`
- [ ] In `extractor/ocr_extractor.py`: Replace `print()` with `logger.info/warning`
- [ ] Test: Run system, verify logs in `logs/` directory
- [ ] Commit: `refactor: replace print with structured logging`

**PR Check**:
- [ ] No print statements remain
- [ ] Logs in JSON format
- [ ] Log levels appropriate

---

### P1.6: Per-Page OCR Retry ⏳ TODO
**File**: `extractor/ocr_extractor.py`  
**Effort**: 2 hours

**Current Problem**:
- If avg_confidence < 0.60, retries ALL pages at 300 DPI
- Wastes compute on high-confidence pages

**Solution**:
- [ ] Track per-page confidence separately
- [ ] Only retry pages with confidence < 0.60
- [ ] Keep high-confidence pages from first pass

**Implementation**:
```python
# In extract_ocr_pdf():
# Old: if avg_conf < 0.60: retry_all_pages()
# New: retry_low_confidence_pages = [i for i, conf in page_confs.items() if conf < 0.60]
#      if retry_low_confidence_pages:
#          retry_at_higher_dpi(retry_low_confidence_pages)
```

- [ ] Test: Extract PDF, verify only low-conf pages retried
- [ ] Benchmark: Processing time should decrease
- [ ] Commit: `perf: implement per-page OCR retry`

**PR Check**:
- [ ] Only retries low-confidence pages
- [ ] Performance improved
- [ ] Accuracy maintained

---

### P1.7: Robust Section Extraction ⏳ TODO
**File**: `extractor/text_extractor.py`  
**Effort**: 3 hours

**Current Problem**:
- `_extract_section()` fails silently if start pattern missing
- Extracts to EOF if end pattern missing
- Can't handle case variations

**Solution**:
```python
def _extract_section_robust(text, start_pattern, end_patterns, max_length=1000):
    """
    Robust section extraction with fallbacks
    """
    # 1. Try exact regex
    start_match = re.search(start_pattern, text, re.IGNORECASE)
    if not start_match:
        logger.debug(f"Start pattern '{start_pattern}' not found")
        return None
    
    start_pos = start_match.end()
    end_pos = start_pos + max_length  # Don't extract too much!
    
    # 2. Find end pattern
    for end_pattern in end_patterns:
        end_match = re.search(end_pattern, text[start_pos:], re.IGNORECASE)
        if end_match:
            end_pos = min(end_pos, start_pos + end_match.start())
    
    return text[start_pos:end_pos].strip()
```

- [ ] Refactor `_extract_section()` to be more robust
- [ ] Add fuzzy matching for section headers
- [ ] Add max_length to prevent over-extraction
- [ ] Test: Verify extraction handles case variations
- [ ] Commit: `refactor: make section extraction more robust`

**PR Check**:
- [ ] Handles case variations
- [ ] Doesn't extract excessive content
- [ ] Graceful fallback behavior

---

## 🔶 PHASE 2: CORE REFACTORING (Days 5-11)

> Start ONLY after Phase 1 complete ✓

### P2.1: Extractor Interface ⏳ TODO
**Files**: Create `infrastructure/extractors/`, refactor extractors  
**Effort**: 1 day (depends: P1.3 ✓)

- [ ] Create `infrastructure/__init__.py`
- [ ] Create `infrastructure/extractors/__init__.py`
- [ ] Create `infrastructure/extractors/base_extractor.py` with abstract base
- [ ] Create `infrastructure/extractors/pdf_text_extractor.py` (move code from text_extractor.py)
- [ ] Create `infrastructure/extractors/pdf_ocr_extractor.py` (move code from ocr_extractor.py)
- [ ] Update `pipeline.py` to use extractor chain
- [ ] Test: All extractors work through new interface
- [ ] Commit: `refactor: create pluggable extractor architecture`

**PR Check**:
- [ ] New extractor can be added without touching existing code
- [ ] Extractor chain works (fallback)
- [ ] All tests pass

---

### P2.2: Report Type Scoring ⏳ TODO
**Files**: Create `infrastructure/detectors/`, `config/report_formats.yaml`  
**Effort**: 1 day (depends: P1.3 ✓)

- [ ] Create `infrastructure/detectors/__init__.py`
- [ ] Create `infrastructure/detectors/format_registry.py` with scoring logic
- [ ] Create `config/report_formats.yaml` with fingerprints + weights
- [ ] Refactor `detector.py` to use registry
- [ ] Test: Scoring works, weighted detection accurate
- [ ] Commit: `refactor: implement weighted report type detection`

**PR Check**:
- [ ] Detection order-independent
- [ ] Scoring correct
- [ ] Confidence scores reasonable

---

### P2.3: Error Recovery ⏳ TODO
**Files**: `utils/exceptions.py`, `utils/retry.py`, update `pipeline.py`  
**Effort**: 1 day (depends: P2.1 ✓)

- [ ] Create custom exceptions in `utils/exceptions.py`
- [ ] Create retry decorator in `utils/retry.py`
- [ ] Update `pipeline.py` to catch errors and try fallback extractor
- [ ] Add retry logic for transient errors
- [ ] Test: Verify fallback chain works (text → OCR → error)
- [ ] Commit: `feat: add error recovery and fallback extraction`

**PR Check**:
- [ ] Fallback extractor tried on failure
- [ ] Retry logic works
- [ ] Better success rate

---

### P2.4: Separate Models ⏳ TODO
**Files**: Create `domain/`, refactor `models/schema.py`  
**Effort**: 1 day (depends: P2.2 ✓, P1.2 ✓)

- [ ] Create `domain/__init__.py`
- [ ] Create `domain/khoj_osint_report.py` with typed model
- [ ] Create `domain/scaninfoga_report.py` with typed model
- [ ] Create `domain/sdr_report_factory.py` to create correct type
- [ ] Update extractors to return typed reports
- [ ] Update analyzer to handle both types
- [ ] Test: Type checking works, serialization correct
- [ ] Commit: `refactor: separate report models by type`

**PR Check**:
- [ ] No mixing of khoj + scaninfoga fields
- [ ] Type checking enforced
- [ ] Factory pattern works

---

### P2.5: Configuration Management ⏳ TODO
**File**: `config/settings.py`, `.env.example`  
**Effort**: 1 day

- [ ] Create `config/settings.py` with Pydantic Settings class
- [ ] Create `.env.example` with all environment variables
- [ ] Make all CLI args configurable via settings
- [ ] Test: Settings load from env, override CLI defaults
- [ ] Commit: `feat: add configuration management`

**PR Check**:
- [ ] All config externalized
- [ ] Environment variables work
- [ ] .env.example documented

---

### P2.6: Unit Tests ⏳ TODO
**Files**: Create `tests/`, write test suites  
**Effort**: 1.5 days (depends: All Phase 1 ✓)

- [ ] Create `tests/` directory structure
- [ ] Write tests: `tests/unit/test_detectors.py`
- [ ] Write tests: `tests/unit/test_extractors.py`
- [ ] Write tests: `tests/unit/test_validators.py`
- [ ] Write tests: `tests/integration/test_khoj_pipeline.py`
- [ ] Write tests: `tests/integration/test_scaninfoga_pipeline.py`
- [ ] Run tests: `pytest --cov` (target: 70%+)
- [ ] Commit: `test: add comprehensive test suite`

**PR Check**:
- [ ] Coverage >= 70%
- [ ] All tests pass
- [ ] Integration tests include real PDFs

---

### P2.7: Documentation ⏳ TODO
**Files**: `README.md`, `docs/*.md`  
**Effort**: 1 day

- [ ] Update `README.md` with architecture diagram
- [ ] Create `docs/ARCHITECTURE.md` (system design)
- [ ] Create `docs/CONFIGURATION.md` (settings)
- [ ] Create `docs/EXTRACTION_PATTERNS.md` (add patterns)
- [ ] Create `docs/ADDING_FORMATS.md` (new report types)
- [ ] Test: Follow docs yourself, verify accuracy
- [ ] Commit: `docs: comprehensive architecture documentation`

**PR Check**:
- [ ] All docs clear and accurate
- [ ] Examples work
- [ ] No dead links

---

## 🟡 PHASE 3+: ENTERPRISE (Days 12+)

> Fill in as you reach these phases

### Phase 3 (Days 12-17):
- [ ] P3.1: Metrics
- [ ] P3.2: Tracing
- [ ] P3.3: Feature Flags
- [ ] P3.4: Audit Trail
- [ ] P3.5: Validation Engine
- [ ] P3.6: Plugin System
- [ ] P3.7: Benchmarking

### Phase 4 (Days 18-25):
- [ ] P4.1: Database Storage
- [ ] P4.2: API Endpoints
- [ ] P4.3: Message Queue
- [ ] P4.4: Docker/K8s
- [ ] P4.5: Data Lake Export

### Phase 5 (Days 26-30):
- [ ] P5.1: Alerting Rules
- [ ] P5.2: CI/CD Pipeline
- [ ] P5.3: Runbooks
- [ ] P5.4: SLOs/SLIs
- [ ] P5.5: Disaster Recovery

---

## 📊 Progress Summary

```
Week 1 (Phase 1):  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 0%
Week 2 (Phase 2):  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 0%
Week 3 (Phase 3):  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 0%
Week 4 (Phase 4):  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 0%
Week 5 (Phase 5):  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 0%
────────────────────────────────────────────────────────
Total:             ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 0%
```

---

## Notes & Issues

```
[Space for writing notes during implementation]
```

---

**Start with P1.3 - it unblocks the most tasks!**  
**Print this and check off items as you go!**
