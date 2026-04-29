import os
import json
import pandas as pd

def profile_output(output_dir):
    stats = []
    for file in os.listdir(output_dir):
        if file.endswith(".json"):
            with open(os.path.join(output_dir, file), 'r') as f:
                try:
                    data = json.load(f)
                    acc = data.get('account', {})
                    summ = data.get('summary', {})
                    txns = data.get('transactions', [])
                    
                    stats.append({
                        "FILE": file[:20],
                        "HOLDER": "OK" if acc.get('holder_name') else "NULL",
                        "ACC_NUM": "OK" if acc.get('account_number') else "NULL",
                        "OPEN_B": "OK" if summ.get('opening_balance') is not None else "NULL",
                        "CLOSE_B": "OK" if summ.get('closing_balance') is not None else "NULL",
                        "TX_COUNT": len(txns),
                        "NULL_BAL_TX": sum(1 for t in txns if t.get('balance') is None),
                        "WARNINGS": ", ".join(data.get('warnings', []))[:30]
                    })
                except:
                    pass
    
    df = pd.DataFrame(stats)
    print(df.to_string(index=False))

if __name__ == "__main__":
    profile_output("D:/develop/ffa/bank_statement_analyzer/output")
