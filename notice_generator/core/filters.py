def filter_transactions_by_layer(transactions, target_layers=None):
    """
    Filters a list of transactions based on target layer IDs.
    
    :param transactions: List of transaction dictionaries.
    :param target_layers: List of strings (e.g., ["1", "2"]) or None for all.
    :return: Filtered list of transactions.
    """
    if not target_layers:
        return transactions
    
    # Ensure target_layers are strings for matching
    target_layers = [str(l) for l in target_layers]
    
    return [t for t in transactions if str(t.get('layer')) in target_layers]
