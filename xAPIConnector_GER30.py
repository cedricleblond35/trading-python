# -*- coding: utf-8 -*-
# python3 -m pip install pymongo==3.5.1
import json
import time
import os
import sys
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

######## calcul de lots
# 10 pips 250€ pour 1 lots
# 1 pips 25€ pour 1 lots
#
# Valeur du contrat
# 15740 points * 25€ * 1 lot = 393 500€
#
# Levier de 20 max
# Marge : 393 500 € / 20 = 19675€
#
# exemple
# si on a un solde : 19436 €
# donc marge dispo : 19436 €
#
# 19436€ * 20 de levier = 388 720 €
# nbre de lot = 388 720 / 393500 € = 0,9878 lot


# horaire---------------
TradeStartTime = 4
TradeStopTime = 22
# gestion managment-----
Risk = 2.00  # risk %
ObjectfDay = 5.00  # %

BALANCE = 0
TICK = False
PROFIT = False
SYMBOL = "DE30"
VNL = 30


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
                close = (value['open'] + value['close']) / 10.0
                high = (value['open'] + value['high']) / 10.0
                low = (value['open'] + value['low']) / 10.0
                pointMedian = round((high + low) / 2, 2)
                # print(value['ctm'] ,">", lastBougieDB['ctm'])
                if lastBougieDB is None or value['ctm'] > lastBougieDB['ctm']:
                    open = value['open'] / 10.0
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

        # MAJ H4 : 13 mois max------------------------------------------------------------------------
        lastBougie = db["M15"].find_one({}, sort=[('ctm', -1)])
        startTime = int(round(time.time() * 1000)) - (60 * 60 * 24 * 45) * 1000
        if lastBougie is not None:
            startTime = lastBougie["ctm"] - (60 * 60 * 8) * 1000

        json_data_H4 = client.commandExecute('getChartRangeRequest', {
            "info": {"start": startTime, "end": endTime, "period": 15,
                     "symbol": symbol,
                     "ticks": 0}})
        data_H4 = json.dumps(json_data_H4)
        dataH4Download = json.loads(data_H4)
        await insertData(logger, email, db["H4"], dataH4Download, lastBougie)

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


async def SMMA200_M1_EMA70(o, tick, bougie1M01, superM05_5003T1, zone, balance, tradeOpen, tradeOpenDic, bougie0M05,
                           bougie1M05):
    if "SMMA200_M1&&EMA70" not in order:
        ###############################################################################################################
        # Aucun ordre
        ###############################################################################################################
        print("-- Aucun ordre   ***************************************")
        print("demarrage de selection d une strategie")
        diff_ST_SMMA200 = superM05_5003T1 - bougie1M01.get(
            "SMMA200")  # ecart entre le stop et overture doit etre > 5 pip
        diff = abs(diff_ST_SMMA200)
        print("diff_ST_SMMA200 : 30 > ", diff, " > 5")

        # strategie des achats et ventes des support
        # strategie: SMMA200_M1 Achat && EMA70
        if bougie1M01.get("SMMA200") is not None:
            if tick > bougie1M01.get("SMMA200") > superM05_5003T1 and bougie1M01.get(
                    "EMA70") > bougie1M01.get("SMMA200") and 30 > abs(diff_ST_SMMA200) > 5:
                print("strategie 1 de achat ***********************************************")
                sl = superM05_5003T1
                tp = round(zoneResistance(tick + 15, zone), 1)
                price = round(bougie1M01.get("SMMA200") + 2, 1)
                comment = "SMMA200_M1&&EMA70 Achat"
                # round(tp, 1)
                o.buyLimit(sl, tp, price, balance, VNL, comment)
            elif tick < bougie1M01.get("SMMA200") < superM05_5003T1 and bougie1M01.get(
                    "EMA70") < bougie1M01.get("SMMA200") and 30 > abs(diff_ST_SMMA200) > 5:
                print("strategie 1 de vente ***********************************************")

                print("*********tick:", tick)
                sl = superM05_5003T1
                tp = zoneResistanceVente(bougie1M01.get("SMMA200") - 15, zone)
                price = round(bougie1M01.get("SMMA200") - 2, 1)
                comment = "SMMA200_M1&&EMA70 vente"
                print("*********tp:", tp)
                o.sellLimit(sl, tp, price, balance, VNL, comment)

    # move order
    if len(tradeOpen['returnData']) > 0:
        for trade in tradeOpenDic['returnData']:
            print("ordre en cours :", trade['customComment'])
            #############" ordre en attente #################################################################
            if bougie1M01.get("SMMA200") is not None:
                diff_ST_SMMA200 = superM05_5003T1 - bougie1M01.get(
                    "SMMA200")  # ecart entre le stop et overture doit etre > 5 pip
                if TransactionSide.BUY_LIMIT == trade['cmd']:
                    print(trade)
                    if trade['customComment'] == "SMMA200_M1&&EMA70 Achat":
                        if superM05_5003T1 > bougie1M01.get("SMMA200") or 30 > abs(diff_ST_SMMA200) < 5:
                            o.delete(trade)

                        elif tick > bougie1M01.get("SMMA200"):
                            sl = superM05_5003T1
                            tp = round(zoneResistance(tick + 15, zone), 1)
                            price = round(bougie1M01.get("SMMA200"), 1) + 2
                            o.movebuyLimitWait(trade, sl, tp, price, balance, VNL)
                        elif tick > trade["tp"]:
                            o.delete(trade)
                elif TransactionSide.SELL_LIMIT == trade['cmd']:
                    if trade['customComment'] == "SMMA200_M1&&EMA70 vente":
                        if superM05_5003T1 < bougie1M01.get("SMMA200") or 30 > abs(diff_ST_SMMA200) < 5:
                            o.delete(trade)
                        elif tick < bougie1M01.get("SMMA200"):
                            sl = superM05_5003T1
                            tp = zoneResistanceVente(bougie1M01.get("SMMA200") - 15, zone)
                            price = round(bougie1M01.get("SMMA200"), 1) - 2
                            o.moveSellLimitWait(trade, sl, tp, price, balance, VNL)
                        elif tick < trade["tp"]:
                            o.delete(trade)

                #############" ordre execute ###################################################################
                elif TransactionSide.BUY == trade['cmd']:
                    if trade['customComment'] == "SMMA200_M1&&EMA70 Achat":
                        # Pour garantir pas de perte : monter le stop  a 5pip de benef :
                        #   Si cours en dessus de l ouverture avec ecart 20pip
                        #   Et si AW change de tendance

                        # Si il touche une resistance et AW change de tendance, monter le stop  au ST01 ?? A FAIRE ???????
                        if trade['sl'] < trade['open_price'] and tick > trade['open_price'] + 25 and \
                                bougie0M05['AW'] < bougie1M05['AW']:
                            sl = trade['open_price'] + 3
                            o.moveStopBuy(trade, sl, tick)

                        elif superM05_5003T1 > trade['sl']:
                            o.moveStopBuy(trade, superM05_5003T1, tick)

                elif TransactionSide.SELL == trade['cmd']:
                    if trade['customComment'] == "SMMA200_M1&&EMA70 vente":
                        # descendre le stop  a 5pip de benef :
                        #   Si cours en dessous de l ouverture avec ecart 20pip
                        #   Et si AW change de tendance
                        if trade['sl'] > trade['open_price'] and tick < trade['open_price'] - 25 and \
                                bougie0M05['AW'] > bougie1M05['AW']:
                            sl = trade['open_price'] - 3
                            o.moveStopSell(trade, sl, tick)

                        elif superM05_5003T1 < trade['sl']:
                            o.moveStopSell(trade, superM05_5003T1, tick)

        print("ordre en cours   END...........................................")

async def ema_st(logger, o, tick, spM01_4005T0, balance, tradeOpen, tradeOpenDic, bougie1M01):
    try:
        orderExist = False
        # move order
        if len(tradeOpen['returnData']) > 0:
            for trade in tradeOpenDic['returnData']:
                print("trade['customComment']:", trade['customComment'])
                print("trade['cmd']:", trade['cmd'])
                if TransactionSide.BUY_LIMIT == trade['cmd'] and trade['customComment'] == "ema_st":
                    orderExist = True
                    sl = spM01_4005T0 - 2
                    price = bougie1M01.get("EMA200")+1
                    tp = 0
                    o.movebuyLimitWait(trade, sl, tp, price, balance, VNL)
                elif TransactionSide.BUY == trade['cmd'] and trade['customComment'] == "ema_st":
                    orderExist = True
                    if trade['sl'] < spM01_4005T0 < tick:
                        o.moveStopBuy(trade, spM01_4005T0, tick)
                elif TransactionSide.SELL_LIMIT == trade['cmd'] and trade['customComment'] == "ema_st":
                    orderExist = True
                    sl = spM01_4005T0 + 2
                    price = bougie1M01.get("EMA200")-1
                    tp = 0
                    o.moveSellLimitWait(trade, sl, tp, price, balance, VNL)
                elif TransactionSide.SELL == trade['cmd'] and trade['customComment'] == "ema_st":
                    orderExist = True
                    if trade['sl'] > spM01_4005T0 > tick:
                        o.moveStopBuy(trade, spM01_4005T0, tick)

        if orderExist is False:
            if tick > bougie1M01.get("EMA40") > bougie1M01.get("EMA200") > spM01_4005T0:
                sl = spM01_4005T0 - 2
                tp = 0
                price = bougie1M01.get("EMA200")+1
                o.buyLimit(sl, tp, price, balance, VNL, "ema_st")
            elif tick < bougie1M01.get("EMA40") < bougie1M01.get("EMA200") < spM01_4005T0:
                sl = spM01_4005T0 + 2
                tp = 0
                price = bougie1M01.get("EMA200") - 1
                o.sellLimit(sl, tp, price, balance, VNL, "ema_st")

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
            print("-- bougie1M01.get(AW) :", bougie1M01.get("AW"))
            print("-- bougie2M01.get(AW) :", bougie2M01.get("AW"))
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

        # # Awesome ##################################################################################################
        ao05 = Awesome(SYMBOL, "M05")
        #
        o = Order(SYMBOL, dbStreaming, client, db["trade"])

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

            zone = await pivot()
            c.getTick()

            candles = c.getCandles()
            print("=================> candles:", candles)
            # ####################################################################################################
            await majDatAall(logger, email, client, SYMBOL, db)
            # ####################################################################################################
            await moyMobil_05.EMA(70, 1)
            await moyMobil_05.SMMA(200, 1)

            await moyMobil_01.SMMA(200, 1)
            await moyMobil_01.EMA(40, 1)
            await moyMobil_01.EMA(70, 1)
            await moyMobil_01.EMA(200, 1)

            await moyMobil_01.EMA(26, 1)
            #
            # # AO ###################################################################################
            await ao05.calculLastCandle(10)
            #
            # # supertrend ###################################################################################
            spM05_1003 = Supertrend(SYMBOL, "M05", 10, 3)
            superM05_1003T0, superM05_1003T1, superM05_1003T2 = spM05_1003.getST()

            spM01_1005 = Supertrend(SYMBOL, "M01", 10, 5)
            spM01_1005T0, spM01_1005T1, spM01_1005T2 = spM01_1005.getST()

            spM01_4005 = Supertrend(SYMBOL, "M01",40, 5)
            spM01_4005T0, spM01_4005T1, spM01_4005T2 = spM01_4005.getST()

            if c.getTick() is not None:
                print("jour:", j, " h:", todayPlus2Hours.hour)
                if 0 <= j < 5 and 2 < todayPlus2Hours.hour < 22:
                    print("dans le if !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
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
                    bougie0M01 = db["M01"].find({}, sort=[('ctm', -1)]).limit(1).skip(0)[0]
                    bougie1M01 = db["M01"].find({}, sort=[('ctm', -1)]).limit(1).skip(1)[0]
                    bougie2M01 = db["M01"].find({}, sort=[('ctm', -1)]).limit(1).skip(2)[0]
                    bougie3M01 = db["M01"].find({}, sort=[('ctm', -1)]).limit(1).skip(3)[0]
                    bougie4M01 = db["M01"].find({}, sort=[('ctm', -1)]).limit(1).skip(4)[0]
                    bougie5M01 = db["M01"].find({}, sort=[('ctm', -1)]).limit(1).skip(5)[0]

                    bougie0M05 = db["M05"].find({}, sort=[('ctm', -1)]).limit(1).skip(0)[0]
                    bougie1M05 = db["M05"].find({}, sort=[('ctm', -1)]).limit(1).skip(1)[0]

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

                    # await SMMA200_M1_EMA70(o, tick, bougie1M01, superM05_1003T1, zone, balance, tradeOpen, tradeOpenDic, bougie0M05, bougie1M05)

                    await AW_pivot_st1004(logger, o, tick, superM05_1003T0, spM01_1005T0,
                                          balance, tradeOpen, tradeOpenDic, bougie1M05, bougie0M05, bougie1M01,
                                          bougie2M01)

                    await ema_st(logger, o, tick, spM01_4005T0, balance, tradeOpen, tradeOpenDic, bougie1M01)
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
