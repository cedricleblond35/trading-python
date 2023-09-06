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

from Configuration.Log import Log

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
        dataM01 = json.dumps(json_data_M01)
        dataDownload = json.loads(dataM01)
        print("maj M01 FINI")

        await insertData(logger, email, db["M01"], dataDownload, lastBougie)

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

async def pivot():
    P = Pivot(SYMBOL, "D")
    PPF, R1F, R2F, R3F, S1F, S2F, S3F = await P.fibonacci()  # valeurs ok
    R1D, S1D = await P.demark()  # valeurs ok
    PPW, R1W, R2W, S1W, S2W = await P.woodie()  # valeurs ok
    # PPC, R1C, R2C, R3C, R4C, S1C, S2C, S3C, S4C = await P.camarilla()  # valeurs ok
    zone = np.array([R1W, R2W, S1W, S2W, R1D, S1D, PPF, R1F, R2F, R3F, S1F, S2F, S3F])
    return np.sort(zone)

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

async def ema30_st15(logger, o, tick, spM15_1006T0, spM15_1006T1, balance, tradeOpen, tradeOpenDic, bougie0M15):
    try:
        orderExist = False
        # move order
        if len(tradeOpen['returnData']) > 0:
            for trade in tradeOpenDic['returnData']:
                print("trade['customComment']:", trade['customComment'])
                print("trade['cmd']:", trade['cmd'])
                if TransactionSide.BUY_LIMIT == trade['cmd'] and trade['customComment'] == "ema30_st15":
                    orderExist = True
                    sl = spM15_1006T0
                    tp = 0
                    price = bougie0M15.get("EMA30")
                    o.movebuyLimitWait(trade, sl, tp, price, balance, VNL)
                elif TransactionSide.BUY == trade['cmd'] and trade['customComment'] == "ema30_st15":
                    orderExist = True
                    if trade['sl'] < spM15_1006T0 < tick:
                        o.moveStopBuy(trade, spM15_1006T0, tick)
                elif TransactionSide.SELL_LIMIT == trade['cmd'] and trade['customComment'] == "ema30_st15":
                    orderExist = True
                    sl = spM15_1006T0
                    price = bougie0M15.get("EMA30")
                    tp = 0
                    o.moveSellLimitWait(trade, sl, tp, price, balance, VNL)
                elif TransactionSide.SELL == trade['cmd'] and trade['customComment'] == "ema30_st15":
                    orderExist = True
                    if trade['sl'] > spM15_1006T0 > tick:
                        o.moveStopBuy(trade, spM15_1006T0, tick)

        if orderExist is False:
            if tick > bougie0M15.get("EMA30") > spM15_1006T0:
                sl = spM15_1006T0
                tp = 0
                price = bougie0M15.get("EMA30")
                o.buyLimit(sl, tp, price, balance, VNL, "ema30_st15")
            elif tick < bougie0M15.get("EMA30") < spM15_1006T0:
                sl = spM15_1006T0
                tp = 0
                price = bougie0M15.get("EMA30")
                o.sellLimit(sl, tp, price, balance, VNL, "ema30_st15")

    except Exception as exc:
        logger.warning(exc)

async def ema_st(logger, o, tick, spM01_4005T1, balance, tradeOpen, tradeOpenDic, bougie1M01):
    try:
        orderExist = False
        # move order
        print("------------- ema_st --------------------------")
        if len(tradeOpen['returnData']) > 0:
            for trade in tradeOpenDic['returnData']:
                print("trade['customComment']:", trade['customComment'])
                print("trade['cmd']:", trade['cmd'])
                if TransactionSide.BUY_LIMIT == trade['cmd'] and trade['customComment'] == "ema_st":
                    orderExist = True
                    sl = spM01_4005T1
                    price = bougie1M01.get("EMA40")
                    tp = 0
                    o.movebuyLimitWait(trade, sl, tp, price, balance, VNL)
                elif TransactionSide.BUY == trade['cmd'] and trade['customComment'] == "ema_st":
                    orderExist = True
                    if trade['sl'] < spM01_4005T1 < tick:
                        o.moveStopBuy(trade, spM01_4005T1, tick)
                elif TransactionSide.SELL_LIMIT == trade['cmd'] and trade['customComment'] == "ema_st":
                    orderExist = True
                    sl = spM01_4005T1
                    price = bougie1M01.get("EMA40")
                    tp = 0
                    o.moveSellLimitWait(trade, sl, tp, price, balance, VNL)
                elif TransactionSide.SELL == trade['cmd'] and trade['customComment'] == "ema_st":
                    orderExist = True
                    if trade['sl'] > spM01_4005T1 > tick:
                        o.moveStopBuy(trade, spM01_4005T1, tick)

        if orderExist is False:
            print("ema40:", bougie1M01.get("EMA40"))
            print("ema200:", bougie1M01.get("EMA200"))
            print("spM01_4005T1:", spM01_4005T1)
            if tick > bougie1M01.get("EMA40") > bougie1M01.get("EMA200") > spM01_4005T1:
                sl = spM01_4005T1
                print("SL:", sl)
                tp = 0
                price = round(bougie1M01.get("EMA40"), ARRONDI_INDIC)
                o.buyLimit(sl, tp, price, balance, VNL, "ema_st")
            elif tick < bougie1M01.get("EMA40") < bougie1M01.get("EMA200") and tick < spM01_4005T1:
                sl = spM01_4005T1

                print("SL:", sl)
                tp = 0
                price = round(bougie1M01.get("EMA40"), ARRONDI_INDIC)
                o.sellLimit(sl, tp, price, balance, VNL, "ema_st")

        print("------------- ema_st end --------------------------")
    except Exception as exc:
        logger.warning(exc)

async def AW_pivot_st1004(logger, o, tick, spM05_1003T0, spM01_1005T0,
                          balance, tradeOpen, tradeOpenDic, bougie1M05, bougie0M05, bougie1M01, bougie2M01):
    try:
        orderExist = False
        # move order
        if len(tradeOpen['returnData']) > 0:
            for trade in tradeOpenDic['returnData']:
                print("trade['customComment']:", trade['customComment'])
                print("trade['cmd']:", trade['cmd'])
                if TransactionSide.BUY == trade['cmd'] and trade['customComment'] == "AW_pivot_st1004":
                    orderExist = True
                    print("ordre en cours :", trade['customComment'])
                    # Pour garantir pas de perte : monter le stop  a 5pip de benef :
                    #   Si cours en dessus de l ouverture avec ecart 20pip
                    #   Et si AW change de tendance
                    # Si il touche une resistance et AW change de tendance, monter le stop  au ST01 ?? A FAIRE ???????
                    if trade['sl'] < trade['open_price'] and tick > trade['open_price'] + 25 and \
                            bougie1M01['AW'] < bougie2M01['AW']:
                        sl = trade['open_price'] + 2
                        o.moveStopBuy(trade, sl, tick)

                    elif bougie1M05.get("AW") > 20 and trade['sl'] < spM01_1005T0 < tick:
                        o.moveStopBuy(trade, spM01_1005T0, tick)
                    elif bougie1M05.get("AW") < 20 and trade['sl'] < spM05_1003T0 < tick:
                        o.moveStopBuy(trade, spM05_1003T0, tick)

                elif TransactionSide.SELL == trade['cmd'] and trade['customComment'] == "AW_pivot_st1004":
                    orderExist = True
                    # descendre le stop  a 5pip de benef :
                    #   Si cours en dessous de l ouverture avec ecart 20pip
                    #   Et si AW change de tendance
                    if trade['sl'] > trade['open_price'] and tick < trade['open_price'] - 25 and \
                            bougie1M01['AW'] < bougie2M01['AW']:
                        sl = trade['open_price'] - 2
                        o.moveStopSell(trade, sl, tick)

                    elif bougie1M05.get("AW") > -20 and trade['sl'] > spM01_1005T0 > tick:
                        o.moveStopSell(trade, spM01_1005T0, tick)
                    elif bougie1M05.get("AW") < -20 and trade['sl'] > spM05_1003T0 > tick:
                        o.moveStopSell(trade, spM05_1003T0, tick)

        if orderExist is False:
            print("-- Aucun ordre  AW_pivot_st1004 ********************")
            print("-- bougie1M01.get(AW) :", bougie0M05.get("AW"))
            print("-- bougie2M01.get(AW) :", bougie1M05.get("AW"))
            print("-- Aucun ordre  AW_pivot_st1004 ********************")
            if tick > spM01_1005T0 and bougie1M01.get("close") > spM01_1005T0 and bougie0M05.get(
                    "close") > spM05_1003T0 and tick > spM05_1003T0 and bougie1M01.get("AW") > bougie2M01.get("AW"):
                sl = spM05_1003T0 - 2
                tp = 0
                price = tick + 10
                o.buyNow(sl, tp, price, balance, VNL, "AW_pivot_st1004")

            elif tick < spM01_1005T0 and bougie1M01.get("close") < spM01_1005T0 and bougie0M05.get(
                    "close") < spM05_1003T0 and tick < spM05_1003T0 and bougie1M01.get("AW") < bougie2M01.get("AW"):
                sl = spM05_1003T0 + 2
                tp = 0
                price = tick - 10
                o.sellNow(sl, tp, price, balance, VNL, "AW_pivot_st1004")
    except Exception as exc:
        logger.warning(exc)

async def main():
    l = Log()
    logger = l.getLogger()
    email = Email()

    order = []
    try:
        sclient, c, client = await connectionAPI(logger)
        connection = MongoClient('localhost', 27017)
        db = connection[SYMBOL]
        dbStreaming = connection["STREAMING"]

        await majDatAall(logger, email, client, SYMBOL, db)

        # # # moyen mobile ##################################################################################################
        moyMobil_05 = MM(SYMBOL, "M05", 0)
        moyMobil_01 = MM(SYMBOL, "M01", 0)
        moyMobil_15 = MM(SYMBOL, "M15", 0)

        # # Awesome ##################################################################################################
        """
        ao05 = Awesome(SYMBOL, "M05", ARRONDI_INDIC)
        await ao05.calculAllCandles()
        #
        o = Order(SYMBOL, dbStreaming, client, db["trade"])
        """
        while True:
            print(
                "*****************************************************************************************************")
            ############### gestion des jours et heures de trading ##########################""
            j = datetime.today().weekday()  # 0:lundi ; 4 vendredi
            today = datetime.now()
            todayPlus2Hours = today + timedelta(hours=2)
            print("mise à jour :", todayPlus2Hours)

            if client.is_socket_closed():
                logger.info("!!!!!!!!! client deconnecté, reconnection en cours !!!!!!!!!!!!!!!!!!!")
                sclient, c, client = connectionAPI(logger)

            c.getTick()

            candles = c.getCandles()
            print("=================> candles:", candles)
            # ####################################################################################################
            await majDatAall(logger, email, client, SYMBOL, db)
            # ####################################################################################################
            """
            await moyMobil_05.EMA(70, ARRONDI_INDIC)
            await moyMobil_05.SMMA(200, ARRONDI_INDIC)

            await moyMobil_01.SMMA(200, ARRONDI_INDIC)
            await moyMobil_01.EMA(40, ARRONDI_INDIC)
            await moyMobil_01.EMA(70, ARRONDI_INDIC)
            await moyMobil_01.EMA(200, ARRONDI_INDIC)

            await moyMobil_15.EMA(30, ARRONDI_INDIC)

            await moyMobil_01.EMA(26, ARRONDI_INDIC)
            # # Awesome ##################################################################################################
            ao05 = Awesome(SYMBOL, "M05", ARRONDI_INDIC)
            await ao05.calculAllCandles()
            #
            zone = await pivot()
            """
            # # AO ###################################################################################
            #await ao05.calculLastCandle(10)
            #
            # # supertrend ###################################################################################
            """
            spM05_1003 = Supertrend(SYMBOL, "M05", 10, 3, ARRONDI_INDIC)
            superM05_1003T0, superM05_1003T1, superM05_1003T2 = spM05_1003.getST()

            spM01_1005 = Supertrend(SYMBOL, "M01", 10, 5, ARRONDI_INDIC)
            spM01_1005T0, spM01_1005T1, spM01_1005T2 = spM01_1005.getST()

            spM01_4005 = Supertrend(SYMBOL, "M01",30, 5, ARRONDI_INDIC)
            spM01_4005T0, spM01_4005T1, spM01_4005T2 = spM01_4005.getST()
            print("***spM01_4005T1:", spM01_4005T1)

            spM15_1006 = Supertrend(SYMBOL, "M15",10, 6, ARRONDI_INDIC)
            spM15_1006T0, spM15_1006T1, spM15_1006T2 = spM15_1006.getST()

            """
            if c.getTick() is not None:
                print("jour:", j, " h:", todayPlus2Hours.hour)
                if 0 <= j < 5 and 2 < todayPlus2Hours.hour < 22:
                    """
                    print("Horaire de Trading ok")
                    tick = c.getTick()["ask"]

                    ###############################################################################################################
                    # order
                    ###############################################################################################################
                    tradeOpenDic = findopenOrder(client)
                    tradeOpen = json.loads(json.dumps(tradeOpenDic))

                    print("tradeOpen:", tradeOpen)
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

                    bougie0M15 = db["M15"].find({}, sort=[('ctm', -1)]).limit(1).skip(0)[0]

                    ###############################################################################################################
                    # balance
                    ###############################################################################################################
                    
                    balance = c.getBalance()
                    if c.getBalance() == 0:
                        resp = client.commandExecute('getMarginLevel')
                        balance = resp["returnData"]["margin_free"]
                    else:
                        balance = balance["marginFree"]

                    print("balance:", balance)
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
                    print("tick:", tick)

                    print("smma200 M1:", bougie1M01.get("SMMA200"))
                    print("--------------------------------------")
                    print("smma200 M1:", bougie1M01.get("SMMA200"))
                    print("superM05_1003T1:", superM05_1003T1)
                    print("--------------------------------------")
                    print("ema70 M1", bougie1M01.get("EMA70"))
                    print("smma200 M1:", bougie1M01.get("SMMA200"))
                    print("--------------------------------------")
                    print("tradeOpen", tradeOpen['returnData'])
                    if len(tradeOpen['returnData']) > 0:
                        for trade in tradeOpenDic['returnData']:
                            order.append(trade['customComment'])

                    print("ordre en cours:", len(tradeOpen['returnData']))
                    print("stategie start ----")
                    # await SMMA200_M1_EMA70(o, tick, bougie1M01, superM05_1003T1, zone, balance, tradeOpen, tradeOpenDic, bougie0M05, bougie1M05)

                    #await AW_pivot_st1004(logger, o, tick, superM05_1003T0, spM01_1005T0, balance, tradeOpen, tradeOpenDic, bougie1M05, bougie0M05, bougie1M01,                            bougie2M01)

                    await ema_st(logger, o, tick, spM01_4005T1, balance, tradeOpen, tradeOpenDic, bougie1M01)

                    #await ema30_st15(logger, o, tick, spM15_1006T0, spM15_1006T1, balance, tradeOpen, tradeOpenDic, bougie0M15)
                    """
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
