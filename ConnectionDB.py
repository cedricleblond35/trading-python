from pymongo import MongoClient

class ConnectionDB:
    def __init__(self):
        self.__c = MongoClient('localhost', 27017)

    def getDB(self, db):
        return self.__c[db]

    def close(self):
        self.__c.close()