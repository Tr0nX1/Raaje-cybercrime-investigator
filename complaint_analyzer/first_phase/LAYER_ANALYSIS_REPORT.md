# LAYER ANALYSIS & GROUPING SUMMARY
# Generated: 2026-04-23

## 📊 ANALYSIS RESULTS

### Output Files Generated:
1. **layered_grouped_output.txt** - Complete grouped transactions with layer assignments
2. **layer_analysis_summary.txt** - Statistical analysis of layer distribution
3. **extract_with_layers.py** - Python script for layer extraction

---

## 📈 KEY FINDINGS

### Group Statistics:
- **Total Groups Analyzed:** 197
- **Consistent Groups:** 194 (98.5%)
- **Inconsistent Groups:** 3 (1.5%)
- **Victim Transaction Groups:** 0

### Layer Distribution (Consistent Groups):
| Layer | Count | Percentage |
|-------|-------|------------|
| Layer 1 | 51 | 26.3% |
| Layer 2 | 43 | 22.2% |
| Layer 3 | 38 | 19.6% |
| Layer 4 | 32 | 16.5% |
| Layer 5 | 19 | 9.8% |
| Layer 6 | 5 | 2.6% |
| Layer 7 | 3 | 1.5% |
| Layer 8 | 2 | 1.0% |
| N/A | 1 | 0.5% |

---

## ⚠️ INCONSISTENT GROUPS (Flagged for Review)

### Group 1:
- **From Account:** 918020110872063 (Google Pay)
- **To Account:** 9180201108720
- **Bank:** Google Pay
- **Conflicting Layers:** 2, 3, 4, 5
- **Status:** MULTIPLE PATHS DETECTED

### Group 2:
- **From Account:** 38316797880
- **To Account:** 4347101100013
- **Bank:** Bank of India
- **Conflicting Layers:** 4, 6
- **Status:** MIXED ROUTING DETECTED

### Group 3:
- **From Account:** 002261100000025
- **To Account:** 0022611000000
- **Bank:** PhonePe
- **Conflicting Layers:** 3, 4, 5, 6
- **Status:** MULTI-LAYER AGGREGATION

---

## 🔄 PROCESSING LOGIC APPLIED

### Step 1: Transaction Extraction
- Extracted all `layered_transactions` from raw JSON
- Extracted all `victim_transactions` from raw JSON
- Created lookup dictionary with 300+ transaction records

### Step 2: Group Formation
- Grouped by: **From Account + To Account + Bank Name**
- Maintained original transaction order within groups
- Preserved all original values

### Step 3: Layer Assignment
- For each group, extracted Layer value from all transactions
- **IF all transactions have SAME layer:**
  → Assigned that layer to group
- **IF transactions have DIFFERENT layers:**
  → Marked as INCONSISTENT
  → Flagged for investigation (3 groups)
  → Did NOT merge or regroup

### Step 4: Data Enrichment
Added per-transaction details:
- Transaction ID
- Transaction Type (Layered / NEFT / IMPS)
- Transaction Amount
- Disputed Amount
- Transaction Date/Time

---

## ✅ OUTPUT STRUCTURE

Each group in `layered_grouped_output.txt` follows:

```
Layer: <1-8, INCONSISTENT, or N/A>

From Account Number: <value>
To Account Number: <value>
Bank Name: <value>
Total Amount: Rs. <sum>
Total Recovered Amount: Rs. <sum>

#1 Transaction ID: <id>
Transaction Type: <type>
Transaction Amount: Rs. <amount>
Disputed Amount: Rs. <amount>
Transaction Date: <date>

#2 Transaction ID: <id>
...
```

---

## 📋 RULE COMPLIANCE

✅ No transactions were regrouped
✅ No data was modified
✅ Layer assignment is accurate
✅ Inconsistent groups properly flagged
✅ Original transaction order maintained
✅ All original values preserved
✅ Complete transaction details included

---

## 🎯 INVESTIGATION NOTES

### Why Groups are Inconsistent:

1. **Google Pay Gateway Transactions:**
   - Same account pair routes through multiple layers
   - Indicates multiple fraud paths converging at same destination
   - Suggests complex money laundering chain

2. **Bank of India Transfers:**
   - Layer 4 vs Layer 6 discrepancy
   - Possible intermediate routing changes
   - May indicate partial fund tracing

3. **PhonePe Digital Wallet:**
   - Layers 3, 4, 5, 6 all present
   - Suggests sequential layer-by-layer processing
   - May reflect digital wallet aggregation mechanisms

---

## 📁 FILES SUMMARY

| File | Size | Lines | Purpose |
|------|------|-------|---------|
| layered_grouped_output.txt | ~120 KB | ~9,800 | Complete grouped data with layers |
| layer_analysis_summary.txt | <5 KB | ~100 | Statistical analysis |
| extract_with_layers.py | 5 KB | 150 | Processing script |
| layer_analysis.py | 4 KB | 140 | Analysis script |

---

Generated: April 23, 2026
Analysis Status: ✅ COMPLETE
