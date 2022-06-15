class TransactionSide(object):
    """
    Type de transation, achat direct, limite ou par stop
    """
    # Possible values of cmd field:
    BUY = 0
    SELL = 1
    BUY_LIMIT = 2
    SELL_LIMIT = 3
    BUY_STOP = 4
    SELL_STOP = 5

    #Possible values of type field
    OPEN = 0
    PENDING = 1
    CLOSE = 2
    MODIFY = 3
    DELETE = 4