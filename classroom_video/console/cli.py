import click
from datetime import datetime, time, timedelta
import pytz
import os

from dotenv import load_dotenv

from classroom_video.honeycomb_service import HoneycombCachingClient
from classroom_video.log import logger
from classroom_video.mongo.client import MongoClient

from .core import delete_videos_for_environment



@click.group()
@click.option("--env-file", type=click.Path(exists=True), help="env file to load environment_name variables from. Defaults to .env")
def cli(env_file):
    if env_file is None:
        env_file = os.path.join(os.getcwd(), ".env")

    if os.path.exists(env_file):
        load_dotenv(dotenv_path=env_file)


@cli.command()
@click.option('--retention-delta', default=30, type=click.IntRange(0,), help='Number of days of videos to retain. Note if 0 is provided, the current day''s videos will be retained (i.e. retention_days doesn''t include today). Anything older than the provided value will be permanently removed.')
@click.option('--environment-id', 'environment_ids', default=[], multiple=True, help='Environment ID to run deletions against. If none provided, videos across all environments will be removed')
@click.option('--dry', is_flag=True)
def delete_video(retention_delta, environment_ids, dry):
    """Remove videos from the video store. Use --retention-delta to specify how many days videos can remain in storage.
    Videos older than this will be removed UNLESS retention rules have been added."""
    retention_delta += 1

    # Attempt to establish Mongo connection
    MongoClient().connect()

    # Fetch all honeycomb environments
    environments = HoneycombCachingClient().fetch_all_environments(output_format="list")

    for environment in environments:
        if len(environment_ids) > 0 and environment['environment_id'] not in environment_ids:
            continue

        if environment['timezone_name'] is None or environment['timezone_name'] == "":
            logger.warning(f"Will not delete '{environment['name']}' ({environment['environment_id']}) videos, environment has not specified a timezone")
            continue

        # Get midnight in each environment's timezone as UTC time, then subtract the specified retention delta
        expiration_datetime = pytz.timezone(environment['timezone_name']).localize(datetime.combine(datetime.today(), time.max)).astimezone(pytz.utc) - timedelta(days=retention_delta)

        logger.info(f"Removing '{environment['name']}' ({environment['environment_id']}) videos older than {expiration_datetime}")
        delete_videos_for_environment(environment_id=environment['environment_id'], expiration_datetime=expiration_datetime, dry=dry)
