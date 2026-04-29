# SDR Mapping - OSINT Report Processor

A comprehensive system for extracting and processing OSINT (Open Source Intelligence) reports from PDF documents, similar to the bank statement analyzer but specialized for SDR (Social Data Reconnaissance) reports.

## Features

- **Multi-format Support**: Processes both Khoj OSINT reports and Scaninfoga reports
- **Dual Extraction Methods**: Text-based extraction for digital PDFs, OCR for scanned documents
- **Parallel Processing**: Batch processing with configurable worker threads
- **Data Validation**: Comprehensive validation and quality scoring
- **Structured Output**: Clean JSON output with full metadata
- **Analysis Insights**: Pattern analysis and risk assessment

## Supported Report Types

### 1. Khoj OSINT Reports
- Phone number intelligence
- Operator and circle information
- Alias names and identities
- Email addresses
- UPI/VPA account details
- Geographic locations
- Social media identifiers
- Compromised data analysis

### 2. Scaninfoga Reports
- Personal details (name, DOB, PAN, Aadhaar)
- Security scores (Security Score, CIBIL Score)
- Detection summaries
- Telecom information
- Document verification status

## Installation

```bash
cd SDR_mapping
pip install -r requirements.txt
```

## Usage

### Single File Processing
```bash
# Process a single PDF
python main.py input/report.pdf

# Force OCR mode for scanned PDFs
python main.py input/report.pdf --force-ocr

# Custom OCR settings
python main.py input/report.pdf --ocr-dpi 300 --ocr-workers 8
```

### Batch Processing
```bash
# Process all PDFs in a directory
python main.py input/ --batch

# Custom output directory
python main.py input/ --batch --output-dir results/

# Parallel processing with custom workers
python main.py input/ --batch --max-workers 8
```

## Output Format

Each processed PDF generates a JSON file with the following structure:

```json
{
  "source_file": "input/report.pdf",
  "report_type": "khoj_osint",
  "extraction_method": "text",
  "phone_number": "9560978030",
  "report_generated_by": "822571136",
  "report_generation_datetime": "2026-03-23T11:09:00",
  "operator_details": {
    "operator": "Airtel",
    "circle": "Delhi"
  },
  "aliases": [
    "akash sahota",
    "Jagga Jasoos FC",
    "AKASH SINGH SAHOTA"
  ],
  "email_addresses": [
    "akash.110795@rediffmail.com",
    "jaggajasoos@gmail.com"
  ],
  "upi_vpa_accounts": [
    {
      "upi_id": "9560978030@apl",
      "app_bank": "Amazon Pay"
    }
  ],
  "locations": ["Delhi"],
  "personal_details": {
    "full_name": "Ravinder Rvinder",
    "gender": null,
    "security_scores": {
      "security_score": 100,
      "cibil_score": 0
    }
  },
  "warnings": []
}
```

## Project Structure

```
SDR_mapping/
├── main.py                 # CLI entry point
├── pipeline.py            # Main processing pipeline
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── input/                # Input PDF files
├── output/               # Generated JSON outputs
├── models/
│   ├── __init__.py
│   └── schema.py         # Pydantic data models
├── extractor/
│   ├── __init__.py
│   ├── detector.py       # PDF type detection
│   ├── text_extractor.py # Text-based extraction
│   ├── ocr_extractor.py  # OCR-based extraction
│   └── normalizer.py     # Text normalization utilities
└── analyzer/
    ├── __init__.py
    └── sdr_analyzer.py   # Validation and analysis
```

## Data Models

### SDRReport (Main Model)
- `source_file`: Original PDF path
- `report_type`: "khoj_osint" or "scaninfoga"
- `extraction_method`: "text" or "ocr"
- `phone_number`: Primary phone number
- `report_generated_by`: Report generator ID
- `report_generation_datetime`: Generation timestamp

### Khoj OSINT Specific Fields
- `operator_details`: Telecom operator information
- `aliases`: List of associated names/identities
- `email_addresses`: Associated email addresses
- `upi_vpa_accounts`: UPI payment accounts
- `locations`: Geographic locations
- `social_media_accounts`: Social media identifiers
- `compromised_services`: Data breach information

### Scaninfoga Specific Fields
- `personal_details`: Personal information
- `security_scores`: Security and credit scores
- `detection_summary`: Account detection statistics
- `telecom_info`: Telecom connection details

## Extraction Methods

### Text Extraction
- Uses `pdfplumber` for direct text extraction
- Pattern-based parsing with regex
- Section-aware content extraction
- Handles multi-page documents

### OCR Extraction
- Uses `easyocr` for scanned documents
- Automatic quality detection and retry
- Parallel page processing
- DPI optimization for accuracy

## Validation & Analysis

### Data Validation
- Phone number format validation
- Email address validation
- UPI ID format checking
- Security score range validation
- Completeness scoring

### Pattern Analysis
- Phone number region analysis
- Email domain distribution
- UPI provider analysis
- Security risk assessment
- Data completeness calculation

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `--ocr-dpi` | 200 | DPI for OCR processing |
| `--ocr-workers` | 4 | OCR worker threads |
| `--max-workers` | 4 | Parallel processing workers |
| `--output-dir` | output/ | Output directory |
| `--force-ocr` | False | Force OCR even for text PDFs |

## Error Handling

- Graceful failure handling with error reports
- Warning accumulation for non-critical issues
- Processing summary with success/failure counts
- Detailed error logging

## Performance

- Parallel PDF processing
- OCR worker thread optimization
- Memory-efficient text processing
- Batch processing with progress tracking

## Dependencies

- `pdfplumber`: PDF text extraction
- `pydantic`: Data validation and serialization
- `easyocr`: OCR processing
- `Pillow`: Image processing
- `PyMuPDF`: PDF manipulation
- `numpy`: Numerical operations
- `opencv-python`: Computer vision

## Similar to Bank Statement Analyzer

This SDR mapping system follows the same architectural patterns as the bank statement analyzer:

- **Modular Design**: Separate concerns (extraction, analysis, models)
- **Dual Processing**: Text and OCR extraction paths
- **Parallel Processing**: Concurrent file processing
- **Structured Output**: Consistent JSON format
- **Validation Layer**: Data quality assurance
- **CLI Interface**: Command-line operation
- **Batch Support**: Directory processing

## Future Enhancements

- Machine learning-based entity recognition
- Advanced pattern matching for new report formats
- Web interface for report visualization
- Database integration for report storage
- API endpoints for programmatic access
- Custom report template support