# -*- coding: utf-8 -*-
# python3 -m pip install pymongo==3.5.1

import json
import time
import os
import sys
import asyncio
import math as math
import numpy as np
from datetime import datetime
from pymongo import MongoClient
from Indicators.Awesome import Awesome
from Service.Order import Order
from Indicators.Pivot import Pivot
from Indicators.SMA import MM
from Service.APIClient import APIClient
import logging
from Service.APIStreamClient import APIStreamClient
from Service.Command import Command
from Configuration.Config import Config
from Indicators.Supertrend import Supertrend
from Service.TransactionSide import TransactionSide

import concurrent.futures

# import datetime


# Variables perso--------------------------------------------------------------------------------------------------------
# horaire---------------
TradeStartTime = 4
TradeStopTime = 22
# gestion managment-----
Risk = 2.00  # risk %
ObjectfDay = 3.00  # %
# communication---------
SignalMail = False

BALANCE = 0
TICK = False
PROFIT = False

# GE30 le cout d un pip = 25€ * 0.01 --------------------------
PRICE = 6.95
PIP = 0.01
SYMBOL = "US100"
VNL = 35
SPREAD = 0.04

# logger properties
logger = logging.getLogger("jsonSocket")
FORMAT = '[%(asctime)-15s][%(funcName)s:%(lineno)d] %(message)s'
logging.basicConfig(format=FORMAT)

# set to true on debug environment only
DEBUG = True

if DEBUG:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.CRITICAL)


def startEA_Horaire():
    time = datetime.now().time()
    if TradeStartTime < int(time.strftime("%H")) < TradeStopTime:
        return True
    else:
        return False


async def insertData(collection, dataDownload, listDataDB):
    '''
    Insertion des données dans l base de donnée ou mise à jour de a dernière donnée de la collection
    :param collection: collection à la quelle on insere des données
    :param dataDownload: (dict) données
    :param listDataDB: dernière ligne de données provenant de la collection
    :return: time traité
    '''

    ctm = ''
    if dataDownload['status'] and len(dataDownload["returnData"]['rateInfos']) > 0:
        # import time
        # tps1 = time.clock()
        # tps2 = time.clock()
        # print("time : ",tps2 - tps1)
        # exit(0)

        for value in dataDownload["returnData"]['rateInfos']:
            if (listDataDB is None) or (value['ctm'] > listDataDB["ctm"]):
                open = value['open'] / 100.0
                close = (value['open'] + value['close']) / 100.0
                high = (value['open'] + value['high']) / 100.0
                low = (value['open'] + value['low']) / 100.0
                pointMedian = round((high + low) / 2, 2)
                newvalues = {
                    "ctm": value['ctm'],
                    "ctmString": value['ctmString'],
                    "open": open,
                    "close": close,
                    "high": high,
                    "low": low,
                    "vol": value['vol'],
                    "pointMedian": pointMedian
                }
                collection.insert_one(newvalues)
                ctm = value['ctm']
            elif value['ctm'] == listDataDB["ctm"]:
                close = (value['open'] + value['close']) / 100.0
                high = (value['open'] + value['high']) / 100.0
                low = (value['open'] + value['low']) / 100.0
                pointMedian = round((high + low) / 2, 2)
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
                ctm = value['ctm']

    return ctm


def findopenOrder(client):
    '''
    Selectionner les ordres ouverts
    :param client: parametre de connexion
    :return: dictionnaire d ordre
    '''
    tradeOpenString = client.commandExecute('getTrades', {"openedOnly": True})
    tradeOpenJson = json.dumps(tradeOpenString)
    return json.loads(tradeOpenJson)


async def majData(client, startTime, symbol, db):
    '''
    Mise à jour de la base de données
    :param client: parametre de connexion
    :param startTime: date de départ en ms
    :param symbol: Indice
    :param db: collection selectionné selon symbol
    :return:
    '''
    # print("**************************************** mise à jour start ****************************************")
    endTime = int(round(time.time() * 1000)) + (6 * 60 * 1000)
    json_data_M01 = client.commandExecute('getChartRangeRequest', {
        "info": {"start": startTime - (6 * 60 * 1000), "end": endTime, "period": 1,
                 "symbol": symbol,
                 "ticks": 0}})
    dataM01 = json.dumps(json_data_M01)
    dataM01Download = json.loads(dataM01)
    listDataDBM01 = db["M01"].find_one({}, sort=[('ctm', -1)])
    await insertData(db["M01"], dataM01Download, listDataDBM01)

    # MAJ H4 ------------------------------------------------------------------------
    # 20 jours x 24 heures x 3600 secondes x 1000
    # print("H4 :", startTime - (6 * 3600000))
    # json_data_H4 = client.commandExecute('getChartRangeRequest', {
    #     "info": {"start": startTime - (6 * 3600000), "end": endTime, "period": 240,
    #              "symbol": symbol,
    #              "ticks": 0}})
    # data_H4 = json.dumps(json_data_H4)
    # dataH4Download = json.loads(data_H4)
    # listDataDB = db["H4"].find_one({}, sort=[('ctm', -1)])
    # await insertData(db["H4"], dataH4Download, listDataDB)

    startTimeM15 = int(round(time.time() * 1000)) - (60 * 60 * 24 * 30 * 15) * 1000
    json_data_M15 = client.commandExecute('getChartRangeRequest', {
        "info": {"start": startTimeM15, "end": endTime, "period": 15,
                 "symbol": symbol,
                 "ticks": 0}})
    dataM15 = json.dumps(json_data_M15)
    dataM15Download = json.loads(dataM15)
    listDataDBM15 = db["M15"].find_one({}, sort=[('ctm', -1)])
    await insertData(db["M15"], dataM15Download, listDataDBM15)

    # MAJ M05 ------------------------------------------------------------------------
    json_data_M05 = client.commandExecute('getChartRangeRequest', {
        "info": {"start": startTime - (6 * 60 * 1000), "end": endTime, "period": 5,
                 "symbol": symbol,
                 "ticks": 0}})
    dataM05 = json.dumps(json_data_M05)
    dataM05Download = json.loads(dataM05)
    listDataDBM05 = db["M05"].find_one({}, sort=[('ctm', -1)])
    newTime = await insertData(db["M05"], dataM05Download, listDataDBM05)

    return newTime


async def majDatAall(client, symbol, db):
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
    print("**************************************** mise à jour majDatAall ****************************************")
    try:

        # ctmRefStart = db["D"].find().sort("ctm", -1).skip(1).limit(1)
        endTime = int(round(time.time() * 1000)) + (6 * 60 * 1000)

        # MAJ DAY : 13 mois------------------------------------------------------------------------
        startTimeDay = int(round(time.time() * 1000)) - (60 * 60 * 24 * 30 * 13) * 1000
        arguments = {
            "info": {"start": startTimeDay, "end": endTime, "period": 1440,
                     "symbol": symbol,
                     "ticks": 0}}
        json_data_Day = client.commandExecute('getChartRangeRequest', arguments)
        dataDAY = json.dumps(json_data_Day)
        dataDAYDownload = json.loads(dataDAY)
        listDataDBDAY = db["D"].find_one({}, sort=[('ctm', -1)])
        await insertData(db["D"], dataDAYDownload, listDataDBDAY)

        # on recupere les 4 dernieres heures pour eviter de tt scanner afin que le traitement soit plus rapide
        ctmRefStart = db["H4"].find().sort("ctm", -1).skip(1).limit(1)
        start = 0
        countH4 = 0
        for n in ctmRefStart:
            startTime = n['ctm']
            start = n['ctm']
            countH4 = 1

        if countH4 == 0:
            startTime = int(round(time.time() * 1000)) - (60 * 60 * 24 * 30 * 13) * 1000

        # MAJ H4 : 13 mois max------------------------------------------------------------------------
        json_data_H4 = client.commandExecute('getChartRangeRequest', {
            "info": {"start": startTime, "end": endTime, "period": 240,
                     "symbol": symbol,
                     "ticks": 0}})
        data_H4 = json.dumps(json_data_H4)
        dataH4Download = json.loads(data_H4)
        listDataDB = db["H4"].find_one({}, sort=[('ctm', -1)])
        await insertData(db["H4"], dataH4Download, listDataDB)
        # MAJ H1 : 13 mois max------------------------------------------------------------------------
        if countH4 == 0:
            startTimeH1 = int(round(time.time() * 1000)) - (60 * 60 * 24 * 30 * 13) * 1000
        else:
            startTimeH1 = start

        json_data_H1 = client.commandExecute('getChartRangeRequest', {
            "info": {"start": startTimeH1, "end": endTime, "period": 60,
                     "symbol": symbol,
                     "ticks": 0}})
        data_H1 = json.dumps(json_data_H1)
        dataH1Download = json.loads(data_H1)
        listDataDB = db["H1"].find_one({}, sort=[('ctm', -1)])
        await insertData(db["H1"], dataH1Download, listDataDB)

        # MAJ 15 min ------------------------------------------------------------------------
        if countH4 == 0:
            startTimeM15 = int(round(time.time() * 1000)) - (60 * 60 * 24 * 30 * 15) * 1000
        else:
            startTimeM15 = start
        json_data_M15 = client.commandExecute('getChartRangeRequest', {
            "info": {"start": startTimeM15, "end": endTime, "period": 15,
                     "symbol": symbol,
                     "ticks": 0}})
        dataM15 = json.dumps(json_data_M15)
        dataM15Download = json.loads(dataM15)
        listDataDBM15 = db["M15"].find_one({}, sort=[('ctm', -1)])
        await insertData(db["M15"], dataM15Download, listDataDBM15)

        # MAJ Minute : 1 mois max------------------------------------------------------------------------
        if countH4 == 0:
            startTimeM01 = int(round(time.time() * 1000)) - (60 * 60 * 24 * 30) * 1000
        else:
            startTimeM01 = start
        json_data_M01 = client.commandExecute('getChartRangeRequest', {
            "info": {"start": startTimeM01, "end": endTime, "period": 1,
                     "symbol": symbol,
                     "ticks": 0}})
        dataM01 = json.dumps(json_data_M01)
        dataM01Download = json.loads(dataM01)
        listDataDBM01 = db["M01"].find_one({}, sort=[('ctm', -1)])
        await insertData(db["M01"], dataM01Download, listDataDBM01)

        # MAJ 5 min ------------------------------------------------------------------------
        if countH4 == 0:
            startTimeM05 = int(round(time.time() * 1000)) - (60 * 60 * 24 * 30) * 1000
        else:
            startTimeM05 = start
        json_data_M05 = client.commandExecute('getChartRangeRequest', {
            "info": {"start": startTimeM05, "end": endTime, "period": 5,
                     "symbol": symbol,
                     "ticks": 0}})
        dataM05 = json.dumps(json_data_M05)
        dataM05Download = json.loads(dataM05)
        listDataDBM05 = db["M05"].find_one({}, sort=[('ctm', -1)])
        newTime = await insertData(db["M05"], dataM05Download, listDataDBM05)
    except Exception as exc:
        print("le programe a déclenché une erreur")
        print("exception de mtype ", exc.__class__)
        print("message", exc)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)

    # on retourne le dernier temps "ctm" enregistré
    return newTime


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


def zoneSoutien2(close, zone):
    arrayT = sorted(zone)
    minimumPIP = 15
    supportDown = 0
    supportHigt = 0
    for v in arrayT:
        if v < close-minimumPIP:
            supportDown = v
        if v > close+minimumPIP:
            if supportHigt == 0:
                supportHigt = v
                # print("pîvot up calcul:", supportHigt)

    # print(supportDown, " / ", supportHigt)
    return supportDown, supportHigt


def subscribe(loginResponse):
    c = Command()
    ssid = loginResponse['streamSessionId']
    sclient = APIStreamClient(
        ssId=ssid,
        tickFun=c.procTickExample,
        tradeFun=c.procTradeExample,
        balanceFun=c.procBalanceExample,
        tradeStatusFun=c.procTradeStatusExample,
        profitFun=c.procProfitExample
    )
    sclient.subscribePrice("US100")
    sclient.subscribeProfits()
    sclient.subscribeTradeStatus()
    sclient.subscribeTrades()
    sclient.subscribeBalance()

    return sclient, c


async def main():
    client = APIClient()  # create & connect to RR socket
    loginResponse = client.identification()  # connect to RR socket, login
    # get ssId from login response
    ssid = loginResponse['streamSessionId']
    logger.info(str(loginResponse))

    # check if user logged in correctly
    if not loginResponse['status']:
        print('Login failed. Error code: {0}'.format(loginResponse['errorCode']))
        return

    try:
        sclient, c = subscribe(loginResponse)
        connection = MongoClient('localhost', 27017)
        db = connection[SYMBOL]
        dbStreaming = connection["STREAMING"]

        startTime = await majDatAall(client, SYMBOL, db)

        print("mise à jour des données : ", SYMBOL, " fini !")

        # # pivot##################################################################################################
        # print('mise à jour du pivot -------------------------')
        P = Pivot(SYMBOL, "D")
        PPF, R1F, R2F, R3F, S1F, S2F, S3F = await P.fibonacci()  # valeurs ok
        PPW, R1W, R2W, S1W, S2W = await P.woodie()  # valeurs ok
        PPC, R1C, R2C, R3C, R4C, S1C, S2C, S3C, S4C = await P.camarilla()  # valeurs ok
        R1D, S1D = await P.demark()  # valeurs ok

        zone = np.array([PPC, R1C, R2C, R3C, R4C, S1C, S2C, S3C, S4C, R1W, R2W, S1W, S2W, R1D, S1D])
        zone = np.sort(zone)
        print('zone :', zone)
        # exit(0)
        # print('calcul du Pivot fini')
        # print("----------------------------------------------")
        print("calcul de moyenne mobile")
        moyMobil_01_120 = MM(SYMBOL, "M01", 0)
        moyMobil_05_120 = MM(SYMBOL, "M05", 0)
        moyMobil_01_120.EMA(120)
        moyMobil_01_120.EMA(70)
        moyMobil_05_120.EMA(120)
        """
        moyMobil_01_120 = MM(SYMBOL, "M01", 0)
        moyMobil_01_120.EMA(45)
        moyMobil_01_120.EMA(70)
        moyMobil_01_120.EMA(120)
        #
        moyMobil_05_120 = MM(SYMBOL, "M05", 0)
        moyMobil_05_120.EMA(45)
        moyMobil_05_120.EMA(70)
        moyMobil_05_120.EMA(120)
        """
        ao05 = Awesome(SYMBOL, "M05")
        await ao05.calculAllCandles()
        ao01 = Awesome(SYMBOL, "M01")
        await ao01.calculAllCandles()

        o = Order(SYMBOL, dbStreaming, client)
        print("calcul fini")
        while True:
            ###################################################################################################
            balance = c.getBalance()
            if c.getBalance() == 0:
                resp = client.commandExecute('getMarginLevel')
                balance = resp["returnData"]["margin_free"]
            else:
                balance = balance["marginFree"]

            ####################################################################################################
            startTime = await majData(client, startTime, SYMBOL, db)
            ####################################################################################################
            moyMobil_01_120.EMA(120)
            moyMobil_01_120.EMA(70)
            moyMobil_05_120.EMA(120)
            # AO ###################################################################################
            await ao05.calculLastCandle(10)
            await ao01.calculLastCandle(10)
            # supertrend ###################################################################################
            spM05 = Supertrend(SYMBOL, "M05", 30, 5)
            superM05T0, superT1, superT2 = spM05.getST()
            superM05T0 = round(float(superM05T0), 2)
            spM01 = Supertrend(SYMBOL, "M01", 30, 12)
            superM01T0, superM01T1, superM01T2 = spM01.getST()
            superM05T0 = round(float(superM01T0), 2)
            ###############################################################################################################
            # order
            ###############################################################################################################
            tradeOpenDic = findopenOrder(client)
            tradeOpen = json.loads(json.dumps(tradeOpenDic))

            ###############################################################################################################
            # bougie
            ###############################################################################################################
            # minutes-------------------------------------------------------
            bougie0M01 = db["M01"].find({}, sort=[('ctm', -1)]).limit(1).skip(0)[0]
            bougie1M01 = db["M01"].find({}, sort=[('ctm', -1)]).limit(1).skip(1)[0]
            bougie2M01 = db["M01"].find({}, sort=[('ctm', -1)]).limit(1).skip(2)[0]
            bougieM05_1 = db["M05"].find({}, sort=[('ctm', -1)]).limit(1).skip(1)[0]


            # sma_01_120 = bougie1M01['SMA120']
            # supportDown, supportHight = zoneSoutien2(sma_01_120, zone)
            if c.getTick() is not None:
                print("trade :", c.getTrade() )
                print("trade status:", c.getTradeStatus() )
                if len(tradeOpen['returnData']) == 0:
                    tick = c.getTick()["ask"]
                    print(tick)
                    if bougie1M01["Awesome"] > bougie2M01["Awesome"]:
                        print("achat !!!!!!!!!!!!" , bougie1M01["Awesome"] ,">", bougie2M01["Awesome"])
                        supportDown, supportHight = zoneSoutien2(tick, zone)
                        support = supportDown
                        objectif = supportHight
                        price = tick

                        o.buyNow(support, objectif, round(price, 2), balance, VNL)

                    if bougie1M01["Awesome"] < bougie2M01["Awesome"]:
                        print("vente !!!!!!!!!!!!", bougie1M01["Awesome"] ,"<", bougie2M01["Awesome"])
                        supportDown, supportHight = zoneSoutien2(tick, zone)
                        support = supportHight
                        objectif = supportDown
                        price = tick
                        o.sellNow(support, objectif, round(price, 2), balance, VNL)
                    '''
                    if bougie1M01["close"] > PPW and \
                            bougie1M01["Awesome"] > bougie2M01["Awesome"] and \
                            bougie1M01["Awesome"] > 0.50:
                        supportDown, supportHight = zoneSoutien2(bougieM05_1['SMA120'], zone)
                        support = supportDown
                        objectif = supportHight
                        price = bougieM05_1['SMA120'] + SPREAD
                        o.buyLimit(support, objectif, round(price, 2), BALANCE["margin_free"])

                        
                    if bougieM05_1['close'] > bougieM05_1['SMA120']:
                        supportDown, supportHight = zoneSoutien2(bougieM05_1['SMA120'], zone)
                        support = supportDown
                        objectif = supportHight
                        price = bougieM05_1['SMA120'] + SPREAD
                        o.buyLimit(support, objectif, round(price, 2))

                    if bougieM05_1['close'] < bougieM05_1['SMA120']:
                        supportDown, supportHight = zoneSoutien2(sma_01_120, zone)
                        # TODO: deffinir l objectif selon le % souhaité et la volatilité
                        support = supportHight
                        objectif = supportDown
                        price = bougieM05_1['SMA120'] - SPREAD
                        o.sellLimit(support, objectif, round(price, 2))
                        '''
                else:
                    # print("un ordre existe")
                    for trade in tradeOpenDic['returnData']:
                        if TransactionSide.BUY_LIMIT == trade['cmd']:
                            support = supportDown
                            objectif = supportHight
                            price = bougieM05_1['SMA120'] + SPREAD
                            o.movebuyLimitWait(trade, support, objectif, round(price, 2), BALANCE["margin_free"])

                        if TransactionSide.SELL_LIMIT == trade['cmd']:
                            support = supportHight
                            objectif = supportDown
                            price = bougieM05_1['SMA120'] - SPREAD
                            o.moveSellLimitWait(trade, support, objectif, round(price, 2), BALANCE["margin_free"])

            time.sleep(5)

    except Exception as exc:
        print("le programe a déclenché une erreur")
        print("exception de mtype ", exc.__class__)
        print("message", exc)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)

        client.disconnect()
        exit(0)

    except OSError as err:
        print("OS error: {0}".format(err))
        client.disconnect()
        exit(0)

    client.disconnect()
    sclient.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
