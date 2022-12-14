import logging
import time
from Service.Command import Command
from Service.APIStreamClient import APIStreamClient

from Service.APIClient import APIClient
DEBUG = True

# Variable de connection serveur-----------------------------------------------------------------------------------------
# default connection properites
DEFAULT_XAPI_ADDRESS = 'xapi.xtb.com'
DEFAULT_XAPI_PORT = 5124
DEFUALT_XAPI_STREAMING_PORT = 5125
# userId = "XXXXXXXXXXXX"
# password = "XXXXXX"
# ------Compte reel------------------------------------------------------
# DEFAULT_XAPI_ADDRESS = 'xapi.xtb.com'
# DEFAULT_XAPI_PORT = 5112
# DEFUALT_XAPI_STREAMING_PORT = 5113  # API inter-command timeout (in ms)
# userId = "XXXXXXXXXXXX"
# password = "XXXXXX"


API_SEND_TIMEOUT = 100
# max connection tries
API_MAX_CONN_TRIES = 3

# wrapper name and version ---------------------------------------------------------------------------------------------
WRAPPER_NAME = 'python'
WRAPPER_VERSION = '2.5.0'

# logger properties
logger = logging.getLogger("jsonSocket")
FORMAT = '[%(asctime)-15s][%(funcName)s:%(lineno)d] %(message)s'
logging.basicConfig(format=FORMAT)

if DEBUG:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.CRITICAL)



def main():
    client = APIClient()  # create & connect to RR socket
    loginResponse = client.identification()  # connect to RR socket, login
    print(str(loginResponse))
    logger.info(str(loginResponse))

    # check if user logged in correctly
    if (loginResponse['status'] == False):
        print('Login failed. Error code: {0}'.format(loginResponse['errorCode']))
        return

    try:
        c = Command()
        ssid = loginResponse['streamSessionId']
        sclientUS100 = APIStreamClient(
            ssId=ssid,
            tickFun=c.procTickExample,
            tradeFun=c.procTradeExample,
            profitFun=c.procProfitExample,
            tradeStatusFun=c.procTradeStatusExample,
            balanceFun=c.procBalanceExample
        )

        # subscribe for profits
        # sclient.subscribeProfits()
        sclientUS100.subscribeBalance()
        sclientUS100.subscribePrice("US100")
        sclientUS100.subscribeProfits()
        sclientUS100.subscribeTradeStatus()
        sclientUS100.subscribeTrades()
        sclientUS100.subscribeBalance()

        sclientOIL = APIStreamClient(
            ssId=ssid,
            tickFun=c.procTickExample,
            tradeFun=c.procTradeExample,
            profitFun=c.procProfitExample,
            tradeStatusFun=c.procTradeStatusExample,
            balanceFun=c.procBalanceExample
        )

        # subscribe for profits
        # sclient.subscribeProfits()
        sclientOIL.subscribeBalance()
        sclientOIL.subscribePrice("OIL")
        sclientOIL.subscribeProfits()
        sclientOIL.subscribeTradeStatus()
        sclientOIL.subscribeTrades()
        sclientOIL.subscribeBalance()


        while True:

            time.sleep(5)
    except KeyboardInterrupt:
        pass
    # this is an example, make it run for 5 seconds
    # time.sleep(5)
    sclientUS100.disconnect()
    sclientOIL.disconnect()


if __name__ == "__main__":
    main()
