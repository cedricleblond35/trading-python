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
VNL = 15
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
        for value in dataDownload["returnData"]['rateInfos']:
            ctm = value['ctm']
            close = (value['open'] + value['close']) / 100.0
            high = (value['open'] + value['high']) / 100.0
            low = (value['open'] + value['low']) / 100.0
            pointMedian = round((high + low) / 2, 2)
            if (listDataDB is None) or (value['ctm'] > listDataDB["ctm"]):
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
            elif value['ctm'] == listDataDB["ctm"]:
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

    return ctm


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

    startTimeDay = int(round(time.time() * 1000)) - (60 * 60 * 24 * 3) * 1000
    arguments = {
        "info": {"start": startTimeDay, "end": endTime, "period": 1440,
                 "symbol": symbol,
                 "ticks": 0}}
    json_data_D = client.commandExecute('getChartRangeRequest', arguments)
    data_D = json.dumps(json_data_D)
    dataDayDownload = json.loads(data_D)
    listDataDB = db["D"].find_one({}, sort=[('ctm', -1)])
    await insertData(db["D"], dataDayDownload, listDataDB)

    # MAJ H4 ------------------------------------------------------------------------
    # 20 jours x 24 heures x 3600 secondes x 1000
    # print("H4 :", startTime - (6 * 3600000))
    json_data_H4 = client.commandExecute('getChartRangeRequest', {
        "info": {"start": startTime - (6 * 3600000), "end": endTime, "period": 240,
                 "symbol": symbol,
                 "ticks": 0}})
    data_H4 = json.dumps(json_data_H4)
    dataH4Download = json.loads(data_H4)
    listDataDB = db["H4"].find_one({}, sort=[('ctm', -1)])
    await insertData(db["H4"], dataH4Download, listDataDB)

    json_data_M15 = client.commandExecute('getChartRangeRequest', {
        "info": {"start": startTime - (6 * 60 * 1000), "end": endTime, "period": 15,
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

        # on retourne le dernier temps "ctm" enregistré
        return newTime
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
    # R1D, S1D = await P.demark()  # valeurs ok

    PPW, R1W, R2W, S1W, S2W = await P.woodie()  # valeurs ok
    #PPC, R1C, R2C, R3C, R4C, S1C, S2C, S3C, S4C = await P.camarilla()  # valeurs ok
    #zone = np.array([PPC, R1C, R2C, R3C, R4C, S1C, S2C, S3C, S4C, R1W, R2W, S1W, S2W])
    zone = np.array([PPW, R1W, R2W, S1W, S2W])
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
        connection = MongoClient('localhost', 27017)
        db = connection[SYMBOL]

        # Charger les bougies
        bougies0_m01 = False
        bougies_m01 = db["M01"].find({"ctm": {"$gt": 1661983200000, "$lt": 1662069600000}, "EMA120": {"$exists": True}})

        order_number = 0
        type_order = 0
        db["simulation"]
        i = 0
        import sys
        import re

        sp_m01 = Supertrend(SYMBOL, "M01", 20, 5)
        super_t0, super_t1, super_t2 = sp_m01.getST()

        for b_m01 in bougies_m01:
            order = db["simulation"].find_one({"close": 0})
            if order is not None:
                # 1 ordre en cours
                if b_m01["low"] < order["stop"] < b_m01["high"]:
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
                        "closeCtmString": b_m01["ctmString"],
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

                if b_m01["low"] < order["objectif"] < b_m01["high"]:
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
                        "closeCtmString": b_m01["ctmString"],
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
                    print(b_m01)
                    print("-----------------------------------------------------------------")
                    db["simulation"].update_one(filter_order, newvalues)
                    #sys.exit()
            if i > 0:
                trade_open = db["simulation"].find_one({"close": 0})

                if trade_open is None and bougies0_m01 is not False:
                    print("aucun ordre en cours ********************")
                    bougies_d = db["D"].find_one({"ctmString": {"$regex": b_m01["ctmString"][:12]}})
                    print("journée : ", bougies_d)
                    print("periode :", b_m01["close"] )
                    print("woodie : ", bougies_d["PWoodie_PP"])
                    print("woodie : ", b_m01["AW"])
                    if b_m01["close"] > bougies_d["PWoodie_PP"] and b_m01["AW"] > bougies0_m01["AW"] and b_m01["AW"] > 0.50:  # condition strategique
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

                        supportDown, supportHight = zoneSoutien(b_m01["close"], zone)
                        support = supportDown
                        objectif = supportHight
                        if objectif == 0:
                            # print("zone:",zone)
                            # print("b_m01:", b_m01)
                            # sys.exit()
                            objectif = b_m01["open"] + 0.50
                        ######################################################""

                        newvalues = {
                            "order_number": order_number,
                            "type_order": type_order,
                            "ctm": b_m01['ctm'],
                            "openCtmString": b_m01['ctmString'],
                            "open": b_m01["close"],
                            "close": 0,
                            "stop": support,
                            "objectif": objectif,
                            "type": "achat",
                            "Awesome": b_m01["AW"]
                        }
                        print("----------achat------------------")
                        print(zone)
                        print(newvalues)
                        print("--------------------------------")
                        # sys.exit()

                        db["simulation"].insert_one(newvalues)
                        order_number = order_number+1
                    elif b_m01["close"] < bougies_d["PWoodie_PP"] and b_m01["AW"] < bougies0_m01["AW"] and b_m01["AW"] < -0.50:  # check if touch
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
                        supportDown, supportHight = zoneSoutien(b_m01["close"], zone)
                        support = supportHight
                        objectif = supportDown
                        if objectif == 0:
                            # print("zone:",zone)
                            # print("b_m01:", b_m01)
                            # sys.exit()
                            objectif = b_m01["close"] - 1.00
                        ######################################################""

                        newvalues = {
                            "order_number" : order_number,
                            "type_order": type_order,
                            "ctm": b_m01['ctm'],
                            "openCtmString": b_m01['ctmString'],
                            "open": b_m01["close"],
                            "close": 0,
                            "stop": support,
                            "objectif": objectif,
                            "type": "vente",
                            "Awesome": b_m01["AW"]
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

            bougies0_m01 = b_m01
            i = i + 1


        print("debut du calcul du gain")
        bilan= 0
        for order in db["simulation"].find({"gain": {"$exists": True}}):
            print(order)
            if order["gain"] is not None:
                bilan= bilan + order["gain"]

        print("bilan :", bilan)


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


if __name__ == "__main__":
    asyncio.run(main())
