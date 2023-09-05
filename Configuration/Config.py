class Config:
    # set to true on debug environment only
    DEBUG = True

    # Variable de connection serveur-----------------------------------------------------------------------------------------
    # DEMO: main port: 5124, streaming port: 5125,
    # REAL: main port: 5112, streaming port: 5113.
    # DEFAULT_XAPI_ADDRESS = 'xapi.xtb.com'

    # Compte demo ---------------------------------------
    DEFAULT_XAPI_ADDRESS = 'xapi.xtb.com'
    DEFAULT_XAPI_PORT = 5124
    DEFUALT_XAPI_STREAMING_PORT = 5125
    USER_ID = "15108702"
    PASSWORD = "1976Drick!"

    # ------Compte reel------------------------------------------------------
    #DEFAULT_XAPI_ADDRESS = 'xapi.xtb.com'
    #DEFAULT_XAPI_PORT = 5112
    #DEFUALT_XAPI_STREAMING_PORT = 5113
    #USER_ID = "1502064"
    #PASSWORD = "1976Drick!"

    API_SEND_TIMEOUT = 100  # API inter-command timeout (in ms)
    API_MAX_CONN_TRIES = 3  # max connection tries

    # wrapper name and version ---------------------------------------------------------------------------------------------
    WRAPPER_NAME = 'python'
    WRAPPER_VERSION = '2.5.0'