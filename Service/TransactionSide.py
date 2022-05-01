class TransactionSide(object):
    """
    Type de transation, achat direct, limite ou par stop
    """
    BUY = 0
    SELL = 1
    BUY_LIMIT = 2
    SELL_LIMIT = 3
    BUY_STOP = 4
    SELL_STOP = 5