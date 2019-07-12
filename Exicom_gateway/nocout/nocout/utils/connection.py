import pymongo

def mongo_conn():
        """
        Mongodb connection function
        Args: Multiple arguments for connection
        Kwargs: None
        Return : Database object
        
        Raise:
                Exception : PymongoError
        """
        DB = None
        try:
                CONN = pymongo.Connection(
                host="127.0.0.1",
                port=27017
                )
                DB = CONN["my_db"]
        except pymongo.errors.PyMongoError, e:
                raise pymongo.errors.PyMongoError, e
        return DB


rt=mongo_conn()
print rt
