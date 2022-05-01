from Indicators.Price import Price


class MM(Price):
    def __init__(self, symbol, timeframe, duration):
        Price.__init__(self, symbol, timeframe)
        """
        constructor
        :param duration: 50
        :param indice: DE30
        :param period: H1
        """
        self.__timeframe = timeframe
        self.__duration = duration
        self._prepareListData(self.__duration)


    def calculSMA(self, duration):
        print("**************** start calcul SMA *********************")
        print("duration :", duration)
        nb = 0
        name = "SMA" + str(duration)
        # print("count :", len(self._listData))
        self._prepareListDataLast(0, 0, name)

        if (len(self._listData) - len(self._listDataLast)) == 0:
            start = 0
            print("calcul complet")
        else:
            start = len(self._listData) - len(self._listDataLast) - duration
            print("calcul partiel : ", start)

        print("calcul en cours ...  ")
        list = self._listData[start:len(self._listData)-1]
        print("nbre :", len(list))

        for v in list:
            nb = nb + 1  # numero necessaire pour debuter la moyenne  , ex : sma25 debute à partir de 26
            if nb >= duration and nb <= len(self._listData):
                somme = 0.00
                list1 = list.copy()[nb - duration : nb]
                b = 0
                for v1 in list1:
                    b = b + 1
                    somme = round(somme + v1["close"], 2)

                sma = round((somme / duration), 2)
                # if "sma" not in list(list1)[-1]:
                newvalues = {
                    "$set": {
                        name: sma
                    }}

                myquery = {"ctm": v["ctm"]}
                #print(newvalues)
                self._db[self.__timeframe].update_one(myquery, newvalues)

        #return sma

    def EMA(self, duration):
        """
        EMA = (CLOSE (i) * P) + (EMA (i - 1) * (1 - P))
        (prix de clôture – EMA du jour précédent) × constante pondérant la moyenne mobile exponentielle en décimale + EMA du jour précédent

        CLOSE (i) – prix de clôture de la période actuelle ;
        EMA (i - 1) – valeur de la Moyenne Mobile de la période précédente ;
        P – pourcentage d'utilisation de la valeur du prix.
        α = 2 / (n + 1)
        :return:
        """
       #print("**************** start calcul EMA *********************")

        name = "EMA" + str(duration)
        nameSMA = "SMA" + str(duration)
        α = round(2 / (duration + 1), 5)
        self._prepareListDataLast(0, 0, name)

        #print("calcul nombre ema :", len(self._listDataLast))

        #configurer le start et EMAPrecedent
        if len(self._listData) - len(self._listDataLast) == 0:
            #rien de rempli
            EMAPrecedent = 0
            start = 0
            # print("calcul complet :", start)
        else:
            #Des ema existant, on configure le EMAPrecedent et le start correctement
            # la 1ere ligne contient le sma ou ema precedent pour le calcul
            start = duration + len(self._listData) - len(self._listDataLast) -2
            idLastEma = start - 1
            EMAPrecedent = self._listData[idLastEma][name]
            # print("calcul partiel : ", start)

        #print("calcul en cours ...  ")
        list = self._listData[start:len(self._listData)-1]
        #print("nbre :", len(list))
        for i in range(0, len(list)):
            if EMAPrecedent > 0:
                close = list[i]["close"]
                ema = round( (close * α ) + ( EMAPrecedent * (1-α)) , 2)

                newvalues = {
                    "$set": {
                        name: round(ema, 2)
                    }}
                myquery = {"ctm": list[i]["ctm"]}
                self._db[self.__timeframe].update_one(myquery, newvalues)

                EMAPrecedent = ema

            elif nameSMA in list[i]:
                newvalues = {
                    "$set": {
                        name: list[i][nameSMA]
                    }}
                myquery = {"ctm": list[i]["ctm"]}
                self._db[self.__timeframe].update_one(myquery, newvalues)

                EMAPrecedent = list[i][nameSMA]

        #return ema

        # if typeCalcul is "all":
        #     EMAPrecedent = 0
        #     for i in range(0, len(self._listData)):
        #         #nb = nb + 1  # numero necessaire pour debuter la moyenne  , ex : sma25 debute à partir de 26
        #         #if i > 1:
        #         if EMAPrecedent > 0:
        #             #print("------------------------------ EMA precedent trouvé")
        #             close = self._listData[i]["close"]
        #             ema = round( (close * α ) + ( EMAPrecedent * (1-α)) , 2)
        #
        #             newvalues = {
        #                 "$set": {
        #                     name: round(ema, 2)
        #                 }}
        #             myquery = {"ctm": self._listData[i]["ctm"]}
        #             self._db[self.__timeframe].update_one(myquery, newvalues)
        #
        #             EMAPrecedent = ema
        #
        #         elif nameSMA in self._listData[i]:
        #             newvalues = {
        #                 "$set": {
        #                     name: self._listData[i][nameSMA]
        #                 }}
        #             myquery = {"ctm": self._listData[i]["ctm"]}
        #             self._db[self.__timeframe].update_one(myquery, newvalues)
        #
        #             EMAPrecedent = self._listData[i][nameSMA]