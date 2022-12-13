from mongita import MongitaClientDisk

client = MongitaClientDisk()
hello_world_db = client.hello_world_db
mongoose_collection = hello_world_db.mongoose_collection
mongoose_collection.insert_many([{'name': 'Meercat', 'does_not_eat': 'Snakes'},
                                     {'name': 'Yellow mongoose', 'eats': 'Termites'}])
mongoose_collection.count_documents({})

mongoose_collection.update_one({'name': 'Meercat'}, {'$set': {"weight": 2}})

mongoose_collection.find({'weight': {'$gt': 1}})

list(mongoose_collection.find({'weight': {'$gt': 1}}))

mongoose_collection.delete_one({'name': 'Meercat'})
