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
        perteAcceptable = round(balance["equityFX"] * Risk / 100, 0)
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


def zoneSoutien(close, zone):
    arrayT = sorted(zone)
    support_down = 0
    support_higt = 0
    for v in arrayT:
        if v < close:
            if close - v > 0.5:
                support_down = v
        if v > close:
            if support_higt == 0:
                #print("support_higt - close :", v, "-", close)
                if v - close > 0.5:  # remplacer 0.50 par l'écart type d'environ 5 bougire
                    support_higt = v

    # print(support_down, " / ",supportHigt)
    return support_down, support_higt


def main():
    try:
        connection = MongoClient('localhost', 27017)
        db = connection[SYMBOL]


        # Charger les bougies
        bougies0_m01 = False
        bougies_m01 = db["M01"].find({"ctm": {"$gt": 1661983200000, "$lt": 1662069600000}, "EMA120": {"$exists": True}})


        trade_open = 0
        type_order = 0
        db["simulation"]
        i = 0
        import sys

        sp_m01 = Supertrend(SYMBOL, "M01", 20, 5)
        super_t0, super_t1, super_t2 = sp_m01.getST()

        import re

        for b_m01 in bougies_m01:
            order = db["simulation"].find_one({"close": 0})
            if order is not None:

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
                        "gain" : round(gain,1)
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
                        "gain" : round(gain,1)
                    }}
                    print("-----------------------------------------------------------------")
                    print(order)
                    print(b_m01)
                    print("-----------------------------------------------------------------")
                    db["simulation"].update_one(filter_order, newvalues)
                    #sys.exit()
            if i > 0:
                trade_open = db["simulation"].find_one({"close": 0})
                # if trade_open is None and bougies0_m01 is not False:
                #     bougies_d = db["D"].find_one({"ctmString": {"$regex": b_m01["ctmString"][:12]}})
                #     if b_m01["SMA120"] > bougies0_m01["SMA120"]  and bougies0_m01["low"] > bougies0_m01["SMA120"]:  # condition strategique
                #         if b_m01["low"] < b_m01["SMA120"] < b_m01["high"]:  # check if touch
                #             type_order = TransactionSide.BUY_LIMIT
                #             ####################################"
                #             zone = np.array(
                #                 [
                #                     bougies_d["PCamarilla_PP"],
                #                     bougies_d["PCamarilla_r1"],
                #                     bougies_d["PCamarilla_r2"],
                #                     bougies_d["PCamarilla_r3"],
                #                     bougies_d["PCamarilla_r4"],
                #                     bougies_d["PCamarilla_s1"],
                #                     bougies_d["PCamarilla_s2"],
                #                     bougies_d["PCamarilla_s3"],
                #                     bougies_d["PCamarilla_s4"],
                #                     bougies_d["PWoodie_PP"],
                #                     bougies_d["PWoodie_r1"],
                #                     bougies_d["PWoodie_r2"],
                #                     bougies_d["PWoodie_s1"],
                #                     bougies_d["PWoodie_s2"],
                #                     bougies_d["demark_r1"],
                #                     bougies_d["demark_s1"]
                #                 ])
                #             zone = np.sort(zone)
                #
                #             supportDown, supportHight = zoneSoutien(b_m01["SMA120"], zone)
                #             support = supportDown
                #             objectif = supportHight
                #             if objectif == 0 :
                #                 # print("zone:",zone)
                #                 # print("b_m01:", b_m01)
                #                 # sys.exit()
                #                 objectif = b_m01["open"] + 0.50
                #             ######################################################""
                #
                #             newvalues = {
                #                 "type_order": type_order,
                #                 "ctm": b_m01['ctm'],
                #                 "openCtmString": b_m01['ctmString'],
                #                 "open": b_m01["SMA120"],
                #                 "close": 0,
                #                 "stop": support,
                #                 "objectif": objectif,
                #                 "type": "achat"
                #             }
                #             print(newvalues)
                #             #sys.exit()
                #
                #             db["simulation"].insert_one(newvalues)
                #     elif b_m01["SMA120"] < bougies0_m01["SMA120"]  and bougies0_m01["low"] < bougies0_m01["SMA120"]:  # condition strategique
                #         if b_m01["low"] < b_m01["SMA120"] < b_m01["high"]:  # check if touch
                #             type_order = TransactionSide.SELL_LIMIT
                #
                #             ####################################"
                #             zone = np.array(
                #                 [
                #                     bougies_d["PCamarilla_PP"],
                #                     bougies_d["PCamarilla_r1"],
                #                     bougies_d["PCamarilla_r2"],
                #                     bougies_d["PCamarilla_r3"],
                #                     bougies_d["PCamarilla_r4"],
                #                     bougies_d["PCamarilla_s1"],
                #                     bougies_d["PCamarilla_s2"],
                #                     bougies_d["PCamarilla_s3"],
                #                     bougies_d["PCamarilla_s4"],
                #                     bougies_d["PWoodie_PP"],
                #                     bougies_d["PWoodie_r1"],
                #                     bougies_d["PWoodie_r2"],
                #                     bougies_d["PWoodie_s1"],
                #                     bougies_d["PWoodie_s2"],
                #                     bougies_d["demark_r1"],
                #                     bougies_d["demark_s1"]
                #                 ])
                #             zone = np.sort(zone)
                #             supportDown, supportHight = zoneSoutien(b_m01["SMA120"], zone)
                #             support = supportHight
                #             objectif = supportDown
                #             if objectif == 0 :
                #                 # print("zone:",zone)
                #                 # print("b_m01:", b_m01)
                #                 # sys.exit()
                #                 objectif = b_m01["close"] - 1.00
                #             ######################################################""
                #
                #             newvalues = {
                #                 "type_order": type_order,
                #                 "ctm": b_m01['ctm'],
                #                 "openCtmString": b_m01['ctmString'],
                #                 "open": b_m01["open"],
                #                 "close": 0,
                #                 "stop": support,
                #                 "objectif": objectif,
                #                 "type": "vente"
                #             }
                #
                #             db["simulation"].insert_one(newvalues)
                #
                # else:
                #     if type_order == TransactionSide.BUY_LIMIT:
                #         pass
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
                                bougies_d["PCamarilla_PP"],
                                bougies_d["PCamarilla_r1"],
                                bougies_d["PCamarilla_r2"],
                                bougies_d["PCamarilla_r3"],
                                bougies_d["PCamarilla_r4"],
                                bougies_d["PCamarilla_s1"],
                                bougies_d["PCamarilla_s2"],
                                bougies_d["PCamarilla_s3"],
                                bougies_d["PCamarilla_s4"],
                                bougies_d["PWoodie_PP"],
                                bougies_d["PWoodie_r1"],
                                bougies_d["PWoodie_r2"],
                                bougies_d["PWoodie_s1"],
                                bougies_d["PWoodie_s2"],
                                bougies_d["demark_r1"],
                                bougies_d["demark_s1"]
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
                    elif b_m01["close"] < bougies_d["PWoodie_PP"] and b_m01["AW"] < bougies0_m01["AW"] and b_m01["AW"] < -0.50:  # check if touch
                        type_order = TransactionSide.SELL_LIMIT

                        ####################################"
                        zone = np.array(
                            [
                                bougies_d["PCamarilla_PP"],
                                bougies_d["PCamarilla_r1"],
                                bougies_d["PCamarilla_r2"],
                                bougies_d["PCamarilla_r3"],
                                bougies_d["PCamarilla_r4"],
                                bougies_d["PCamarilla_s1"],
                                bougies_d["PCamarilla_s2"],
                                bougies_d["PCamarilla_s3"],
                                bougies_d["PCamarilla_s4"],
                                bougies_d["PWoodie_PP"],
                                bougies_d["PWoodie_r1"],
                                bougies_d["PWoodie_r2"],
                                bougies_d["PWoodie_s1"],
                                bougies_d["PWoodie_s2"],
                                bougies_d["demark_r1"],
                                bougies_d["demark_s1"]
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
        print("le programe a déclenché une erreur")
        print("exception de mtype ", exc.__class__)
        print("message", exc)
        # client.disconnect()
    except OSError as err:
        print("OS error: {0}".format(err))
        # client.disconnect()
    print("exit")

if __name__ == "__main__":
    main()
