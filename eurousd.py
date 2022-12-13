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
SYMBOL = "EURUSD"
VNL = 25


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
                close = (value['open'] + value['close']) / 100000.0
                high = (value['open'] + value['high']) / 100000.0
                low = (value['open'] + value['low']) / 100000.0
                pointMedian = round((high + low) / 2, 2)
                #print(value['ctm'] ,">", lastBougieDB['ctm'])
                if lastBougieDB is None or value['ctm'] > lastBougieDB['ctm']:
                    open = value['open'] / 100000.0
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
    #print("**************************************** mise à jour majDatAall ****************************************")
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
    PPF, R1F, R2F, R3F, S1F, S2F, S3F = await P.fibonacci()  # valeurs ok
    R1D, S1D = await P.demark()  # valeurs ok
    PPW,R1W, R2W, S1W, S2W = await P.woodie()  # valeurs ok
    #PPC, R1C, R2C, R3C, R4C, S1C, S2C, S3C, S4C = await P.camarilla()  # valeurs ok
    #zone = np.array([R1W, R2W, S1W, S2W, R1D, S1D, PPF, R1F, R2F, R3F, S1F, S2F, S3F, PPC, R1C, R2C, R3C, R4C, S1C, S2C, S3C, S4C])
    zone = np.array(
        [R1W, R2W, S1W, S2W, R1D, S1D, PPF, R1F, R2F, R3F, S1F, S2F, S3F])
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
        moyMobil_05_120 = MM(SYMBOL, "M05", 0)

        await moyMobil_05_120.EMA(120, 5)
        await moyMobil_05_120.EMA(70, 5)
        await moyMobil_05_120.EMA(40, 5)
        #
        # # Awesome ##################################################################################################
        ao05 = Awesome(SYMBOL, "M05")
        await ao05.calculAllCandles()
        #
        o = Order(SYMBOL, dbStreaming, client, db["trade"])
        # logger.info("mise à jour du start fini ")

        while True:
            ############### gestion des jours et heures de trading ##########################""
            j = datetime.today().weekday() #0:lundi ; 4 vendredi
            today = datetime.now()
            todayPlus2Hours = today + timedelta(hours=2)
            if 0 <= j < 5 and 2 < todayPlus2Hours.hour < 22:
                ############### calcul des indicateurs ##########################""
                current_time = today.strftime("%H:%M:%S")
                print(
                    "*****************************************************************************************************")
                print("Current Time =", current_time)
                print("mise à jour des indicateurs : ", current_time, " -----------------------------------------------")
                if updatePivot():
                     zone = await pivot()
                #
                print("pivot :", zone)
                # ####################################################################################################
                await majDatAall(client, SYMBOL, db)
                # ####################################################################################################
                #
                await moyMobil_05_120.EMA(120, 5)
                await moyMobil_05_120.EMA(70, 5)
                await moyMobil_05_120.EMA(40, 5)
                #
                # # AO ###################################################################################
                await ao05.calculLastCandle(10)
                #
                # # supertrend ###################################################################################
                spM05 = Supertrend(SYMBOL, "M05", 15, 6, 5)
                superM05T0, superM05t1, superM05T2 = spM05.getST()
                #
                now = datetime.now()
                current_time = now.strftime("%H:%M:%S")
                print("Mise à jour ", current_time)
                #
                if c.getTick() is not None:
                    tick = c.getTick()["ask"]

                    ###############################################################################################################
                    # order
                    ###############################################################################################################
                    tradeOpenDic = findopenOrder(client)
                    tradeOpen = json.loads(json.dumps(tradeOpenDic))

                    ###############################################################################################################
                    # bougie
                    ###############################################################################################################
                    # minutes-------------------------------------------------------
                    bougie0M05 = db["M05"].find({}, sort=[('ctm', -1)]).limit(1).skip(0)[0]
                    bougie1M05 = db["M05"].find({}, sort=[('ctm', -1)]).limit(1).skip(1)[0]
                    bougie2M05 = db["M05"].find({}, sort=[('ctm', -1)]).limit(1).skip(2)[0]
                    bougie3M05 = db["M05"].find({}, sort=[('ctm', -1)]).limit(1).skip(3)[0]
                    bougie4M05 = db["M05"].find({}, sort=[('ctm', -1)]).limit(1).skip(3)[0]
                    bougie5M05 = db["M05"].find({}, sort=[('ctm', -1)]).limit(1).skip(3)[0]


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
                    ecart = abs(round(bougie0M05["high"] - bougie0M05["low"], 2)) \
                            + abs(round(bougie1M05["high"] - bougie1M05["low"], 2)) \
                            + abs(round(bougie2M05["high"] - bougie2M05["low"], 2)) \
                            + abs(round(bougie3M05["high"] - bougie3M05["low"], 2)) \
                            + abs(round(bougie4M05["high"] - bougie2M05["low"], 2)) \
                            + abs(round(bougie5M05["high"] - bougie3M05["low"], 2))

                    ###############################################################################################################
                    # start order
                    ###############################################################################################################
                    if len(tradeOpen['returnData']) == 0:
                        ###############################################################################################################
                        # Aucun ordre
                        ###############################################################################################################
                        print("-- Aucun ordre   ***************************************")
                        print("demarrage de selection d une strategie")
                        print("mea 40 :", bougie1M05.get("EMA40"))
                        print("mea 70: ", bougie1M05.get("EMA70"))
                        print("superM05t1 :", superM05t1)

                        # strategie des achats et ventes des support
                        if bougie1M05.get("EMA40") is not None and bougie1M05.get("EMA70") is not None and superM05t1 is not None:
                            print("************ Analyse strategie 1 ***********************************************")
                            if superM05t1 < bougie0M05["close"] and bougie1M05.get("EMA70") < bougie0M05["close"]:
                                print("strategie 1 achat ***********************************************")
                                sl = superM05t1
                                tp = 0
                                price = bougie1M05.get("EMA70")
                                comment = "Achat buyLimit: strategie 1"
                                o.buyLimit(sl, tp, price, balance, VNL, comment)
                            elif superM05t1 > bougie0M05["close"] and bougie1M05.get("EMA70") > bougie0M05["close"]:
                                print("strategie 1 vente ***********************************************")
                                sl = superM05t1
                                tp = 0
                                price = bougie1M05.get("EMA70")
                                comment = "Achat sellLimit: strategie 1"
                                o.sellLimit(sl, tp, price, balance, VNL, comment)


                        # elif bougie1M01.get("AW") < bougie2M01.get("AW") < bougie3M01.get("AW") and bougie1M01.get("AW") \
                        #         and tick < bougie1M01.get("EMA26") < bougie1M01.get("EMA70") < bougie1M01.get("EMA120") \
                        #         and tick < superM01_1003T1:
                        #     sl = superM01_1003T1
                        #     tp = zoneResistanceVente(tick, zone)
                        #     price = tick - 15
                        #     # l ecart doit avoir un minimum
                        #     dif = sl - price
                        #     r = zoneResistanceVente(bougie1M01.get("close"), zone)
                        #     difR = price - r
                        #     if dif > 5 and difR > 15:
                        #         comment = "Vente direct : strategie 1"
                        #         o.sellNow(sl, tp, price, balance, VNL, comment)
                        #
                        # elif bougie0M01["close"] < superM01_1003T1 and bougie1M01.get("EMA26") < bougie1M01.get("EMA120"):
                        #     print("strategie 2 Vente***********************************************")
                        #     sl = superM01_1003T1
                        #     tp = zoneResistanceVente(tick, zone)
                        #     price = bougie1M01.get("EMA120")
                        #     # l ecart doit avoir un minimum
                        #     dif = sl - price
                        #     if dif > 5:
                        #         comment = "Vente direct: strategie 2"
                        #         o.sellNow(sl, tp, price, balance, VNL, comment)
                        #
                        ### strategie 1 ################################################################################
                        # elif zone[0] < bougie3M05.get("EMA120") < bougie2M05.get("EMA120") < bougie1M05.get("EMA120") \
                        #         and bougie1M05.get("AW") > bougie2M05.get("AW") > bougie3M05.get("AW"):
                        #     print("strategie 1***********************************************")
                        #     print("zone[0] ", zone[0], " EMA120:", bougie3M05.get("EMA120"), " < ",
                        #           bougie3M05.get("EMA120"),
                        #           " < ", bougie3M05.get("EMA120"))
                        #     print("AW ", bougie1M05.get("AW"), " > ", bougie2M05.get("AW"), " > ", bougie3M05.get("AW"))
                        #     #sl = zoneSoutien(tick, zone)
                        #     sl = superM01_1003T1
                        #     print(sl)
                        #     print(sl[0])
                        #     tp = 0
                        #     price = bougie1M01.get("EMA120")
                        #     comment = "Achat buyLimit: strategie 1"
                        #     o.buyLimit(sl[0], tp, price, balance, VNL, comment)
                        #
                        # ### strategie 2 ################################################################################
                        # elif bougie0M01["close"] > superM01_1003T1 and bougie1M01.get("EMA26") > bougie1M01.get("EMA120") and bougie1M05.get("AW") > 5:
                        #     print("strategie 2 Achat ***********************************************")
                        #     sl = superM01_1003T1
                        #     tp = zoneResistance(tick, zone)
                        #     price = bougie1M01.get("EMA120")
                        #     dif = price - sl
                        #     if dif > 5:
                        #         comment = "Achat limit : strategie 2"
                        #         o.buyLimit(sl, tp, price, balance, VNL, comment)
                        # elif bougie0M01["close"] < superM01_1003T1 and bougie1M01.get("EMA26") < bougie1M01.get("EMA120") and bougie1M05.get("AW") < -5:
                        #     print("strategie 2 Vente ***********************************************")
                        #     sl = superM01_1003T1
                        #     tp = zoneResistance(tick, zone)
                        #     price = bougie1M01.get("EMA120")
                        #     dif = abs(price - sl)
                        #     if dif > 5:
                        #         comment = "Achat limit : strategie 2"
                        #         o.sellLimit(sl, tp, price, balance, VNL, comment)



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
                            print(tick)
                            #############" ordre en attente #################################################################
                            if TransactionSide.BUY_LIMIT == trade['cmd']:
                                print(trade)
                                sl = superM05t1
                                tp = 0
                                price = bougie1M05.get("EMA70")
                                comment = "Achat buyLimit: strategie 1"
                                o.movebuyLimitWait(trade, sl, tp, price, balance, VNL)


                            elif TransactionSide.SELL_LIMIT == trade['cmd']:
                                sl = superM05t1
                                tp = 0
                                price = bougie1M05.get("EMA70")
                                o.moveSellLimitWait(trade, sl, tp, price, balance, VNL)

                            #o.delete(trade)





                            #############" ordre execute ###################################################################
                            elif TransactionSide.BUY == trade['cmd']:
                                if trade['customComment'] == "Achat direct":
                                    if superM05t1 > trade['sl']:
                                        o.moveStopBuy(trade, superM05t1, tick)

                                else:
                                    # Pour garantir pas de perte : monter le stop  a 5pip de benef :
                                    #   Si cours en dessus de l ouverture avec ecart 20pip
                                    #   Et si AW change de tendance

                                    # Si il touche une resistance et AW change de tendance, monter le stop  au ST01 ?? A FAIRE ???????
                                    if trade['sl'] < trade['open_price'] and tick > trade['open_price'] + 15 and bougie0M05[
                                        'AW'] < bougie1M05['AW']:
                                        sl = trade['open_price'] + 3
                                        o.moveStopBuy(trade, sl, tick)
                                    else:
                                        sl = round(superM05t1 - ecart / 4, 2)
                                        print("sl superM01_1003T1:", sl)
                                        o.moveStopBuy(trade, sl, tick)

                            elif TransactionSide.SELL == trade['cmd']:
                                print("trade['customComment'] :", trade['customComment'])

                                if trade['customComment'] == "Vente direct":
                                    print(trade['sl'] ,">", superM05t1)
                                    if trade['sl'] > superM05t1:
                                        o.moveStopSell(trade, superM05t1, tick)
                                else:
                                    # descendre le stop  a 5pip de benef :
                                    #   Si cours en dessous de l ouverture avec ecart 20pip
                                    #   Et si AW change de tendance
                                    if trade['sl'] > trade['open_price'] and tick < trade['open_price'] - 15 and bougie0M05[
                                        'AW'] > \
                                            bougie1M05['AW']:
                                        sl = trade['open_price'] - 3
                                        o.moveStopSell(trade, sl, tick)
                                    else:
                                        print("vente direct ok : sl :", superM05t1)
                                        sl = round(superM05t1 + ecart / 4, 2)
                                        o.moveStopSell(trade, sl, tick)

                        print("ordre en cours   END...........................................")
                time.sleep(30)

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
