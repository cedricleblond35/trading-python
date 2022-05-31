#!/usr/bin/python3
from pymongo import MongoClient

Client = MongoClient()
myclient = MongoClient('localhost', 27017)

my_database = myclient["US100"]
my_collection = my_database["D"]


essai = my_collection.find().count()
print(essai)
# number of documents in the collection
total_count = my_collection.count_documents({})
print("Total number of documents : ", total_count)