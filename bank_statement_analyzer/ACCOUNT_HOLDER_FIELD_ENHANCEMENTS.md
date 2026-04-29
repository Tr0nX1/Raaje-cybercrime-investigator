# Account Holder Name Field Extraction Enhancements

## Overview
Enhanced the bank statement analyzer to support multiple field name variations when extracting customer/account holder names. Different banks use different field names and formats to represent the same information.

## FIX-17: Enhanced Field Name Support

### What Changed

#### 1. **Main Regex Pattern Update** (`_HOLDER_RE`)
The primary regex pattern now supports more variations:

**Previous Patterns:**
- "customer name"
- "customer details"
- "account title"
- "account holder"
- "account holder name"
- "name of account"
- "a/c name" / "a/c holder"
- "acct name"
- "member name"
- "account name" / "acc name"
- "sole proprietor"

**New Patterns (FIX-17):**
- "customer name"
- "customer details"
- "customer account holder" (combined variation)
- "account title"
- "account holder"
- "account holder name"
- "account holder names"
- "name of account"
- "name of customer"
- "a/c name" / "a/c holder"
- "acct name" / "acct holder"
- "member name"
- "account name" / "acc name"
- "sole proprietor"
- "account details"

#### 2. **Additional Fallback Patterns**
Added two new fallback patterns to catch alternative formatting:

**Pattern 1: Generic Alternative Field Regex** (`alt_field_regex`)
```
customer: NAME
holder: NAME
account holder: NAME
account holder name: NAME
```
Confidence: 0.82

**Pattern 2: Alternative Colon Format** (`alt_colon_regex`)
```
customer name: NAME
account holder: NAME
```
Confidence: 0.81

### Why This Matters

Different banks format their statements differently:

1. **Bank A** might use: `Customer Name: JOHN SMITH`
2. **Bank B** might use: `Account Holder: JOHN SMITH`
3. **Bank C** might use: `Name of Account Holder: JOHN SMITH`
4. **Bank D** might use: `Customer: JOHN SMITH`

The enhanced extraction now handles all these variations in a single pass.

### Confidence Scoring

Extraction methods are ranked by confidence:

| Method | Confidence | Format | Priority |
|--------|-----------|--------|----------|
| `label_regex` (main pattern) | 0.90 | With colon/dash separator | 1st (highest) |
| `label_regex_bom` | 0.85 | "Account Holder Names" style | 2nd |
| `alt_field_regex` | 0.82 | Alternative generic format | 3rd |
| `alt_colon_regex` | 0.81 | Alternative colon format | 4th |
| `salutation_regex` | 0.80 | "Mr. JOHN SMITH" style | 5th |
| `allcaps_heuristic` | 0.75 | All-caps standalone line | 6th (fallback) |

The first match with highest confidence is used.

### Usage

The enhancement works automatically during statement processing:

```python
from bank_statement_analyzer.extractor.text_extractor import extract_text_pdf

# Process a bank statement
statement = extract_text_pdf("bank_statement.pdf")

# The holder_name is now extracted with support for all variations
print(f"Account Holder: {statement.account.holder_name}")
```

### Testing

To verify the enhancement is working:

1. **Test with different bank statement formats**
   - Test statements that use "Customer Name:" format
   - Test statements that use "Account Holder:" format
   - Test statements with combined patterns

2. **Check the extraction method used**
   ```python
   # View which extraction method was used
   extracted_field = extract_result.fields['holder_name']
   print(f"Method: {extracted_field.method}")
   print(f"Confidence: {extracted_field.confidence}")
   ```

3. **Verify confidence scores**
   - Statements with clear labels should score 0.90 (highest)
   - Statements with alternative formats should score 0.81-0.85
   - Fallback patterns should score lower but still capture the name

### Fields Supporting This Enhancement

- `AccountInfo.holder_name` - Primary account holder
- `Transaction.holder_name` - Transaction-level holder (when available)

### Bank-Specific Notes

**HDFC Bank**
- Uses: "Account Holder Name:" or "Name of Customer:"
- ✓ Supported

**ICICI Bank**
- Uses: "Customer Name:" or "Account Holder Name:"
- ✓ Supported

**Axis Bank**
- Uses: "Account Holder:" or "Customer Name:"
- ✓ Supported

**KOTAK Bank**
- Uses: "Account Holder Name:" or "Member Name:"
- ✓ Supported

**SBI Bank**
- Uses: "A/C Name:" or "Customer Name:"
- ✓ Supported

**Other Banks**
- Uses various formats including combined patterns
- ✓ Supported

### Future Enhancements

Possible improvements for future versions:

1. **Database of Bank Formats** - Store known patterns per bank
2. **Machine Learning** - Use ML to identify holder names probabilistically
3. **Context Awareness** - Use transaction data to validate extracted names
4. **Multilingual Support** - Handle non-English names and formats

## Files Modified

- `bank_statement_analyzer/extractor/text_extractor.py`
  - Updated `_HOLDER_RE` regex pattern (line ~71)
  - Added fallback patterns in `_extract_header_fields()` function (line ~268-282)

## Backward Compatibility

✓ **Fully backward compatible** - Existing statements that were extracting correctly will continue to work. New statements with alternative formats will now extract correctly as well.
