# -*- coding: utf-8 -*-
# python3 -m pip install pymongo==3.5.1
import json
import time
import asyncio
import math as math
import numpy as np
from datetime import datetime, timedelta
from pymongo import MongoClient
from Indicators.Awesome import Awesome
from Service.Order import Order
from Indicators.Pivot import Pivot
from Indicators.SMA import MM
from Service.APIClient import APIClient
from Service.APIStreamClient import APIStreamClient
from Service.Command import Command
from Indicators.Supertrend import Supertrend
from Service.TransactionSide import TransactionSide
from Service.Email import Email

import logging


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

# 1 pips 25€ pour 1 lots


async def insertData(logger, email, collection, dataDownload, lastBougieDB):
    '''
    Insertion des données dans l base de donnée ou mise à jour de a dernière donnée de la collection
    :param collection: collection à la quelle on insere des données
    :param dataDownload: (dict) données
    :param listDataDB: dernière ligne de données provenant de la collection
    :return: time traité
    '''

    try:
        if dataDownload['status'] and len(dataDownload["returnData"]['rateInfos']) > 0:
            for value in dataDownload["returnData"]['rateInfos']:
                ctm = value['ctm']
                close = (value['open'] + value['close']) / ARRONDI
                high = (value['open'] + value['high']) / ARRONDI
                low = (value['open'] + value['low']) / ARRONDI
                pointMedian = round((high + low) / 2, 2)
                # print(value['ctm'] ,">", lastBougieDB['ctm'])
                if lastBougieDB is None or value['ctm'] > lastBougieDB['ctm']:
                    open = value['open'] / ARRONDI
                    newvalues = {
                        "ctm": ctm,
                        "ctmString": value['ctmString'],
                        "open": open,
                        "close": close,
                        "high": high,
                        "low": low,
                        "vol": value['vol'],
                        "pointMedian": pointMedian
                    }
                    collection.insert_one(newvalues)
                elif value['ctm'] == lastBougieDB['ctm']:
                    myquery = {"ctm": value['ctm']}
                    newvalues = {
                        "$set": {
                            "close": close,
                            "high": high,
                            "low": low,
                            "vol": value['vol'],
                            "pointMedian": pointMedian
                        }}
                    collection.update_many(myquery, newvalues)

    except Exception as exc:
        logger.warning(exc)
        email.sendMail(exc)


async def majDatAall(logger, email, client, symbol, db):
    '''
    Mise à jour de la base de données
    Limitations: there are limitations in charts data availability. Detailed ranges for charts data, what can be accessed with specific period, are as follows:
    PERIOD_M1 --- <0-1) month, i.e. one month time
    PERIOD_M30 --- <1-7) month, six months time
    PERIOD_H4 --- <7-13) month, six months time
    PERIOD_D1 --- 13 month, and earlier on
    :param client: parametre de connexion
    :param startTime: date de départ en ms
    :param symbol: Indice
    :param db: collection selectionné selon symbol
    :return:
    '''
    # print("**************************************** mise à jour majDatAall ****************************************")
    try:
        # ctmRefStart = db["D"].find().sort("ctm", -1).skip(1).limit(1)
        endTime = int(round(time.time() * 1000)) + (6 * 60 * 1000)

        # MAJ DAY : 13 mois------------------------------------------------------------------------
        lastBougie = db["D"].find_one({}, sort=[('ctm', -1)])
        startTime = int(round(time.time() * 1000)) - (60 * 60 * 24 * 30 * 13) * 1000
        if lastBougie is not None:
            startTime = lastBougie["ctm"] - (60 * 60 * 24) * 1000

        json_data_Day = client.commandExecute(
            'getChartRangeRequest',
            {"info": {"start": startTime, "end": endTime, "period": 1440, "symbol": symbol, "ticks": 0}})
        dataDAY = json.dumps(json_data_Day)
        dataDAYDownload = json.loads(dataDAY)
        await insertData(logger, email, db["D"], dataDAYDownload, lastBougie)
        print("maj D FINI")

        # MAJ H4 : 13 mois max------------------------------------------------------------------------
        lastBougie = db["H4"].find_one({}, sort=[('ctm', -1)])
        startTime = int(round(time.time() * 1000)) - (60 * 60 * 24 * 30 * 13) * 1000
        if lastBougie is not None:
            startTime = lastBougie["ctm"] - (60 * 60 * 8) * 1000

        json_data_H4 = client.commandExecute('getChartRangeRequest', {
            "info": {"start": startTime, "end": endTime, "period": 240,
                     "symbol": symbol,
                     "ticks": 0}})
        data_H4 = json.dumps(json_data_H4)
        dataH4Download = json.loads(data_H4)
        await insertData(logger, email,db["H4"], dataH4Download, lastBougie)
        print("maj H4 FINI")

        # MAJ H4 : 13 mois max------------------------------------------------------------------------
        lastBougie = db["M15"].find_one({}, sort=[('ctm', -1)])
        startTime = int(round(time.time() * 1000)) - (60 * 60 * 24 * 45) * 1000
        if lastBougie is not None:
            startTime = lastBougie["ctm"] - (60 * 15) * 1000

        json_data_H4 = client.commandExecute('getChartRangeRequest', {
            "info": {"start": startTime, "end": endTime, "period": 15,
                     "symbol": symbol,
                     "ticks": 0}})
        data_H4 = json.dumps(json_data_H4)
        dataH4Download = json.loads(data_H4)
        await insertData(logger, email, db["M15"], dataH4Download, lastBougie)
        print("maj M15 FINI")

        # MAJ Minute : 1 mois max------------------------------------------------------------------------
        lastBougie = db["M01"].find_one({}, sort=[('ctm', -1)])
        startTime = int(round(time.time() * 1000)) - (60 * 60 * 24 * 5) * 1000
        if lastBougie is not None:
            startTime = lastBougie["ctm"] - (60 * 2) * 1000

        json_data_M01 = client.commandExecute('getChartRangeRequest', {
            "info": {"start": startTime, "end": endTime, "period": 1,
                     "symbol": symbol,
                     "ticks": 0}})
        print(json_data_M01)
        dataM01 = json.dumps(json_data_M01)
        dataDownload = json.loads(dataM01)
        print("maj M01:", dataDownload)


        await insertData(logger, email, db["M01"], dataDownload, lastBougie)
        print("maj M01 FINI")

        # MAJ 5 min ------------------------------------------------------------------------
        lastBougie = db["M05"].find_one({}, sort=[('ctm', -1)])
        startTime = int(round(time.time() * 1000)) - (60 * 60 * 24 * 45) * 1000
        if lastBougie is not None:
            startTime = lastBougie["ctm"] - (60 * 5) * 1000

        json_data_M05 = client.commandExecute('getChartRangeRequest', {
            "info": {"start": startTime, "end": endTime, "period": 5,
                     "symbol": symbol,
                     "ticks": 0}})
        dataM05 = json.dumps(json_data_M05)
        dataM05Download = json.loads(dataM05)

        await insertData(logger, email,db["M05"], dataM05Download, lastBougie)
        print("maj M05 FINI")

    except Exception as exc:
        logger.warning(exc)
        client.disconnect()
        exit(0)


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


async def connectionAPI(logger):
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
    logger = logging.getLogger('Main')
    handler = logging.FileHandler('mylog.log')
    formatter = logging.Formatter(
            '%(asctime)s~%(levelname)s~%(message)s~module:%(module)s~function:%(module)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)
    email = Email()

    order = []
    try:
        sclient, c, client = await connectionAPI(logger)
        connection = MongoClient('localhost', 27017)
        db = connection[SYMBOL]
        dbStreaming = connection["STREAMING"]

        logger.info("mise à jour")
        await majDatAall(logger, email, client, SYMBOL, db)


        while True:


            await majDatAall(logger, email, client, SYMBOL, db)


            time.sleep(30)

    except Exception as exc:
        logger.warning(exc)
        email.sendMail(exc)
        client.disconnect()
        exit(0)

    except OSError as exc:
        logger.warning(exc)
        email.sendMail(exc)
        client.disconnect()
        exit(0)

    client.disconnect()
    sclient.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
