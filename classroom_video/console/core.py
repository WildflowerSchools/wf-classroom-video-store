from datetime import datetime
from multiprocessing.pool import ThreadPool
import os

import pymongo.errors
from tqdm import tqdm

from classroom_video.log import logger
from classroom_video.mongo.client import MongoClient
from classroom_video.mongo.models import ExistingRetentionRule, ExistingVideo


def delete_video(video_meta_data: ExistingVideo):
    video_meta_collection = MongoClient().connect().video_meta_collection()

    try:
        if os.path.exists(video_meta_data.full_path()):
            os.unlink(video_meta_data.full_path())

        video_meta_collection.delete_one({"_id": video_meta_data.id})
    except pymongo.errors.PyMongoError as e:
        logger.error(
            f"Failed removing video_meta record '{video_meta_data.id}' from MongoDB for environment '{video_meta_data.meta.environment_id}': {e}"
        )
    except OSError:
        logger.error(
            f"Failed deleting video for record '{video_meta_data.id}' at path '{video_meta_data.full_path()}' for environment '{video_meta_data.meta.environment_id}'"
        )


def delete_videos_for_environment(environment_id: str, expiration_datetime: datetime, dry=True):
    # Establish mongo connection if one hasn't yet been established
    mongo_session = MongoClient().connect()

    video_meta_collection = mongo_session.video_meta_collection()
    video_retention_collection = mongo_session.video_retention_collection()

    mongo_retention_filters = []
    for raw_retention_record in video_retention_collection.find({"environment_id": environment_id}):
        retention_record = ExistingRetentionRule.from_mongo(raw_retention_record)
        nor_filter = {"timestamp": {"$gte": retention_record.start, "$lte": retention_record.end}}

        if len(retention_record.camera_ids) > 0:
            nor_filter["meta.camera_id"] = {"$in": retention_record.camera_ids}

        mongo_retention_filters.append({"$nor": [nor_filter]})

    mongo_environment_filter = {
        "$and": [
            {"meta.environment_id": environment_id, "timestamp": {"$lt": expiration_datetime}},
            *mongo_retention_filters,
        ]
    }

    # video_meta_collection_count = video_meta_collection.count_documents(filter={
    #     "meta.environment_id": environment_id, "timestamp": {"$lt": expiration_datetime}
    # })
    # logger.info(f"Found {video_meta_collection_count} videos for '{environment_id}'")

    video_meta_collection_count_with_retention_filters = video_meta_collection.count_documents(
        filter=mongo_environment_filter
    )
    logger.info(
        f"Found {video_meta_collection_count_with_retention_filters} videos for removal from '{environment_id}'"
    )

    video_meta_data_for_removal = []
    for video in video_meta_collection.find(filter=mongo_environment_filter, batch_size=5000):
        video_meta_data_for_removal.append(ExistingVideo.from_mongo(video))

    logger.info(f"{'(DRY) ' if dry else ''}Removing {len(video_meta_data_for_removal)} videos from '{environment_id}'")
    if not dry:
        with ThreadPool(processes=16) as pool:
            with tqdm(total=len(video_meta_data_for_removal), desc=f"Removing '{environment_id}' video") as pbar:
                for _ in pool.imap_unordered(delete_video, video_meta_data_for_removal, chunksize=100):
                    pbar.update()
            pool.close()
            pool.join()
        logger.info(f"Finished removing videos from '{environment_id}'")
