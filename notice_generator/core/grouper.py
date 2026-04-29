from collections import defaultdict
import re

def group_by_bank(transactions):
    """
    Groups filtered transactions by bank and aggregates account details.
    
    :param transactions: List of transaction dictionaries.
    :return: Dictionary keyed by bank name with aggregated data.
    """
    grouped_data = defaultdict(lambda: {
        'accounts': set(), 
        'total_amount': 0.0,
        'transactions': []
    })
    
    for txn in transactions:
        bank_name = txn.get('bank', 'Unknown Bank').strip()
        # Use destination_account as the primary target for notices
        account_no = txn.get('destination_account', 'Unknown Account').strip()
        
        # Clean amount string (remove commas)
        amount_str = txn.get('amount', '0').replace(',', '')
        try:
            amount = float(amount_str)
        except ValueError:
            amount = 0.0
            
        if bank_name and account_no:
            grouped_data[bank_name]['accounts'].add(account_no)
            grouped_data[bank_name]['total_amount'] += amount
            grouped_data[bank_name]['transactions'].append({
                'account': account_no,
                'amount': amount,
                'utr': txn.get('transaction_utr', ''),
                'date': txn.get('datetime', ''),
                'ifsc': txn.get('destination_ifsc', '')
            })
            
    # Convert sets to sorted lists for deterministic output
    final_output = {}
    for bank, data in grouped_data.items():
        final_output[bank] = {
            'accounts': sorted(list(data['accounts'])),
            'total_amount': round(data['total_amount'], 2),
            'transactions': data['transactions']
        }
        
    return final_output
