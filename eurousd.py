# -*- coding: utf-8 -*-
# python3 -m pip install pymongo==3.5.1
import json
import asyncio
import math as math
from datetime import datetime, timedelta
from pymongo import MongoClient
from Service.Order import Order
from Service.APIClient import APIClient
from Service.APIStreamClient import APIStreamClient
from Service.Command import Command
from Service.Email import Email

from Configuration.Log import getmylogger

'''

Strategie

Periode 5 min :
A) Acheter pivot Woodie si la EMA7 repasse au dessus de la ligne de soutien
B) Acheter 
    si EMa7 > EAM25 et Awesome > 20 (3 bars verte au dessus de 20)
    et  Prix a touché S2 de Woodie
: Position achat: EAM25  stop au plus bas des 10 derniers periodes si supertrend est ko sinon faire  avec super tr

Calcul de lot
---------------
1 lot Forex équivaut à 100 000
Un pip sur la paire de devises EUR/USD vaut 20 USD par lot.

si l euro/usd vaut 1.0745 donc le VNL = 1 lot/1.0745€/10 = 9.30€

9.30€ / pip / lot
pip 0.0001

18.6 pip cout 173 pour 1 lot
VLN*nbre de pip= valeur
9.30*18.1 = 172.9€

pour 0.5 lot
9.30*18.5*0.5= 86.5€

90€/(9.30*18.5pip) = 0.52

'''

# Variables perso--------------------------------------------------------------------------------------------------------
# horaire---------------
TradeStartTime = 4
TradeStopTime = 22
# gestion managment-----
Risk = 2.00  # risk %
ObjectfDay = 5.00  # %

BALANCE = 0
TICK = False
PROFIT = False
SYMBOL = "EURUSD"
VNL = 9.30
SPREAD = 0.0001
ARRONDI= 100000.0
ARRONDI_INDIC=5

logger = getmylogger(__name__)

# 1 pips 25€ pour 1 lots

def startEA_Horaire():
    time = datetime.now().time()
    if TradeStartTime < int(time.strftime("%H")) < TradeStopTime:
        return True
    else:
        return False


def updatePivot():
    time = datetime.now().time()
    if 6 > int(time.strftime("%H")) > 1:
        return True
    else:
        return False



def findTradesHistory(client, start):
    '''
    Selectionner les ordres ouverts
    :param client: parametre de connexion
    :return: dictionnaire d ordre
    '''
    tradesHistoryString = client.commandExecute('getTradesHistory', {"end": 0, "start": start})
    tradesHistoryJson = json.dumps(tradesHistoryString)
    return json.loads(tradesHistoryJson)


def findopenOrder(client):
    '''
    Selectionner les ordres ouverts
    :param client: parametre de connexion
    :return: dictionnaire d ordre
    '''
    tradeOpenString = client.commandExecute('getTrades', {"openedOnly": True})
    tradeOpenJson = json.dumps(tradeOpenString)
    return json.loads(tradeOpenJson)



def round_up(n, decimals=0):
    '''
    Arrondi au superieur
    :param n:
    :param decimals:
    :return:
    '''
    multiplier = 10 ** decimals
    return math.ceil(n * multiplier) / multiplier

def round_down(n, decimals=0):
    '''
    Arrondi à l inférieur
    :param n:
    :param decimals:
    :return:
    '''
    multiplier = 10 ** decimals
    return math.floor(n * multiplier) / multiplier

def zoneSoutien(close, zone):
    arrayT = sorted(zone)
    minimumPIP = 15
    supportDown = 0
    supportHigt = 0
    for v in arrayT:
        if v < close - minimumPIP:
            supportDown = v
        if v > close + minimumPIP:
            if supportHigt == 0:
                supportHigt = v
                # print("pîvot up calcul:", supportHigt)

    # print(supportDown, " / ", supportHigt)
    return supportDown, supportHigt

def zoneResistance(close, zone):
    arrayT = sorted(zone)
    resistance = 0
    for v in arrayT:
        if v > close and resistance == 0:
            resistance = v
            return resistance
    return None

def zoneResistanceVente(close, zone):
    arrayT = sorted(zone, reverse=True)
    resistance = 0
    for v in arrayT:
        if v < close and resistance == 0:
            resistance = v
            return resistance
    return None

def subscribe(loginResponse):
    c = Command()
    ssid = loginResponse['streamSessionId']
    sclient = APIStreamClient(
        ssId=ssid,
        tickFun=c.procTickExample,
        tradeFun=c.procTradeExample,
        balanceFun=c.procBalanceExample,
        tradeStatusFun=c.procTradeStatusExample,
        profitFun=c.procProfitExample,
        candles=c.procCandles
    )
    sclient.subscribePrice(SYMBOL)
    sclient.subscribeProfits()
    sclient.subscribeTradeStatus()
    sclient.subscribeTrades()
    sclient.subscribeBalance()
    sclient.subscribeCandles(SYMBOL)

    return sclient, c


async def connectionAPI():
    client = APIClient()  # create & connect to RR socket
    loginResponse = client.identification()  # connect to RR socket, login
    logger.info(str(loginResponse))

    # check if user logged in correctly
    if not loginResponse['status']:
        print('Login failed. Error code: {0}'.format(loginResponse['errorCode']))
        return
    sclient, c = subscribe(loginResponse)
    return sclient, c, client


async def main():
    email = Email()

    order = []
    try:
        sclient, c, client = await connectionAPI()
        connection = MongoClient('localhost', 27017)
        db = connection[SYMBOL]
        dbStreaming = connection["STREAMING"]

        logger.info("mise à jour")

        logger.info("mise à jour fini")


        # # Awesome ##################################################################################################
        logger.info("calcul Awesome")
        #ao05 = Awesome(SYMBOL, "M05", ARRONDI_INDIC)
        #await ao05.calculAllCandles()
        #
        logger.info("reception des ordres en cours")
        o = Order(SYMBOL, dbStreaming, client, db["trade"])



    except Exception as exc:
        logger.warning(exc)
        email.sendMail(exc)
        client.disconnect()
        sclient.disconnect()
        exit(0)

    client.disconnect()
    sclient.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
