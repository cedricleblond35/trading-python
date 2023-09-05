import math as math
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from Service.Email import Email
from Configuration.Log import Log
from Service.TransactionSide import TransactionSide




class Order:
    def __init__(self, symbol, dbStreaming, client, dbTrade):
        email = Email()
        self.symbol = symbol
        self.dbStreaming = dbStreaming
        self.dbTrade = dbTrade
        self.client = client
        l = Log()
        self.logger = l.getLogger()

    ################## ordre avec limit #################################################
    def buyLimit(self,  sl, tp, price, balance, vnl, comment="buyLimit"):
        try:
            h = self.client.commandExecute('getServerTime')
            timeExpiration = h['returnData']['time'] + 3600000

            nbrelot = NbrLot(self.logger,balance, price, sl, vnl)
            print("**************comment :", comment)
            detail = {
                "cmd": TransactionSide.BUY_LIMIT,
                "customComment": comment,
                "expiration": timeExpiration,
                "offset": 0,
                "price": price,
                "sl": sl,
                "symbol": self.symbol,
                "tp": tp,
                "type": TransactionSide.OPEN,
                "volume": nbrelot
            }
            print("**************buy limit :", detail)
            resp = self.client.commandExecute('tradeTransaction', {"tradeTransInfo": detail})
            detail['resp'] = resp
            detail['comment'] = comment
            print("retour dee l ordre:",resp)
            self.dbTrade.insert_one(detail)
            self.logger.info(detail)

        except Exception as exc:
            self.logger.warning(exc)

    def sellLimit(self,  sl, tp, price, balance, vnl, comment="sellLimit"):
        try:
            h = self.client.commandExecute('getServerTime')
            timeExpiration = h['returnData']['time'] + 3600000
            print("**************comment :", comment)

            nbrelot = NbrLot(self.logger,balance, price, sl, vnl)
            detail = {
                "cmd": TransactionSide.SELL_LIMIT,
                "customComment": comment,
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
            #self.logger.info"detail :", detail)
            resp = self.client.commandExecute('tradeTransaction', {"tradeTransInfo": detail})
            detail['resp'] = resp
            self.dbTrade.insert_one(detail)
            print("retour dee l ordre:", resp)
            self.logger.info(detail)
        except Exception as exc:
            self.logger.warning(exc)

    ################### ordre direct ##################################################
    def sellNow(self, sl, tp, price, balance, vnl, comment=""):
        h = self.client.commandExecute('getServerTime')
        timeExpiration = h['returnData']['time'] + 3600000
        nbrelot = NbrLot(self.logger,balance, price, sl, vnl)
        detail = {
            "cmd": TransactionSide.SELL,
            "customComment": comment,
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
        detail['comment'] = comment
        self.dbTrade.insert_one(detail)
        self.logger.info(detail)
        '''
        respString = json.dumps(resp) + "forex robot Action"
        detailString = json.dumps(detail)
        self.sendMail(respString, detailString)
        '''

    def buyNow(self, sl, tp, price, balance, vnl, comment=""):
        # tp = round(tp, 1)
        # sl = round(sl, 1)
        h = self.client.commandExecute('getServerTime')
        timeExpiration = h['returnData']['time'] + 3600000
        nbrelot = NbrLot(self.logger,balance, price, sl, vnl)
        detail = {
            "cmd": 0,
            "customComment": comment,
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
        detail['comment'] = comment
        self.dbTrade.insert_one(detail)
        self.logger.info(detail)

    ############################ move stop après ordre executé ###########################

    def moveStopBuy(self, trade, sl, tick):
        try:
            if sl > trade["sl"]:

                detail = {
                     "order": trade['order'],
                    "customComment": trade["customComment"],
                     "sl": sl,
                     "price":  tick,
                     "symbol": trade["symbol"],
                     "volume": trade["volume"],
                     "tp": trade["tp"],
                     "type": TransactionSide.MODIFY
                 }
                print("moveStopBuy :", detail)
                resp = self.client.commandExecute('tradeTransaction', {"tradeTransInfo": detail})
                print("retour dee l ordre:", resp)
                self.logger.info(detail)

        except Exception as exc:
            self.logger.warning(exc)

    def moveStopSell(self, trade, sl, tick):
        try:
            if sl < trade["sl"]:
                detail = {
                     "order": trade['order'],
                    "customComment": trade["customComment"],
                     "sl": sl,
                     "price": tick,  # TICK["bid"],
                     "symbol": trade["symbol"],
                     "volume": trade["volume"],
                     "tp": trade["tp"],
                     "type": TransactionSide.MODIFY
                }
                print("moveStopSell :", detail)
                resp = self.client.commandExecute('tradeTransaction', {"tradeTransInfo": detail})
                print("retour dee l ordre:", resp)
                self.logger.info(detail)
        except Exception as exc:
            self.logger.warning(exc)

    ###############################################################

    def movebuyLimit(self,trade, sl , tp, price, balance):
        try:

            # print("------------- movebuyLimit -----------------")
            # tp = round(tp, 1)
            # sl = round(sl, 1)

            h = self.client.commandExecute('getServerTime')
            timeExpiration = h['returnData']['time'] + 3600000

            nbrelot = NbrLot(self.logger,balance, price, sl)
            detail = {
                  "cmd": trade['order'],
                "customComment": trade["customComment"],
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
            print("retour dee l ordre:", resp)
            #self.logger.info("resp :", resp)
        except Exception as exc:
            self.logger.warning(exc)

    def movebuyLimitWait(self,trade, sl, tp, price, balance, vnl, comment=""):
        try:
            print("------------- movebuyLimitWait ************************-----------------")
            print("trade :", trade)
            # tp = round(tp, 1)
            # sl = round(sl, 1)

            nbrelot = NbrLot(self.logger,balance, price, sl, vnl)
            if float(trade['volume']) == nbrelot:
                detail = {
                          "cmd": trade['cmd'],
                    "customComment": trade["customComment"],
                          "order": trade['order'],
                          "sl": sl,
                          "price": price,  # TICK["bid"],
                          "symbol": self.symbol,
                          "volume": nbrelot,
                          "tp": tp,
                          "type": 3
                      }
                print("***************movebuyLimitWait :",detail)
                resp = self.client.commandExecute('tradeTransaction', { "tradeTransInfo": detail})
                print("retour dee l ordre:", resp)
            else:
                print("delete order buy !!!!!!!!!!!! because volume is differente")
                detail = {
                    "cmd": trade['cmd'],
                    "order": trade['order'],
                    "sl": sl,
                    "price": price,  # TICK["bid"],
                    "symbol": self.symbol,
                    "volume": nbrelot,
                    "tp": tp,
                    "type": 4
                }
                print("detail :", detail)
                resp = self.client.commandExecute('tradeTransaction', {"tradeTransInfo": detail})
                print("retour dee l ordre:", resp)


                #new order
                h = self.client.commandExecute('getServerTime')
                timeExpiration = h['returnData']['time'] + 3600000

                nbrelot = NbrLot(self.logger,balance, price, sl, vnl)
                print("**************comment :", comment)
                detail = {
                    "cmd": TransactionSide.BUY_LIMIT,
                    "customComment": trade["customComment"],
                    "expiration": timeExpiration,
                    "offset": 0,
                    "price": price,
                    "sl": sl,
                    "symbol": self.symbol,
                    "tp": tp,
                    "type": TransactionSide.OPEN,
                    "volume": nbrelot
                }
                print("**************buy limit :", detail)
                resp = self.client.commandExecute('tradeTransaction', {"tradeTransInfo": detail})
                detail['resp'] = resp
                detail['comment'] = comment
                print("retour dee l ordre:", resp)
                self.dbTrade.insert_one(detail)

            #self.logger.info("resp :", resp)
        except Exception as exc:
            self.logger.warning(exc)

    def moveSellLimitWait(self,trade, sl , tp, price, balance, vnl):
        self.logger.info("------------- moveSellLimit ************************-----------------")
        print("trade :", trade)
        # tp = round(tp, 1)
        # sl = round(sl, 1)
        nbrelot = NbrLot(self.logger,balance, price, sl, vnl)
        print(float(trade['volume']) ,"==", nbrelot)

        if float(trade['volume']) == nbrelot:
            print("move order sell !!!!!!!!!!!!")
            resp = self.client.commandExecute('tradeTransaction',
                                         {
                                             "tradeTransInfo":
                                                 {
                                                     "cmd": trade['cmd'],
                                                     "customComment": trade["customComment"],
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
            resp = self.client.commandExecute('tradeTransaction',
                                              {
                                                  "tradeTransInfo":
                                                      {
                                                          "cmd": trade['cmd'],
                                                          "order": trade['order'],
                                                          "sl": sl,
                                                          "price": price,  # TICK["bid"],
                                                          "symbol": self.symbol,
                                                          "volume": nbrelot,
                                                          "tp": tp,
                                                          "type": 4
                                                      }
                                              })
            h = self.client.commandExecute('getServerTime')
            timeExpiration = h['returnData']['time'] + 3600000
            print("**************comment :", trade["customComment"])

            nbrelot = NbrLot(self.logger,balance, price, sl, vnl)
            detail = {
                "cmd": TransactionSide.SELL_LIMIT,
                "customComment": trade["customComment"],
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
            # self.logger.info"detail :", detail)
            resp = self.client.commandExecute('tradeTransaction', {"tradeTransInfo": detail})
            detail['resp'] = resp
            print("retour dee l ordre:", resp)
            self.dbTrade.insert_one(detail)

    def delete(self, trade):
        detail = {
            "cmd": trade['cmd'],
            "order": trade['order'],
            "symbol": self.symbol,
            "type": TransactionSide.DELETE
        }
        print("detail :", detail)
        resp = self.client.commandExecute('tradeTransaction', {"tradeTransInfo": detail})
        print("resp delete:", resp)

def NbrLot(logger,balance, position, stp, vnl):
    '''
    Calcul le nombre de posible à prendre
    GER30 : 2,5 € de perte max, Stop loss : 10, valeur nominale du lot : 25 €
    calcul: 2,5 / 10 / 25 = 0,01 lot

    NASDAQ : 2,5 de perte, Stop loss : 10, vaLeur nominale du lot : 20 $  mettre 35
    calcul : 2,5 / 10 / 35 =

    Calcul de lot EURO/USD
    ---------------
    1 lot Forex équivaut à 100 000
    Un pip sur la paire de devises EUR/USD vaut 20 USD par lot.

    si l euro/usd vaut 1.0745 donc le VNL = 1 lot/1.0745€/10 = 9.30€

    9.30€ / pip / lot
    pip 0.0001

    18.6 pip cout 173 pour 1 lot
    VLN*nbre de pip= valeur
    9.30*18.1 = 172.9€

    pour 0.5 lot:
    9.30*18.5*0.5= 86.5€
    nombre de lot pour 90€ de perte:  90€/(9.30*18.5pip) = 0.52

    '''
    try:
        print("calcul du nombre de lot #############################################################################")
        print("balance :", balance)
        perteAcceptable = round(balance * 0.03, 0)
        vln = round(1/position/10, 2)

        valeurContrat = position*vnl*1       #valeur_contrat pour 1 lot
        levier = 20

        print("perteAcceptable :", perteAcceptable)
        print("position :", position)
        print("stp :", stp)
        print("vnl :", vnl)
        ecartPip = abs((position - stp)*10000)

        print("ecart type :", ecartPip)
        #nbrelot = round(perteAcceptable / ecartPip / vnl, 2 )
        nbrelot = round( perteAcceptable/(vln*ecartPip), 2)

        lotMaxPossible = round_down(balance * levier / valeurContrat, 2)
        print("lotMaxPossible :", lotMaxPossible)
        if nbrelot > lotMaxPossible:
            nbrelot = lotMaxPossible

        """
        qtMax = self.round_down((balance["equityFX"] / 20000), 2)
        if nbrelot > qtMax:
            nbrelot = qtMax
        """
        print("nombre de lot:", nbrelot)
        print(
            "calcul du nombre de lot #############################################################################")


        return nbrelot


    except Exception as exc:
        logger.warning(exc)


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
