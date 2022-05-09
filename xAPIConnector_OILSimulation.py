# -*- coding: utf-8 -*-
# python3 -m pip install pymongo==3.5.1

import json
import time
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

# import datetime
startSimultion = 0
endSimultion = 0

# Variables perso--------------------------------------------------------------------------------------------------------
# horaire---------------
TradeStartTime = 4
TradeStopTime = 22
# gestion managment-----
Risk = 2.00  # risk %
TakeProfit = 50
StopLoss = 10
ObjectfDay = 3.00 # %
# communication---------
SignalMail = False

BALANCE = 0
TICK = False
PROFIT = False

# GE30 le cout d un pip = 25€ * 0.01 --------------------------
PRICE = 6.95
PIP = 0.01
SYMBOL = "OIL"
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
        for value in dataDownload["returnData"]['rateInfos']:
            open = value['open'] / 100.0
            close = (value['open'] + value['close']) / 100.0
            high = (value['open'] + value['high']) / 100.0
            low = (value['open'] + value['low']) / 100.0
            pointMedian = round((high + low) / 2, 2)
            if (listDataDB is None) or (value['ctm'] > listDataDB["ctm"]):
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
async def majDatAall(client, startTime, symbol, db):
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

    endTime = int(round(time.time() * 1000)) + (6 * 60 * 1000)

    # MAJ DAY : 13 mois------------------------------------------------------------------------
    print("Mise à jour D")
    startTimeDay = int(round(time.time() * 1000)) - (60 * 60 * 24 * 30 * 13) * 1000
    arguments = {
        "info": {"start": startTimeDay - (30 * 24 * 3600 * 1000), "end": endTime, "period": 1440,
                 "symbol": symbol,
                 "ticks": 0}}
    json_data_Day = client.commandExecute('getChartRangeRequest', arguments)
    dataDAY = json.dumps(json_data_Day)
    dataDAYDownload = json.loads(dataDAY)
    listDataDBDAY = db["D"].find_one({}, sort=[('ctm', -1)])
    await insertData(db["D"], dataDAYDownload, listDataDBDAY)

    # MAJ H4 : 13 mois max------------------------------------------------------------------------
    print("Mise à jour H4")
    startTimeH4 = int(round(time.time() * 1000)) - (60 * 60 * 24 * 30 * 13) * 1000
    json_data_H4 = client.commandExecute('getChartRangeRequest', {
        "info": {"start": startTimeH4, "end": endTime, "period": 240,
                 "symbol": symbol,
                 "ticks": 0}})
    data_H4 = json.dumps(json_data_H4)
    dataH4Download = json.loads(data_H4)
    # print(dataH4Download)
    listDataDB = db["H4"].find_one({}, sort=[('ctm', -1)])
    await insertData(db["H4"], dataH4Download, listDataDB)

    # MAJ H1 : 13 mois max------------------------------------------------------------------------
    print("Mise à jour H1")
    startTimeH1 = int(round(time.time() * 1000)) - (60 * 60 * 24 * 30 * 13) * 1000
    json_data_H1 = client.commandExecute('getChartRangeRequest', {
        "info": {"start": startTimeH1, "end": endTime, "period": 60,
                 "symbol": symbol,
                 "ticks": 0}})
    data_H1 = json.dumps(json_data_H1)
    dataH1Download = json.loads(data_H1)
    # print(dataH4Download)
    listDataDB = db["H1"].find_one({}, sort=[('ctm', -1)])
    await insertData(db["H1"], dataH4Download, listDataDB)

    # MAJ 15 min ------------------------------------------------------------------------
    print("Mise à jour M15")
    startTimeM15 = int(round(time.time() * 1000)) - (60 * 60 * 24 * 30 * 15) * 1000
    json_data_M15 = client.commandExecute('getChartRangeRequest', {
        "info": {"start": startTimeM15, "end": endTime, "period": 15,
                 "symbol": symbol,
                 "ticks": 0}})
    dataM15 = json.dumps(json_data_M15)
    dataM15Download = json.loads(dataM15)
    listDataDBM15 = db["M15"].find_one({}, sort=[('ctm', -1)])
    await insertData(db["M15"], dataM15Download, listDataDBM15)

    # MAJ Minute : 1 mois max------------------------------------------------------------------------
    print("Mise à jour M01")
    startTimeM01 = int(round(time.time() * 1000)) - (60 * 60 * 24 * 30) * 1000
    json_data_M01 = client.commandExecute('getChartRangeRequest', {
        "info": {"start": startTimeM01, "end": endTime, "period": 1,
                 "symbol": symbol,
                 "ticks": 0}})
    dataM01 = json.dumps(json_data_M01)
    dataM01Download = json.loads(dataM01)
    # print(dataM01Download)
    listDataDBM01 = db["M01"].find_one({}, sort=[('ctm', -1)])
    await insertData(db["M01"], dataM01Download, listDataDBM01)

    # MAJ 5 min ------------------------------------------------------------------------
    print("Mise à jour M05")
    startTimeM05 = int(round(time.time() * 1000)) - (60 * 60 * 24 * 30) * 1000
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
def NbrLot(balance, position, stp):
    '''
    Calcul le nombre de posible à prendre
    :param balance:
    :param position:
    :param stp:
    :return:
    '''
    try:
        perteAcceptable = round(balance["equityFX"] * Risk/100, 0)
        ecartPip = abs((position - stp))
        print("ecartPip :", ecartPip)
        nbrelot = perteAcceptable / ecartPip / (1000 / 100) / 100
        # print("nbre de lot :", nbrelot)
        qtMax = round_down((balance["equityFX"] / 20000), 2)
        if nbrelot > qtMax:
            nbrelot = qtMax

        # print('//////////////////////////////////// NbrLot ////////////////////////////////////')
        # print('balance :', balance["equityFX"])
        # print('position :', position)
        # print('stp :', stp)
        # print('perteAcceptable :', perteAcceptable)
        # print('ecartPip :', ecartPip)
        # print('nbrelot :', nbrelot)
        # print('//////////////////////////////////// NbrLot ////////////////////////////////////')

        return round(nbrelot, 2)
    except (RuntimeError, TypeError, NameError):
        pass
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
    print("close:", close)
    print("pîvot down:", arrayT)
    support_down = 0
    supportHigt = 0
    for v in arrayT:
        if v < close:
            support_down = v
        if v > close:
            if supportHigt == 0:
                supportHigt = v
                print("pîvot up calcul:", supportHigt)
        

    print(support_down, " / ",supportHigt)
    return support_down, supportHigt

async def main():
    client = APIClient()  # create & connect to RR socket
    loginResponse = client.identification()  # connect to RR socket, login
    logger.info(str(loginResponse))

    # check if user logged in correctly
    if (loginResponse['status'] == False):
        print('Login failed. Error code: {0}'.format(loginResponse['errorCode']))
        return
    try:
        connection = MongoClient('localhost', 27017)
        db = connection[SYMBOL]
        dbStreaming = connection["STREAMING"]
        c = Command()
        # ssid = loginResponse['streamSessionId']
        # sclient = APIStreamClient(
        #     ssId=ssid,
        #     tickFun=c.procTickExample,
        #     tradeFun=c.procTradeExample,
        #     profitFun=c.procProfitExample,
        #     tradeStatusFun=c.procTradeStatusExample,
        #     balanceFun=c.procBalanceExample
        # )
        # sclient.subscribePrice("OIL")
        # sclient.subscribeProfits()
        # sclient.subscribeTradeStatus()
        # sclient.subscribeTrades()
        # sclient.subscribeBalance()
        #

        #
        # startTime = int(round(time.time() * 1000)) - (
        #         60 * 60 * 30 * 1) * 1000  # reculer de 30 jours : (60*60*24*30)*1000
        #
        # # print("************************** calcul balance******************************************")
        # json_balance1 = json.dumps(client.commandExecute('getMarginLevel'))
        # dict_balance = json.loads(json_balance1)
        # BALANCE = dict_balance["returnData"]
        #
        # print("mise à jour en cours de l ensemble .......")
        # startTime = await majDatAall(client, startTime, SYMBOL, db)
        #
        # # # pivot##################################################################################################
        # print('mise à jour du pivot -------------------------')
        # P = Pivot(SYMBOL, "D")
        # PPF, R1F, R2F, R3F, S1F, S2F, S3F = await P.fibonacci()  # valeurs ok
        # PPW, R1W, R2W, S1W, S2W = await P.woodie()  # valeurs ok
        # PPC, R1C, R2C, R3C, R4C, S1C, S2C, S3C, S4C = await P.camarilla()  # valeurs ok
        # R1D, S1D = await P.demark()  # valeurs ok
        #
        # zone = np.array(
        #     [PPC, R1C, R2C, R3C, R4C, S1C, S2C, S3C, S4C, R1W, R2W, S1W, S2W, R1D, S1D])
        # zone = np.sort(zone)
        # print('zone :', zone)
        # #exit(0)
        # print('calcul du Pivot fini')
        # moy_mobil_01_120 = MM(SYMBOL, "M01", 0)
        # moy_mobil_01_120.calculSMA(120)
        # #
        # moy_mobil_05_120 = MM(SYMBOL, "M05", 0)
        # moy_mobil_05_120.calculSMA(120)
        # moy_mobil_05_120.EMA(120)
        #
        # ao05 = Awesome(SYMBOL, "M05")
        # await ao05.calculAllCandles()
        # ao01 = Awesome(SYMBOL, "M01")
        # await ao01.calculAllCandles()
        #
        # # supertrend ###################################################################################
        # sp_m05 = Supertrend(SYMBOL, "M05", 30, 5)
        # super_m05_t0, super_t1, super_t2 = sp_m05.getST()
        # super_m05T0 = round(float(super_m05_t0), 2)
        # # print("super_m01T0 :", super_m05T0)
        # superT1 = round(float(super_t1), 1)
        # # print("superT1 :", superT1)
        # sp_m05 = Supertrend(SYMBOL, "M05", 10, 4)
        # super_m05T0, super_m05T1, super_m05T2 = sp_m05.getST()
        # # print("super_m05T0 :", super_m05T0)
        #
        # print("fini *********************************")
        #
        # o = Order(SYMBOL, dbStreaming, client)


        # Charger les bougies
        bougies_m01 = db["M01"].find({"ctm" : {"$gt" : 1648828380000, "$lt" : 1651769400000},"SMA120": {"$exists": True}})

        trade_open = 0
        type_order = 0
        db["simulation"]
        print(type(bougies_m01))
        i = 0
        for b in bougies_m01:
            if i > 0:
                trade_open = db["simulation"].find_one({"close": 0})
                if trade_open is None:
                    if b["low"] < b["SMA120"] > b["high"] :
                        type_order = TransactionSide.BUY_LIMIT
                        newvalues = {
                            "type_order" : type_order,
                            "ctm": b['ctm'],
                            "ctmString": b['ctmString'],
                            "open": b["open"],
                            "close": 0
                        }
                        print(b)
                        db["simulation"].insert_one(newvalues)
                else:
                    if type_order == TransactionSide.BUY_LIMIT:
                        pass

            i = i+1

        print(db["simulation"].find_one())

    except Exception as exc:
        print("le programe a déclenché une erreur")
        print("exception de mtype ", exc.__class__)
        print("message", exc)
        # client.disconnect()
    except OSError as err:
        print("OS error: {0}".format(err))
        # client.disconnect()
    print("exit")
    # client.disconnect()
    # sclient.disconnect()
if __name__ == "__main__":
    asyncio.run(main())
