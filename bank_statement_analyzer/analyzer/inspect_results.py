import json
import os
from pathlib import Path

output_dir = "output"
results = []

for json_file in Path(output_dir).glob("*.json"):
    if json_file.name.endswith("_report.json"):
        continue
        
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        file_name = json_file.name
        
        # Header Fields
        acc = data.get("account", {})
        summ = data.get("summary", {})
        
        holder = acc.get("holder_name")
        acc_num = acc.get("account_number")
        open_bal = summ.get("opening_balance")
        close_bal = summ.get("closing_balance")
        
        # Transaction Fields (aggregate counts)
        txns = data.get("transactions", [])
        null_date = 0
        null_amount = 0
        null_balance = 0
        unknown_type = 0
        
        for tx in txns:
            if tx.get("date") is None: null_date += 1
            if tx.get("amount") is None: null_amount += 1
            if tx.get("balance") is None: null_balance += 1
            if tx.get("type") == "unknown": unknown_type += 1
            
        results.append({
            "file": file_name,
            "holder": "NULL" if holder is None else "OK",
            "acc_num": "NULL" if acc_num is None else "OK",
            "open_bal": "NULL" if open_bal is None else "OK",
            "close_bal": "NULL" if close_bal is None else "OK",
            "txn_null_date": null_date,
            "txn_null_amt": null_amount,
            "txn_null_bal": null_balance,
            "txn_unk_type": unknown_type,
            "total_txns": len(txns)
        })
            
    except Exception as e:
        pass

# Print as a nice table
header = f"{'FILE':<40} | {'HOLDER':<6} | {'ACC_NUM':<7} | {'OPEN_B':<6} | {'CLOSE_B':<7} | {'TX_DATE':<7} | {'TX_AMT':<6} | {'TX_BAL':<6}"
print(header)
print("-" * len(header))

for r in results:
    # Truncate file name for readability
    fname = (r['file'][:37] + '..') if len(r['file']) > 37 else r['file']
    print(f"{fname:<40} | {r['holder']:<6} | {r['acc_num']:<7} | {r['open_bal']:<6} | {r['close_bal']:<7} | {r['txn_null_date']:<7} | {r['txn_null_amt']:<6} | {r['txn_null_bal']:<6}")
