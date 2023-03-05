import os

from bson.codec_options import CodecOptions
import pymongo
from pymongo import errors
import pytz


from .config import logger


MONGO_DATABASE = "video_storage"
MONGO_VIDEO_META_COLLECTION = "video_meta"
MONGO_VIDEO_RETENTION_COLLECTION = "video_retention"


class MongoClient:
    def __init__(self, host=None, port=None):
        self.host = host
        if self.host is None:
            self.host = os.getenv("WF_MONGODB_HOST")

        self.port = port
        if self.port is None:
            self.port = int(os.environ.get("WF_MONGODB_PORT", "27017"))

        self.client = None
        self.default_codec_options = CodecOptions(
            tz_aware=True,
            tzinfo=pytz.timezone('UTC'))

    def connect(self):
        if self.client is not None:
            return self.client

        self.client = pymongo.MongoClient(
            host=self.host,
            port=self.port,
            serverSelectionTimeoutMS=2500
        )

        try:
            self.client.admin.command('ping')
        except pymongo.errors.ConnectionFailure as e:
            logger.error("MongoDB server not available")
            raise e

        logger.info("Connected to MongoDB")
        self._migrate()
        return self

    def close(self):
        if self.client:
            self.client.close()
            self.client = None

    def __enter__(self, *args, **kwargs):
        self.connect()
        return self.client

    def __exit__(self, *args):
        self.close()

    def database(self):
        if self.client is None:
            raise ConnectionError("Connect must first be established before accessing database")

        return self.client[MONGO_DATABASE]

    def _get_collection(self, collection_name) -> pymongo.collection.Collection:
        if self.client is None:
            raise ConnectionError("Connect must first be established before accessing collections")

        return self.database()[collection_name].with_options(codec_options=self.default_codec_options)

    def video_meta_collection(self) -> pymongo.collection.Collection:
        return self._get_collection(MONGO_VIDEO_META_COLLECTION)

    def video_retention_collection(self) -> pymongo.collection.Collection:
        return self._get_collection(MONGO_VIDEO_RETENTION_COLLECTION)

    def _migrate(self):
        logger.info("Running MongoDB migrations...")
        db = self.database()

        try:
            known_collections = db.list_collection_names()
            if MONGO_VIDEO_META_COLLECTION not in known_collections:
                db.create_collection(MONGO_VIDEO_META_COLLECTION)

            if MONGO_VIDEO_RETENTION_COLLECTION not in known_collections:
                db.create_collection(MONGO_VIDEO_RETENTION_COLLECTION)
        except pymongo.errors.PyMongoError as e:
            logger.error(f"Failed creating mongo collection: {e}")
            raise e

        video_meta_collection = self.video_meta_collection()
        video_meta_collection.create_index([('meta.path', pymongo.ASCENDING)], unique=True)
        video_meta_collection.create_index([('timestamp', pymongo.ASCENDING), ("meta.environment_id", pymongo.ASCENDING), ("meta.camera_id", pymongo.ASCENDING)])
        logger.info("Finishing running MongoDB migrations")


mongo_session = MongoClient()
