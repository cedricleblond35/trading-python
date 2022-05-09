from Configuration.Config import Config

import json
import math as math

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from Service.Email import Email


class Order():
    def __init__(self, symbol, dbStreaming, client):
        email = Email()
        self.symbol = symbol
        self.dbStreaming = dbStreaming
        self.client = client

    def achatDirect(self, tp, sl):
        print(
            "------------------------------- achat direct 1--------------------------------------------")

        balance = self.dbStreaming["Balance"].find_one({"_id": Config.USER_ID})
        self.email.sendMail("forex robot Action", "Prise de postion -- Achat 1")
        # print("ask :", float(TICK["ask"]), ">", superT1, " and ", bougie2['close'], "<", superT1)

        tp = round(tp, 1)
        sl = round(sl - 5.0, 1)
        tick = self.dbStreaming["Tick"].find_one({"symbol": self.symbol})
        price = tick["bid"]

        h = self.client.commandExecute('getServerTime')
        timeExpiration = h['returnData']['time'] + 3600000

        if tp - price > 10:
            nbrelot = self.NbrLot(balance, price, sl)
            self.buyNow(self.client, timeExpiration, price, sl, self.symbol, tp, nbrelot)

    def venteDirect(self, supportDown, supportHight, superM01T0):
        print(
                "------------------------------- vente direct 1 --------------------------------------------")
        balance = self.dbStreaming["Balance"].find_one({"_id": Config.USER_ID})
        #self.sendMail("forex robot Action", "Prise de postion -- Vente 1")
        tick = self.dbStreaming["Tick"].find_one({"symbol": self.symbol})

        sl = round(superM01T0 + 5.0, 1)
        tp = round(supportDown, 1)
        price = tick["ask"]

        h = self.client.commandExecute('getServerTime')
        timeExpiration = h['returnData']['time'] + 3600000

        if price - tp > 10:
            nbrelot = self.NbrLot(balance, price, sl)
            self.sellNow(self.client, timeExpiration, price, sl, self.symbol, tp, nbrelot)

    def NbrLot(self, balance, position, stp):
        '''
        Calcul le nombre de posible à prendre
        :param balance:
        :param position:
        :param stp:
        :return:
        '''
        try:
            perteAcceptable = round(balance["equityFX"] * 0.01, 0)
            # ecartPip = position - (position - stp)
            ecartPip = abs((position - stp))
            # print("ecartPip :", ecartPip)
            nbrelot = perteAcceptable / ecartPip / (1000 / 100) / 100
            # print("nbre de lot :", nbrelot)
            qtMax = self.round_down((balance["equityFX"] / 20000), 2)
            if nbrelot > qtMax:
                nbrelot = qtMax

            print('//////////////////////////////////// NbrLot ////////////////////////////////////')
            print('balance :', balance["equityFX"])
            print('position :', position)
            print('stp :', stp)
            print('perteAcceptable :', perteAcceptable)
            print('ecartPip :', ecartPip)
            print('nbrelot :', nbrelot)
            print('//////////////////////////////////// NbrLot ////////////////////////////////////')

            return round(nbrelot, 2)
        except (RuntimeError, TypeError, NameError):
            pass

    def sellNow(self, client, timeExpiration, price, sl, symbol, tp, nbrelot):
        detail = {"tradeTransInfo": {
            "cmd": 1,
            "customComment": "Vente direct",
            "expiration": timeExpiration,
            "offset": 0,
            "price": price,
            "sl": sl,
            "symbol": symbol,
            "tp": tp,
            "type": 0,
            "volume": nbrelot
        }}
        resp = client.commandExecute('tradeTransaction', detail)
        respString = json.dumps(resp) + "forex robot Action"
        detailString = json.dumps(detail)
        #self.sendMail(respString, detailString)

    def buyNow(self, client, timeExpiration, price, sl, symbol, tp, nbrelot):
        '''
        Achat immediat
        :param client:
        :param time:
        :param price:
        :param sl:
        :param symbol:
        :param tp:
        :param nbrelot:
        :return:
        '''
        detail = {
            "cmd": 0,
            "customComment": "Achat direct",
            "expiration": timeExpiration,
            "offset": 0,
            "price": price,
            "sl": sl,
            "symbol": symbol,
            "tp": tp,
            "type": 0,
            "volume": nbrelot
        }
        # print(detail)
        resp = client.commandExecute('tradeTransaction', {"tradeTransInfo": detail})
        # print("|||||||||||||||||||| resp :", resp)
        respString = json.dumps(resp) + "forex robot Action"
        detailString = json.dumps(detail)
        #self.sendMail(respString, detailString)

    def buyLimit(self, sl, tp, price):

        print("------------- buyLimit -----------------")
        tp = round(tp, 1)
        sl = round(sl, 1)

        h = self.client.commandExecute('getServerTime')
        timeExpiration = h['returnData']['time'] + 3600000

        balance = self.dbStreaming["Balance"].find_one({"_id": Config.USER_ID})
        nbrelot = self.NbrLot(balance, price, sl)
        detail = {
            "cmd": 2,
            "customComment": "Achat limit",
            "expiration": timeExpiration,
            "offset": 0,
            "price": price,
            "sl": sl,
            "symbol": self.symbol,
            "tp": tp,
            "type": 0,
            "volume": nbrelot
        }
        print("detail :", detail)
        resp = self.client.commandExecute('tradeTransaction', {"tradeTransInfo": detail})
        # print("|||||||||||||||||||| resp :", resp)
        respString = json.dumps(resp) + "forex robot Action"
        detailString = json.dumps(detail)
        #self.sendMail(respString, detailString)

    def movebuyLimit(self,trade, sl , tp, price):
        print("------------- movebuyLimit -----------------")
        tp = round(tp, 1)
        sl = round(sl, 1)

        h = self.client.commandExecute('getServerTime')
        timeExpiration = h['returnData']['time'] + 3600000

        balance = self.dbStreaming["Balance"].find_one({"_id": Config.USER_ID})
        nbrelot = self.NbrLot(balance, price, sl)
        detail = {
              "cmd": 2,
              "order": trade['order'],
              "sl": sl,
              "price": price,  # TICK["bid"],
              "symbol": self.symbol,
              "volume": nbrelot,
              "tp": tp,
              "type": 3

        }
        print("detail :", detail)
        resp = self.client.commandExecute('tradeTransaction',  {"tradeTransInfo": detail })
        print("resp :", resp)

    def movebuyLimitWait(self,trade, sl , tp, price):
        print("------------- movebuyLimitWait ************************-----------------")
        tp = round(tp, 1)
        sl = round(sl, 1)
        print("trade :", trade)

        balance = self.dbStreaming["Balance"].find_one({"_id": Config.USER_ID})
        nbrelot = self.NbrLot(balance, price, sl)
        detail = {
                                                      "cmd": 2,
                                                      "order": trade['order'],
                                                      "sl": sl,
                                                      "price": price,  # TICK["bid"],
                                                      "symbol": self.symbol,
                                                      "volume": nbrelot,
                                                      "tp": tp,
                                                      "type": 3
                                                  }
        print(detail)
        resp = self.client.commandExecute('tradeTransaction', { "tradeTransInfo": detail})
        print("resp :", resp)

    def moveStopBuy(self, trade, sl):
        print("new sl :", sl)
        print("old sl", trade["sl"])
        if sl > trade["sl"]:
            tick = self.dbStreaming["Tick"].find_one({"symbol": self.symbol})
            resp = self.client.commandExecute('tradeTransaction',
                                         {
                                             "tradeTransInfo":
                                                 {
                                                     "order": trade['order'],
                                                     "sl": sl,
                                                     "price":  tick["ask"],
                                                     "symbol": trade["symbol"],
                                                     "volume": trade["volume"],
                                                     "tp": trade["tp"],
                                                     "type": 3
                                                 }
                                         })
            print("resp :", resp)

    def moveStopSell(self, trade, sl):
        print("*********** moveStopSell *************")
        print("new sl :", sl)
        print("old sl", trade["sl"])
        if sl < trade["sl"]:
            tick = self.dbStreaming["Tick"].find_one({"symbol": self.symbol})
            resp = self.client.commandExecute('tradeTransaction',
                                              {
                                                  "tradeTransInfo":
                                                      {
                                                          "order": trade['order'],
                                                          "sl": sl,
                                                          "price": tick["ask"],
                                                          "symbol": trade["symbol"],
                                                          "volume": trade["volume"],
                                                          "tp": trade["tp"],
                                                          "type": 3
                                                      }
                                              })
            print("resp :", resp)

    def sellLimit(self, sl, tp, price):
        print("------------- sellLimit -----------------")
        tp = round(tp, 1)
        sl = round(sl, 1)

        h = self.client.commandExecute('getServerTime')
        timeExpiration = h['returnData']['time'] + 3600000

        balance = self.dbStreaming["Balance"].find_one({"_id": Config.USER_ID})
        nbrelot = self.NbrLot(balance, price, sl)
        nbrelot = 0.10
        detail = {
            "cmd": 3,
            "customComment": "vente limit",
            "expiration": timeExpiration,
            "offset": 0,
            "price": price,
            "sl": sl,
            "symbol": self.symbol,
            "tp": tp,
            "type": 0,
            "volume": nbrelot
        }
        print("detail :", detail)
        resp = self.client.commandExecute('tradeTransaction', {"tradeTransInfo": detail})
        respString = json.dumps(resp) + "forex robot Action"
        detailString = json.dumps(detail)
        #self.sendMail(respString, detailString)

    def moveSellLimitWait(self,trade, sl , tp, price):
        print("------------- moveSellLimit ************************-----------------")
        tp = round(tp, 1)
        sl = round(sl, 1)

        balance = self.dbStreaming["Balance"].find_one({"_id": Config.USER_ID})
        nbrelot = self.NbrLot(balance, price, sl)
        resp = self.client.commandExecute('tradeTransaction',
                                     {
                                         "tradeTransInfo":
                                             {
                                                 "cmd": 3,
                                                 "order": trade['order'],
                                                 "sl": sl,
                                                 "price": price , # TICK["bid"],
                                                 "symbol": self.symbol,
                                                 "volume": nbrelot,
                                                 "tp": tp,
                                                 "type": 3
                                             }
                                     })
        print("resp :", resp)

    def round_up(self, n, decimals=0):
        '''
        Arrondi au superieur
        :param n:
        :param decimals:
        :return:
        '''
        multiplier = 10 ** decimals
        return math.ceil(n * multiplier) / multiplier

    def round_down(self, n, decimals=0):
        '''
        Arrondi à l inférieur
        :param n:
        :param decimals:
        :return:
        '''
        multiplier = 10 ** decimals
        return math.floor(n * multiplier) / multiplier

    def sendMail(self, subject, message):
        msg = MIMEMultipart()
        msg['From'] = 'drick35@gmail.com'
        msg['To'] = 'drick35@gmail.com'
        msg['Subject'] = subject
        message = message
        msg.attach(MIMEText(message))
        mailserver = smtplib.SMTP('smtp.gmail.com', 587)
        mailserver.ehlo()
        mailserver.starttls()
        mailserver.ehlo()
        mailserver.login('drick35@gmail.com', 'hdfykpdsoireyedl')
        mailserver.sendmail('drick35@gmail.com', 'drick35@gmail.com', msg.as_string())
        mailserver.quit()
        pass
