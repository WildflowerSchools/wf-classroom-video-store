from datetime import datetime
import math
import multiprocessing as mp
from multiprocessing.pool import ThreadPool
import os
import queue
import time

import pymongo.errors
from tqdm import tqdm

from classroom_video.log import logger
from classroom_video.mongo.client import MongoClient
from classroom_video.mongo.models import ExistingRetentionRule, ExistingVideo
from classroom_video.util import is_running_in_kubernetes


def delete_video(video_meta_data: ExistingVideo):
    video_meta_collection = MongoClient().connect().video_meta_collection()

    try:
        video_meta_data_path = video_meta_data.full_path()
        if os.path.exists(video_meta_data_path):
            os.unlink(video_meta_data_path)

        video_meta_collection.delete_one({"_id": video_meta_data.id})
    except pymongo.errors.PyMongoError as e:
        logger.error(
            f"Failed removing video_meta record '{video_meta_data.id}' from MongoDB for environment '{video_meta_data.meta.environment_id}': {e}"
        )
    except OSError:
        logger.error(
            f"Failed deleting video for record '{video_meta_data.id}' at path '{video_meta_data.full_path()}' for environment '{video_meta_data.meta.environment_id}'"
        )


def progress(num_tasks: int, completed_queue: mp.Queue, environment_id: str):
    completed = 0
    with tqdm(total=num_tasks, desc=f"Removing '{environment_id}' video") as progress_bar:
        while completed < num_tasks:
            if is_running_in_kubernetes() and (completed % math.ceil(num_tasks * 0.01)) == 0:
                logger.info(
                    f"Removing video for '{environment_id}' progress: {completed}/{num_tasks} ({str(round(completed/num_tasks * 100))}%)"
                )

            completed_queue.get()
            completed += 1
            progress_bar.update()


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

    if dry:
        logger.info(f"(DRY) Not deleting videos from '{environment_id}'")
        return

    def video_consumer(work_queue: mp.Queue, completed_queue: mp.Queue, stop_event):
        while True:
            if stop_event.is_set():
                break

            try:
                video_meta_data = work_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            delete_video(video_meta_data)
            completed_queue.put(1)

    manager = mp.Manager()
    work_queue = manager.Queue(maxsize=30000)
    completed_queue = manager.Queue()
    stop_event = mp.Event()

    # Launch the video_consumer threads. These consumers read work from the work_queue.
    thread_count = 8
    pool = ThreadPool(processes=thread_count)
    _ = [
        pool.apply_async(
            video_consumer,
            args=(
                work_queue,
                completed_queue,
                stop_event,
            ),
        )
        for _ in range(thread_count)
    ]

    # Start a separate process to track and report progress
    logger.info(
        f"Progress bar for video deletion starting for '{environment_id}'. To view in kubernetes, you will need to 'attach' to the pod"
    )
    progress_process = mp.Process(
        target=progress,
        args=(
            video_meta_collection_count_with_retention_filters,
            completed_queue,
            environment_id,
        ),
    )
    progress_process.start()

    # Fetch video_meta_data and add each record to the work_queue
    for video in video_meta_collection.find(filter=mongo_environment_filter, batch_size=5000):
        work_queue.put(ExistingVideo.from_mongo(video))

    # The work_queue has been loaded up with tasks. Now wait for the queue to reach 0.
    while True:
        time.sleep(0.5)
        if work_queue.qsize() == 0:
            break

    # Send a stop event to all worker threads
    stop_event.set()

    # Wait for worker_threads to wrap up
    pool.close()
    pool.join()

    # Stop the progress reporter process
    progress_process.terminate()
