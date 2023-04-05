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
from Configuration.Log import Log

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
SPREAD = 0.0001


# ----------------------------------------------------------------------------------------------------------

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
                        }}
                    collection.update_many(myquery, newvalues)

    except Exception as exc:
        print("insertData a déclenché une erreur")
        print("exception de mtype ", exc.__class__)
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(exc).__name__, exc.args)
        print(exc)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print("Details : ", exc_type, fname, exc_tb.tb_lineno)


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
        await insertData(db["D"], dataDAYDownload, lastBougie)

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
    sclient.subscribePrice("EURUSD")
    sclient.subscribeProfits()
    sclient.subscribeTradeStatus()
    sclient.subscribeTrades()
    sclient.subscribeBalance()

    return sclient, c


async def pivot():
    print('calcul pivot ')
    P = Pivot(SYMBOL, "D", 5)
    PPF, R1F, R2F, R3F, S1F, S2F, S3F = await P.fibonacci()  # valeurs ok
    R1D, S1D = await P.demark()  # valeurs ok
    PPW, R1W, R2W, S1W, S2W = await P.woodie()  # valeurs ok
    # PPC, R1C, R2C, R3C, R4C, S1C, S2C, S3C, S4C = await P.camarilla()  # valeurs ok
    # zone = np.array([R1W, R2W, S1W, S2W, R1D, S1D, PPF, R1F, R2F, R3F, S1F, S2F, S3F, PPC, R1C, R2C, R3C, R4C, S1C, S2C, S3C, S4C])
    zone = np.array(
        [R1W, R2W, S1W, S2W, R1D, S1D, PPF, R1F, R2F, R3F, S1F, S2F, S3F])
    return np.sort(zone), PPF

async def main():
    try:
        connection = MongoClient('localhost', 27017)
        db = connection[SYMBOL]

        # Charger les bougies
        bougies0_m05 = False
        bougies_m05 = db["M05"].find({"ctm": {"$gt": 1672993294000, "$lt": 1673035200000}, "EMA70": {"$exists": True}})

        order_number = 0
        type_order = 0
        db["simulation"]
        i = 0
        import sys
        import re

        spM05 = Supertrend(SYMBOL, "M05", 15, 6, 5)
        super_t0, super_t1, super_t2 = spM05.getST()

        for b_m05 in bougies_m05:
            order = db["simulation"].find_one({"close": 0})
            if order is not None:
                # 1 ordre en cours
                if b_m05["low"] < order["stop"] < b_m05["high"]:
                    # verifier si le stop est touché
                    filter_order= {'ctm': order["ctm"]}
                    gain = 0
                    if order["type_order"] == 2:
                        gain = order["stop"] - order["open"]
                    elif order["type_order"] == 3:
                        gain = order["open"] - order["stop"]

                    newvalues = { "$set": {
                        "type_order": order["type_order"],
                        "ctm": order["ctm"],
                        "openCtmString": order['openCtmString'],
                        "closeCtmString": b_m05["ctmString"],
                        "open": order["open"],
                        "close": order["stop"],
                        "stop": order["stop"],
                        "objectif": order["objectif"],
                        "type": order["type"],
                        "Awesome": order["Awesome"],
                        "gain" : round(gain,20)
                    }}
                    db["simulation"].update_one(filter_order, newvalues)
                    print("stop touch")

                if b_m05["low"] < order["objectif"] < b_m05["high"]:
                    # verifier si objectiof est touché
                    filter_order = {'ctm': order["ctm"]}
                    gain = 0
                    if order["type_order"] == 2:
                        gain = order["objectif"] - order["open"]
                    elif order["type_order"] == 3:
                        gain = order["open"] - order["objectif"]

                    newvalues = { "$set": {
                        "type_order": order["type_order"],
                        "ctm": order["ctm"],
                        "openCtmString": order['openCtmString'],
                        "closeCtmString": b_m05["ctmString"],
                        "open": order["open"],
                        "close": order["objectif"],
                        "stop": order["stop"],
                        "objectif": order["objectif"],
                        "type": order["type"],
                        "Awesome": order["Awesome"],
                        "gain" : round(gain,20)
                    }}
                    print("-----------------------------------------------------------------")
                    print(order)
                    print(b_m05)
                    print("-----------------------------------------------------------------")
                    db["simulation"].update_one(filter_order, newvalues)
                    #sys.exit()
            if i > 0:
                trade_open = db["simulation"].find_one({"close": 0})

                if trade_open is None and bougies0_m05 is not False:
                    print("aucun ordre en cours ********************")
                    bougies_d = db["D"].find_one({"ctmString": {"$regex": b_m05["ctmString"][:12]}})
                    print("journée : ", bougies_d)
                    print("periode :", b_m05["close"] )
                    print("woodie : ", bougies_d["PWoodie_PP"])
                    if b_m05["close"] > bougies_d["PWoodie_PP"] and b_m05["EMA70"] > bougies0_m05["EMA70"]:  # condition strategique
                        print("passage d ordree d achat ********************")
                        type_order = TransactionSide.BUY_LIMIT
                        ####################################"
                        zone = np.array(
                            [
                                bougies_d["PWoodie_PP"],
                                bougies_d["PWoodie_r1"],
                                bougies_d["PWoodie_r2"],
                                bougies_d["PWoodie_s1"],
                                bougies_d["PWoodie_s2"]
                            ])
                        zone = np.sort(zone)

                        supportDown, supportHight = zoneSoutien(b_m05["close"], zone)
                        support = supportDown
                        objectif = supportHight
                        if objectif == 0:
                            # print("zone:",zone)
                            # print("b_m05:", b_m05)
                            # sys.exit()
                            objectif = b_m05["open"] + 0.50
                        ######################################################""

                        newvalues = {
                            "order_number": order_number,
                            "type_order": type_order,
                            "ctm": b_m05['ctm'],
                            "openCtmString": b_m05['ctmString'],
                            "open": b_m05["close"],
                            "close": 0,
                            "stop": support,
                            "objectif": objectif,
                            "type": "achat",
                            "EMA70": b_m05["EMA70"]
                        }
                        print("----------achat------------------")
                        print(zone)
                        print(newvalues)
                        print("--------------------------------")
                        # sys.exit()

                        db["simulation"].insert_one(newvalues)
                        order_number = order_number+1
                    elif b_m05["close"] < bougies_d["PWoodie_PP"] and b_m05["EMA70"] < bougies0_m05["EMA70"]:  # check if touch
                        print("passage d ordree de vente ********************")
                        type_order = TransactionSide.SELL_LIMIT

                        ####################################"
                        zone = np.array(
                            [
                                bougies_d["PWoodie_PP"],
                                bougies_d["PWoodie_r1"],
                                bougies_d["PWoodie_r2"],
                                bougies_d["PWoodie_s1"],
                                bougies_d["PWoodie_s2"]
                            ])
                        zone = np.sort(zone)
                        supportDown, supportHight = zoneSoutien(b_m05["close"], zone)
                        support = supportHight
                        objectif = supportDown
                        if objectif == 0:
                            # print("zone:",zone)
                            # print("b_m05:", b_m05)
                            # sys.exit()
                            objectif = b_m05["close"] - 1.00
                        ######################################################""

                        newvalues = {
                            "order_number" : order_number,
                            "type_order": type_order,
                            "ctm": b_m05['ctm'],
                            "openCtmString": b_m05['ctmString'],
                            "open": b_m05["close"],
                            "close": 0,
                            "stop": support,
                            "objectif": objectif,
                            "type": "vente",
                            "EMA70": b_m05["EMA70"]
                        }

                        print("----------vente------------------")
                        print(zone)
                        print(newvalues)
                        print("--------------------------------")
                        db["simulation"].insert_one(newvalues)
                        order_number = order_number + 1

                    print("type_order :", type_order)
                    print("traitement de la bougie fini")
                else:
                    if type_order == TransactionSide.BUY_LIMIT:
                        pass

            bougies0_m05 = b_m05
            i = i + 1

        print("debut du calcul du gain")
        bilan= 0
        for order in db["simulation"].find({"gain": {"$exists": True}}):
            print(order)
            if order["gain"] is not None:
                bilan= bilan + order["gain"]

        print("bilan :", bilan)




    except OSError as err:
        print("erreur : ", err)
        exit(0)


if __name__ == "__main__":
    asyncio.run(main())
