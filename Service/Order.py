from Configuration.Config import Config
import json
import math as math
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import sys
from Service.Email import Email
import logging
from Service.TransactionSide import TransactionSide


logger = logging.getLogger("jsonSocket")

class Order:
    def __init__(self, symbol, dbStreaming, client, dbTrade):
        email = Email()
        self.symbol = symbol
        self.dbStreaming = dbStreaming
        self.dbTrade = dbTrade
        self.client = client

    ################## ordre avec limit #################################################
    def buyLimit(self,  sl, tp, price, balance, vnl):
        try:
            tp = round(tp, 1)
            sl = round(sl, 1)

            h = self.client.commandExecute('getServerTime')
            timeExpiration = h['returnData']['time'] + 3600000

            nbrelot = NbrLot(balance, price, sl, vnl)
            detail = {
                "cmd": TransactionSide.BUY_LIMIT,
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
            print("buy limit :", detail)
            resp = self.client.commandExecute('tradeTransaction', {"tradeTransInfo": detail})
            detail['resp'] = resp
            self.dbTrade.insert_one(detail)

        except Exception as exc:
            logger.info("le programe a déclenché une erreur")
            logger.info("exception de mtype ", exc.__class__)
            logger.info("message", exc)
            sendMail("Erreur ordre", exc)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

    def sellLimit(self,  sl, tp, price, balance, vnl):
        try:
            h = self.client.commandExecute('getServerTime')
            timeExpiration = h['returnData']['time'] + 3600000

            nbrelot = NbrLot(balance, price, sl, vnl)
            detail = {
                "cmd": TransactionSide.SELL_LIMIT,
                "customComment": "Vente limit",
                "expiration": timeExpiration,
                "offset": 0,
                "price": price,
                "sl": sl,
                "symbol": self.symbol,
                "tp": tp,
                "type": TransactionSide.OPEN,
                "volume": nbrelot
            }
            print("sell limit :", detail)
            #logger.info("detail :", detail)
            resp = self.client.commandExecute('tradeTransaction', {"tradeTransInfo": detail})
            detail['resp'] = resp
            self.dbTrade.insert_one(detail)
        except Exception as exc:
            logger.info("le programe a déclenché une erreur")
            logger.info("exception de mtype ", exc.__class__)
            logger.info("message", exc)
            sendMail("Erreur ordre", exc)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.info(exc_type, fname, exc_tb.tb_lineno)

    ################### ordre direct ##################################################
    def sellNow(self, sl, tp, price, balance, vnl):
        tp = round(tp, 1)
        sl = round(sl, 1)

        h = self.client.commandExecute('getServerTime')
        timeExpiration = h['returnData']['time'] + 3600000
        nbrelot = NbrLot(balance, price, sl, vnl)
        detail = {
            "cmd": TransactionSide.SELL,
            "customComment": "Vente direct",
            "expiration": timeExpiration,
            "offset": 0,
            "price": price-50,
            "sl": sl,
            "symbol": self.symbol,
            "tp": tp,
            "type": 0,
            "volume": nbrelot
        }
        resp = self.client.commandExecute('tradeTransaction', {"tradeTransInfo": detail})

        detail['resp'] = resp
        self.dbTrade.insert_one(detail)
        '''
        respString = json.dumps(resp) + "forex robot Action"
        detailString = json.dumps(detail)
        self.sendMail(respString, detailString)
        '''


    def buyNow(self, sl, tp, price, balance, vnl):
        tp = round(tp, 1)
        sl = round(sl, 1)
        h = self.client.commandExecute('getServerTime')
        timeExpiration = h['returnData']['time'] + 3600000
        nbrelot = NbrLot(balance, price, sl, vnl)
        detail = {
            "cmd": 0,
            "customComment": "Achat direct",
            "expiration": timeExpiration,
            "offset": 0,
            "price": price+50,
            "sl": sl,
            "symbol": self.symbol,
            "tp": tp,
            "type": 0,
            "volume": nbrelot
        }
        resp = self.client.commandExecute('tradeTransaction', {"tradeTransInfo": detail})
        detail['resp'] = resp
        self.dbTrade .insert_one(detail)

    ############################ move stop après ordre executé ###########################

    def moveStopBuy(self, trade, sl, tick):
        try:
            if sl > trade["sl"]:

                detail = {
                     "order": trade['order'],
                     "sl": sl,
                     "price":  tick,
                     "symbol": trade["symbol"],
                     "volume": trade["volume"],
                     "tp": trade["tp"],
                     "type": TransactionSide.MODIFY
                 }
                print("moveStopBuy :", detail)
                resp = self.client.commandExecute('tradeTransaction', {"tradeTransInfo": detail})

        except Exception as exc:
            logger.info("le programe a déclenché une erreur")
            logger.info("exception de mtype ", exc.__class__)
            logger.info("message", exc)
            sendMail("Erreur ordre", exc)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.info(exc_type, fname, exc_tb.tb_lineno)

    def moveStopSell(self, trade, sl, tick):
        try:
            if sl < trade["sl"]:
                detail = {
                     "order": trade['order'],
                     "sl": sl,
                     "price": tick,  # TICK["bid"],
                     "symbol": trade["symbol"],
                     "volume": trade["volume"],
                     "tp": trade["tp"],
                     "type": TransactionSide.MODIFY
                }
                print("moveStopSell :", detail)
                resp = self.client.commandExecute('tradeTransaction', {"tradeTransInfo": detail})

                logger.info("resp moveStopSell:", resp)
        except Exception as exc:
            logger.info("le programe a déclenché une erreur")
            logger.info("exception de mtype ", exc.__class__)
            logger.info("message", exc)
            sendMail("Erreur ordre", exc)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.info(exc_type, fname, exc_tb.tb_lineno)

    ###############################################################

    def movebuyLimit(self,trade, sl , tp, price, balance):
        try:

            # print("------------- movebuyLimit -----------------")
            tp = round(tp, 1)
            sl = round(sl, 1)

            h = self.client.commandExecute('getServerTime')
            timeExpiration = h['returnData']['time'] + 3600000

            nbrelot = NbrLot(balance, price, sl)
            detail = {
                  "cmd": trade['order'],
                  "order": trade['order'],
                  "sl": sl,
                  "price": price,  # TICK["bid"],
                  "symbol": self.symbol,
                  "volume": nbrelot,
                  "tp": tp,
                  "type": 3

            }
            print("movebuyLimit :", detail)
            resp = self.client.commandExecute('tradeTransaction',  {"tradeTransInfo": detail })
            #logger.info("resp :", resp)
        except Exception as exc:
            logger.info("le programe a déclenché une erreur")
            logger.info("exception de mtype ", exc.__class__)
            logger.info("message", exc)
            sendMail("Erreur ordre", exc)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.info(exc_type, fname, exc_tb.tb_lineno)

    def movebuyLimitWait(self,trade, sl , tp, price, balance, vnl):
        try:
            logger.info("------------- movebuyLimitWait ************************-----------------")
            print("trade :", trade)
            tp = round(tp, 1)
            sl = round(sl, 1)
            nbrelot = NbrLot(balance, price, sl, vnl)

            if trade['volume'] == nbrelot:
                print("move order buy !!!!!!!!!!!!")
                detail = {
                                                              "cmd": trade['cmd'],
                                                              "order": trade['order'],
                                                              "sl": sl,
                                                              "price": price,  # TICK["bid"],
                                                              "symbol": self.symbol,
                                                              "volume": nbrelot,
                                                              "tp": tp,
                                                              "type": 3
                                                          }
                print("movebuyLimitWait :",detail)
                resp = self.client.commandExecute('tradeTransaction', { "tradeTransInfo": detail})
            else:
                print("delete order buy !!!!!!!!!!!! because volume is differente")
                detail = {
                    "cmd": trade['cmd'],
                    "order": trade['order'],
                    "type": 4
                  }
                print("detail :", detail)
                resp = self.client.commandExecute('tradeTransaction', {"tradeTransInfo": detail})
                print("resp :", resp)

            #logger.info("resp :", resp)
        except Exception as exc:
            logger.info("le programe a déclenché une erreur")
            logger.info("exception de mtype ", exc.__class__)
            logger.info("message", exc)
            sendMail("Erreur ordre", exc)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.info(exc_type, fname, exc_tb.tb_lineno)

    def moveSellLimitWait(self,trade, sl , tp, price, balance, vnl):
        logger.info("------------- moveSellLimit ************************-----------------")
        print("trade :", trade)
        tp = round(tp, 1)
        sl = round(sl, 1)
        nbrelot = NbrLot(balance, price, sl, vnl)

        if trade['volume'] == nbrelot:
            print("move order sell !!!!!!!!!!!!")
            resp = self.client.commandExecute('tradeTransaction',
                                         {
                                             "tradeTransInfo":
                                                 {
                                                     "cmd": trade['cmd'],
                                                     "order": trade['order'],
                                                     "sl": sl,
                                                     "price": price , # TICK["bid"],
                                                     "symbol": self.symbol,
                                                     "volume": nbrelot,
                                                     "tp": tp,
                                                     "type": 3
                                                 }
                                         })

        else:
            print("delete order sell !!!!!!!!!!!! because volume is differente")
            resp = self.client.commandExecute('tradeTransaction', {"tradeTransInfo": {
                "cmd": trade['cmd'],
                "order": trade['order'],
                "type": 4
            }})
            print("reponse :", resp)

def NbrLot(balance, position, stp, vnl):
    '''
    Calcul le nombre de posible à prendre
    GER30 : 2,5 € de perte max, Stop loss : 10, valeur nominale du lot : 25 €
    calcul: 2,5 / 10 / 25 = 0,01 lot

    NASDAQ : 2,5 de perte, Stop loss : 10, vaLeur nominale du lot : 20 $  mettre 35
    calcul : 2,5 / 10 / 35 =

    '''
    try:
        print("calcul du nombre de lot #############################################################################")
        print("balance :", balance)
        print("vnl :", vnl)
        perteAcceptable = round(balance * 0.05, 0)

        print("perteAcceptable :", perteAcceptable)
        print("position :", position)
        print("stp :", stp)
        ecartPip = abs((position - stp))

        print("ecart type :", ecartPip)
        nbrelot = perteAcceptable / ecartPip / vnl
        print("nbrelot :", nbrelot)
        """
        qtMax = self.round_down((balance["equityFX"] / 20000), 2)
        if nbrelot > qtMax:
            nbrelot = qtMax
        """
        print(
            "calcul du nombre de lot #############################################################################")


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


def sendMail(subject, message):
    msg = MIMEMultipart()
    msg['From'] = 'cedricleb35@gmail.com'
    msg['To'] = 'cedricleb35@gmail.com'
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
