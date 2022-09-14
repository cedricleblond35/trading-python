# -*- coding: utf-8 -*-
# python3 -m pip install pymongo==3.5.1
import json
import time
import os
import sys
import asyncio
import math as math
import numpy as np
import logging
from datetime import datetime
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

'''
Grace à lza liste des trade enregistrés ds la table trade
ex : 
{ 
    "_id" : ObjectId("62cec201e4feeb03898d9fec"), "cmd" : 3, "customComment" : "Vente limit", "expiration" : NumberLong("1657720849600"), 
    "offset" : 0, "price" : 11711.52, "sl" : 11682.49, "symbol" : "US100", "tp" : 0, "type" : 0, "volume" : 0.07, 
    "resp" : { "status" : true, "returnData" : { "order" : 404426012 } } 
}

Prendre l ensemble des trades pour stocker le details des trades ds la table : details
{
	"command": "getTradeRecords",
	"arguments": {
		"orders": [404426012, 7489841, ...]
	}
}
repnse
{
	"close_price": 1.3256,
	"close_time": null,
	"close_timeString": null,
	"closed": false,
	"cmd": 0,
	"comment": "Web Trader",
	"commission": 0.0,
	"customComment": "Some text",
	"digits": 4,
	"expiration": null,
	"expirationString": null,
	"margin_rate": 0.0,
	"offset": 0,
	"open_price": 1.4,
	"open_time": 1272380927000,
	"open_timeString": "Fri Jan 11 10:03:36 CET 2013",
	"order": 7497776,
	"order2": 1234567,
	"position": 1234567,
	"profit": -2196.44,
	"sl": 0.0,
	"storage": -4.46,
	"symbol": "EURUSD",
	"timestamp": 1272540251000,
	"tp": 0.0,
	"volume": 0.10
}









Strategie

Periode 5 min :
A) Acheter pivot Woodie si la EMA7 repasse au dessus de la ligne de soutien
B) Acheter 
    si EMa7 > EAM25 et Awesome > 20 (3 bars verte au dessus de 20)
    et  Prix a touché S2 de Woodie
: Position achat: EAM25  stop au plus bas des 10 derniers periodes si supertrend est ko sinon faire  avec super tr












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

# GE30 le cout d un pip = 25€ * 0.01 --------------------------
# PRICE = 6.95
# PIP = 0.01
SYMBOL = "US100"
VNL = 20
# SPREAD = 0.04

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


def updatePivot():
    time = datetime.now().time()
    if 6 > int(time.strftime("%H")) > 1:
        return True
    else:
        return False


async def insertData(collection, dataDownload, lastBougieDB):
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
                close = (value['open'] + value['close']) / 100.0
                high = (value['open'] + value['high']) / 100.0
                low = (value['open'] + value['low']) / 100.0
                pointMedian = round((high + low) / 2, 2)
                #print(value['ctm'] ,">", lastBougieDB['ctm'])
                if lastBougieDB is None or value['ctm'] > lastBougieDB['ctm']:
                    open = value['open'] / 100.0
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
        print("insertData a déclenché une erreur")
        print("exception de mtype ", exc.__class__)
        print("message", exc)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)



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
        lastBougie = db["D"].find_one({}, sort=[('ctm', -1)])
        startTime = int(round(time.time() * 1000)) - (60 * 60 * 24 * 30 * 13) * 1000
        if lastBougie is not None:
            startTime = lastBougie["ctm"] - (60 * 60 * 24 ) * 1000

        json_data_Day = client.commandExecute(
            'getChartRangeRequest',
            {"info": {"start": startTime, "end": endTime, "period": 1440, "symbol": symbol, "ticks": 0}})
        dataDAY = json.dumps(json_data_Day)
        dataDAYDownload = json.loads(dataDAY)
        await insertData(db["D"], dataDAYDownload, lastBougie)

        # MAJ H4 : 13 mois max------------------------------------------------------------------------
        lastBougie = db["H4"].find_one({}, sort=[('ctm', -1)])
        startTime = int(round(time.time() * 1000)) - (60 * 60 * 24 * 30 * 13) * 1000
        if lastBougie is not None:
            startTime = lastBougie["ctm"] - (60 * 60 * 8 ) * 1000

        json_data_H4 = client.commandExecute('getChartRangeRequest', {
            "info": {"start": startTime, "end": endTime, "period": 240,
                     "symbol": symbol,
                     "ticks": 0}})
        data_H4 = json.dumps(json_data_H4)
        dataH4Download = json.loads(data_H4)
        await insertData(db["H4"], dataH4Download, lastBougie)

        # MAJ Minute : 1 mois max------------------------------------------------------------------------
        lastBougie = db["M01"].find_one({}, sort=[('ctm', -1)])
        startTime = int(round(time.time() * 1000)) - (60 * 60 * 24) * 1000
        if lastBougie is not None:
            startTime = lastBougie["ctm"] - (60 * 2) * 1000

        json_data_M01 = client.commandExecute('getChartRangeRequest', {
            "info": {"start": startTime, "end": endTime, "period": 1,
                     "symbol": symbol,
                     "ticks": 0}})
        dataM01 = json.dumps(json_data_M01)
        dataDownload = json.loads(dataM01)

        await insertData(db["M01"], dataDownload, lastBougie)

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

        await insertData(db["M05"], dataM05Download, lastBougie)

    except Exception as exc:
        print("majDatAall a déclenché une erreur")
        print("exception de mtype ", exc.__class__)
        print("message", exc)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)


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


def zoneResistanceVente(close, zone):
    arrayT = sorted(zone, reverse=True)
    resistance = 0
    for v in arrayT:
        if v < close and resistance == 0:
            resistance = v
    return resistance


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


async def pivot():
    print('calcul pivot ')
    P = Pivot(SYMBOL, "D")
    # PPF, R1F, R2F, R3F, S1F, S2F, S3F = await P.fibonacci()  # valeurs ok
    R1D, S1D = await P.demark()  # valeurs ok

    PPW, R1W, R2W, S1W, S2W = await P.woodie()  # valeurs ok
    # PPC, R1C, R2C, R3C, R4C, S1C, S2C, S3C, S4C = await P.camarilla()  # valeurs ok
    zone = np.array([PPW, R1W, R2W, S1W, S2W, R1D, S1D])
    # zone = np.array([PPW, R1W, R2W, S1W, S2W])
    return np.sort(zone)


async def main():
    client = APIClient()  # create & connect to RR socket
    print(client)
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
        print("insert db")

        await majDatAall(client, SYMBOL, db)

        # # # pivot##################################################################################################
        zone = await pivot()
        #
        # # # moyen mobile ##################################################################################################
        moyMobil_01_120 = MM(SYMBOL, "M01", 0)
        moyMobil_05_120 = MM(SYMBOL, "M05", 0)
        await moyMobil_01_120.EMA(120)
        await moyMobil_01_120.EMA(70)
        await moyMobil_01_120.EMA(26)
        #
        await moyMobil_05_120.EMA(120)
        await moyMobil_05_120.EMA(70)
        await moyMobil_05_120.EMA(26)
        #
        # # Awesome ##################################################################################################
        ao05 = Awesome(SYMBOL, "M05")
        await ao05.calculAllCandles()
        ao01 = Awesome(SYMBOL, "M01")
        await ao01.calculAllCandles()
        #
        o = Order(SYMBOL, dbStreaming, client, db["trade"])
        # logger.info("mise à jour du start fini ")
        while True:
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            print(
                "*****************************************************************************************************")
            print("Current Time =", current_time)
            print("mise à jour des indicateurs : ", current_time, " -----------------------------------------------")
            # if updatePivot():
            #     zone = await pivot()
            #
            # print("pivot :", zone)
            # ####################################################################################################
            await majDatAall(client, SYMBOL, db)
            # ####################################################################################################
            await moyMobil_01_120.EMA(120)
            await moyMobil_01_120.EMA(70)
            await moyMobil_01_120.EMA(26)
            #
            await moyMobil_05_120.EMA(120)
            await moyMobil_05_120.EMA(70)
            await moyMobil_05_120.EMA(26)
            #
            # # AO ###################################################################################
            await ao05.calculLastCandle(10)
            await ao01.calculLastCandle(10)
            #
            # # supertrend ###################################################################################
            # # spM013012 = Supertrend(SYMBOL, "M01", 30, 12)
            # # superM013012T0, superM013012T1, superM013012T2 = spM013012.getST()
            spM05_1003 = Supertrend(SYMBOL, "M05", 10, 3)
            superM05_1003T0, superM05_1003T1, superM05_1003T2 = spM05_1003.getST()
            #
            spM01_1003 = Supertrend(SYMBOL, "M01", 10, 4)
            superM01_1003T0, superM01_1003T1, superM01_1003T2 = spM01_1003.getST()
            #
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            print("fin de la mise à jour ", current_time)
            #
            if c.getTick() is not None:
                print("go stategie ***************************************")
                #print("c.getTick() :", c.getTick())
                tick = c.getTick()["ask"]
                # print("tick :", tick)
                # print("c.getTrade() :", c.getTrade())

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
                bougie3M01 = db["M01"].find({}, sort=[('ctm', -1)]).limit(1).skip(3)[0]
                bougie4M01 = db["M01"].find({}, sort=[('ctm', -1)]).limit(1).skip(4)[0]
                bougie5M01 = db["M01"].find({}, sort=[('ctm', -1)]).limit(1).skip(5)[0]

                bougie0M05 = db["M05"].find({}, sort=[('ctm', -1)]).limit(1).skip(0)[0]
                bougie1M05 = db["M05"].find({}, sort=[('ctm', -1)]).limit(1).skip(1)[0]
                bougie2M05 = db["M05"].find({}, sort=[('ctm', -1)]).limit(1).skip(2)[0]
                bougie3M05 = db["M05"].find({}, sort=[('ctm', -1)]).limit(1).skip(3)[0]


                ###############################################################################################################
                # balance
                ###############################################################################################################
                balance = c.getBalance()
                if c.getBalance() == 0:
                    resp = client.commandExecute('getMarginLevel')
                    balance = resp["returnData"]["margin_free"]
                else:
                    balance = balance["marginFree"]

                ###############################################################################################################
                # ecart entre bougie
                ###############################################################################################################
                ecart = abs(round(bougie0M01["high"] - bougie0M01["low"], 2)) \
                        + abs(round(bougie1M01["high"] - bougie1M01["low"], 2)) \
                        + abs(round(bougie2M01["high"] - bougie2M01["low"], 2)) \
                        + abs(round(bougie3M01["high"] - bougie3M01["low"], 2)) \
                        + abs(round(bougie4M01["high"] - bougie2M01["low"], 2)) \
                        + abs(round(bougie5M01["high"] - bougie3M01["low"], 2))

                ###############################################################################################################
                # start order
                ###############################################################################################################
                print("recherche de type d ordre à executer : nouvel ordre ou move SL")
                if len(tradeOpen['returnData']) == 0:
                    ###############################################################################################################
                    # Aucun ordre
                    ###############################################################################################################
                    print("-- Aucun ordre   ***************************************")
                    print("demarrage de selection d une strategie")


                    if zone[0] < bougie3M05.get("EMA120") < bougie2M05.get("EMA120") < bougie1M05.get("EMA120") \
                            and bougie1M05.get("AW") > bougie2M05.get("AW") > bougie3M05.get("AW"):
                        ### strategie 1 ################################################################################
                        print("strategie 1***********************************************")
                        print("zone[0] ", zone[0], " EMA120:", bougie3M05.get("EMA120"), " < ",
                              bougie3M05.get("EMA120"),
                              " < ", bougie3M05.get("EMA120"))
                        print("AW ", bougie1M05.get("AW"), " > ", bougie2M05.get("AW"), " > ", bougie3M05.get("AW"))
                        sl = zoneSoutien(tick, zone)
                        print(sl)
                        print(sl[0])
                        tp = 0
                        price = bougie1M01.get("EMA120")
                        comment = "Achat : strategie 1"

                        o.buyLimit(sl[0], tp, price, balance, VNL, comment)

                    print("strategie 2")
                    print(bougie0M01["close"] ,">", superM01_1003T1 ,"and", bougie1M01.get("EMA26") ,">", bougie1M01.get("EMA120"))
                    if bougie0M01["close"] > superM01_1003T1 and bougie1M01.get("EMA26") > bougie1M01.get("EMA120"):
                        print("strategie 2 Achat ***********************************************")
                        sl = superM01_1003T1
                        tp = zoneResistance(tick, zone)
                        price = bougie1M01.get("EMA120")
                        dif = price - sl
                        if dif > 5:
                            comment = "Achat : strategie 2"
                            o.buyNow(sl, tp, price, balance, VNL, comment)

                    if bougie0M01["close"] < superM01_1003T1 and bougie1M01.get("EMA26") < bougie1M01.get("EMA120"):
                        print("strategie 2 Vente***********************************************")
                        sl = superM01_1003T1
                        tp = zoneResistanceVente(tick, zone)
                        price = bougie1M01.get("EMA120")
                        # l ecart doit avoir un minimum
                        dif = sl - price
                        if dif > 5:
                            comment = "Achat : strategie 2"
                            o.sellNow(sl, tp, price, balance, VNL, comment)

                    # elif bougie1M01.get("EMA26") and bougie1M01.get("EMA70") and bougie1M01.get(
                    #         "EMA120") and bougie1M05.get("EMA120"):
                    #     ######################## achat ###################################
                    #     if bougie1M01["EMA26"] > bougie1M01["EMA70"] > bougie1M01["EMA120"] > bougie2M01["EMA120"] \
                    #             and bougie1M01["EMA70"] > bougie2M01["EMA70"] \
                    #             and bougie1M01["EMA26"] > supportDown > bougie1M01["EMA120"] \
                    #             and bougie1M01["EMA26"] > superM05_1003T1 > superM05_1003T2:
                    #         support = supportDown - 15
                    #         objectif = supportHight - 5
                    #         # o.buyNow(support, objectif, round(price, 2), balance, VNL)
                    #         o.buyLimit(support, objectif, round(supportDown, 2), balance, VNL)
                    #
                    #
                    #     ######################## vente ###################################
                    #     if bougie1M01["EMA120"] > bougie1M01["EMA70"] > bougie1M01["EMA26"] \
                    #             and bougie1M01["EMA70"] < bougie2M01["EMA70"] \
                    #             and bougie2M01["EMA120"] > bougie1M01["EMA120"] > supportHight > bougie1M01["EMA26"] \
                    #             and bougie1M01["EMA26"] < superM05_1003T1 \
                    #             and superM05_1003T1 > superM05_1003T2:
                    #         support = supportHight + 15
                    #         objectif = supportDown + 5
                    #         # o.sellNow(support, objectif, round(price, 2), balance, VNL)
                    #         o.sellLimit(support, objectif, round(supportHight, 2), balance, VNL)
                    #
                    # print("tick :", tick, " ema120", bougie1M01["EMA120"], "superM05_1003T0:", superM05_1003T0)
                    # print("zone 0 :", zone[0])
                    # '''
                    # Strategie EMA:
                    #     Ouverture d ordre au niveau : suivre la EMA120 de 5 min
                    #     SL : superM05_1003T1
                    #     tack profit : infini
                    # '''
                    # print("stragegie EMA :")
                    # print("sell ???? :",tick ,"<", superM01_1003T1 ,"<=", superM01_1003T2 ,"and", tick ,"<", superM01_1003T0 ,"and", tick ,"<", bougie1M01["EMA120"] ,"<", superM05_1003T1 ,"and", bougie1M05["EMA250"] ,"<", zone[0])
                    #
                    # if tick > superM05_1003T1 >= superM05_1003T2:
                    #     print("Achat level 1")
                    #     if tick > superM05_1003T0:
                    #         print("Achat level 2")
                    #         if tick > bougie1M01["EMA120"] > superM05_1003T1:
                    #             print("Achat level 3")
                    #             if bougie1M01["EMA120"] > zone[0]:
                    #                 print("Achat level 4")
                    #                 if bougie1M01["EMA120"] > bougie2M01["EMA120"]:
                    #                     print("Achat level 5")
                    #                     if bougie1M01["EMA70"] > bougie1M01["EMA120"]:
                    #                         print("Achat level 6")
                    #
                    # print("buy ???? :", tick, ">", superM05_1003T1, ">=", superM05_1003T2, "and", tick, ">",
                    #       superM05_1003T0, "and", tick, ">", bougie1M01["EMA120"], ">", superM05_1003T1, "and",
                    #       bougie1M05["EMA250"], "<", zone[0])
                    # if tick < superM01_1003T1 <= superM01_1003T2 and tick < superM01_1003T0 \
                    #         and tick < bougie1M01["EMA120"] < superM05_1003T1 and bougie1M05["EMA250"] < zone[0]:
                    #     # vente limit *************************************************************************************
                    #     sl = superM05_1003T1
                    #     tp = 0
                    #     o.sellLimit(sl, tp, bougie1M01["EMA120"], balance, VNL)
                    #
                    # elif tick > superM05_1003T1 >= superM05_1003T2 and tick > superM05_1003T0 \
                    #         and tick > bougie1M01["EMA120"] > superM05_1003T1 and bougie1M01["EMA120"] > zone[0] and bougie1M01["EMA120"] > bougie2M01["EMA120"] and bougie1M01["EMA70"] > bougie0M01["EMA120"]:
                    #
                    #     # Achat limit *************************************************************************************
                    #     if superM05_1003T1 < bougie0M05["EMA120"]:
                    #         sl = superM05_1003T1
                    #     else:
                    #         sl = bougie0M05["EMA120"]
                    #
                    #     tp = 0
                    #     price = bougie1M01["EMA120"]
                    #     resistance = zoneResistance(price, zone)
                    #
                    #     ecartStop = price - sl
                    #     ecartResistance = resistance - price
                    #     if ecartResistance > ecartStop*2.5 :
                    #         o.buyLimit(sl, tp, price, balance, VNL)

                    # elif bougie1M01.get("EMA70") and bougie1M01.get("AW") and bougie1M01.get(
                    #         "EMA70") and bougie1M05.get("EMA120") :
                    #     ######################## achat ###################################
                    #     if tick > superM01_1003T1 >= superM01_1003T2 and bougie1M01["EMA70"] > bougie1M01["EMA120"] \
                    #             and tick > superM05_1003T0:
                    #         sl = superM01_1003T1-4
                    #         tp = 0
                    #         o.buyNow(sl, tp, tick, balance, VNL)
                    #     ######################## vente ###################################
                    #     elif tick < superM01_1003T1 <= superM01_1003T2 and bougie1M01["EMA70"] < bougie1M01["EMA120"] \
                    #             and tick < superM05_1003T0:
                    #         sl = superM01_1003T1 + 4
                    #         tp = 0
                    #         o.sellNow(sl, tp, tick, balance, VNL)
                else:
                    print("ordre en cours ...........................................")
                    for trade in tradeOpenDic['returnData']:
                        print(trade)
                        print("c.getProfit(): ", c.getProfit())
                        print("trade['customComment'] :", trade['customComment'])
                        print("bougie0M05['AW'] :", bougie0M05)
                        #############" ordre en attente ##################"
                        if TransactionSide.BUY_LIMIT == trade['cmd']:
                            print("move price buy !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                            sl = superM01_1003T1
                            tp = 0
                            o.movebuyLimitWait(trade, sl, tp, bougie1M01["EMA120"], balance, VNL)

                        elif TransactionSide.SELL_LIMIT == trade['cmd']:

                            print("move price dell !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                            sl = superM01_1003T1
                            tp = 0
                            o.moveSellLimitWait(trade, sl, tp, bougie1M01["EMA120"], balance, VNL)

                        #############" ordre execute ##################"
                        elif TransactionSide.BUY == trade['cmd']:
                            if trade['customComment'] == "Achat direct":
                                if superM01_1003T1 > trade['sl']:
                                    o.moveStopBuy(trade, superM01_1003T1, tick)

                            else:
                                # Pour garantir pas de perte : monter le stop  a 5pip de benef :
                                #   Si cours en dessus de l ouverture avec ecart 20pip
                                #   Et si AW change de tendance

                                # Si il touche une resistance et AW change de tendance, monter le stop  au ST01 ?? A FAIRE ???????
                                if trade['sl'] < trade['open_price'] and tick > trade['open_price'] + 20 and bougie0M05[
                                    'AW'] < bougie1M05['AW']:
                                    sl = trade['open_price'] + 5
                                    o.moveStopBuy(trade, sl, tick)
                                else:
                                    sl = round(superM01_1003T1 - ecart / 4, 2)
                                    print("sl superM01_1003T1:", sl)
                                    o.moveStopBuy(trade, sl, tick)

                        elif TransactionSide.SELL == trade['cmd']:
                            print("trade['customComment'] :", trade['customComment'])
                            if trade['customComment'] == "Vente direct":
                                if trade['sl'] > superM05_1003T1:
                                    o.moveStopSell(trade, superM05_1003T1, tick)
                            else:
                                # descendre le stop  a 5pip de benef :
                                #   Si cours en dessous de l ouverture avec ecart 20pip
                                #   Et si AW change de tendance
                                if trade['sl'] > trade['open_price'] and tick < trade['open_price'] - 20 and bougie0M05[
                                    'AW'] > \
                                        bougie1M05['AW']:
                                    sl = trade['open_price'] - 5
                                    o.moveStopSell(trade, sl, tick)
                                else:
                                    print("vente direct ok : sl :", superM05_1003T1)
                                    sl = round(superM05_1003T1 + ecart / 4, 2)
                                    o.moveStopSell(trade, sl, tick)

                    print("ordre en cours   END...........................................")
            time.sleep(2)

    except Exception as exc:
        logger.info("le programe a déclenché une erreur xApiconnector_US100")
        logger.info("exception de mtype ", exc.__class__)
        logger.info("message", exc)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logger.info(exc_type, fname, exc_tb.tb_lineno)

        client.disconnect()
        exit(0)

    except OSError as err:
        logger.info("OS error: {0}".format(err))
        client.disconnect()
        exit(0)

    client.disconnect()
    sclient.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
