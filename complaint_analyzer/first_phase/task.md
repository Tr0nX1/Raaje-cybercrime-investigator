# System Redesign Implementation Tasks

- [x] **1. Define Coordinate Structures:** Create the base data models (e.g., `Word`, `PhysicalLine`, `TransactionRow`) to manage 2D spatial layouts.
- [x] **2. Spatial Word Extraction (`engine/parser.py`):** Rip out `pdfplumber.extract_tables()` and replace it with `extract_words()` logic, calculating X-axis line density to find the Date, Details, and Math columns.
- [x] **3. Date-Anchored Grouping (`engine/parser.py`):** Group physical text lines vertically using regular expressions explicitly checked against the Date column X-boundaries.
- [x] **4. Multi-Page Edge Cases (`engine/parser.py`):** Implement header/footer stripping and splice transactions that break across page boundaries. Skip "Brought Forward" artifacts.
- [x] **5. Micro-Math Validation (`engine/validator.py`):** Build the `LedgerValidator` to trace chronological `Previous Balance - Debit + Credit = Expected Balance` line by line. Pinpoint exact corrupted zones when math fails.
- [x] **6. Micro-Auditor LLM Re-design (`engine/llm_client.py`):** Deprecate the massive full-page LLM prompt. Design a strict, focused prompt that only takes a corrupted row + the target beginning/ending balances. (`MICRO_AUDIT_PROMPT` + `heal_ledger_rows()` in place; `call_llm_text` full-page extractor removed.)
- [x] **7. Auto-Healing Pipeline Integration (`engine/pipeline.py`):** Wire the parser, validator, and llm_client together so the system falls back onto the LLM *only* for the broken slices of the document. (`run_pipeline()` + `_apply_healing()` created.)
- [x] **8. Entrypoint Refactoring:** Update `main.py` and `forensic_batch_analyzer.py` to push documents through this new unified spatial-validation pipeline. (Removed broken `call_llm_text` imports; both now route through `run_pipeline`.)
- [x] **9. End-to-End Validation:** Run local integration tests on existing complex PDFs inside `inputs/` to ensure math validation passes without full-page token hallucination. (`run_validation.py` updated to use `run_pipeline`; fixed broken `ExtractionValidator` import.)
