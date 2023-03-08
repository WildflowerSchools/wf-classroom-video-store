import os

from bson.codec_options import CodecOptions
import pymongo
import pytz


from classroom_video.log import logger


MONGO_DATABASE = "video_storage"
MONGO_VIDEO_META_COLLECTION = "video_meta"
MONGO_VIDEO_RETENTION_COLLECTION = "video_retention"


class MongoClient:
    __instance = None

    def __new__(cls):
        # pylint: disable=access-member-before-definition
        # pylint: disable=protected-access

        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance.__initialized = False
        return cls.__instance

    def __init__(
        self,
        host: str = None,
        port: int = None,
        username: str = None,
        password: str = None,
        direct_connection: bool = None,
    ):
        # pylint: disable=access-member-before-definition
        if self.__initialized:
            return
        self.__initialized = True

        self.host = host
        if self.host is None:
            self.host = os.getenv("WF_MONGODB_HOST", "localhost")

        self.is_host_uri = "/" in self.host
        self.additional_mongo_args = {}

        if not self.is_host_uri:
            self.additional_mongo_args["port"] = port
            if self.additional_mongo_args["port"] is None:
                self.additional_mongo_args["port"] = int(os.environ.get("WF_MONGODB_PORT", "27017"))

            self.additional_mongo_args["directConnection"] = direct_connection
            if self.additional_mongo_args["directConnection"] is None:
                self.additional_mongo_args["directConnection"] = os.environ.get(
                    "WF_MONGODB_DIRECT_CONNECTION", "False"
                ).lower() in ["true", "1", "t", "y"]

            self.additional_mongo_args["username"] = username
            if self.additional_mongo_args["username"] is None:
                self.additional_mongo_args["username"] = os.environ.get("WF_MONGODB_USERNAME")

            self.additional_mongo_args["password"] = password
            if self.additional_mongo_args["password"] is None:
                self.additional_mongo_args["password"] = os.environ.get("WF_MONGODB_PASSWORD")

            # Forced to use this args dict to workaround annoying Mongo logic when not auth'ing with a USERNAME
            if self.additional_mongo_args["username"] is not None:
                self.additional_mongo_args["authMechanism"] = "SCRAM-SHA-256"

        self.client = None
        self.default_codec_options = CodecOptions(tz_aware=True, tzinfo=pytz.timezone("UTC"))

    def _connection_string(self):
        return f"Host: '{self.host}' - Add'l Conn Args:'{self.additional_mongo_args}'"

    def connect(self):
        if self.client is not None:
            return self

        self.client = pymongo.MongoClient(host=self.host, serverSelectionTimeoutMS=2500, **self.additional_mongo_args)

        try:
            self.client.admin.command("ping")
        except pymongo.errors.ConnectionFailure as e:
            logger.error(f"MongoDB server not available: {self._connection_string()}")
            raise e

        logger.info(f"Connected to MongoDB: {self._connection_string()}")
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
        video_meta_collection.create_index([("meta.path", pymongo.ASCENDING)], unique=True)
        video_meta_collection.create_index(
            [
                ("timestamp", pymongo.ASCENDING),
                ("meta.environment_id", pymongo.ASCENDING),
                ("meta.camera_id", pymongo.ASCENDING),
            ]
        )
        logger.info("Finishing running MongoDB migrations")
