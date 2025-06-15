import glob
import os
import re
import time

from redis import Redis
from rq import Queue

from assayer.jobs.eval_job import launch_eval


def retrieve_checkpoints(directory, regex_filter):
    # filter files through filter function
    all_files = glob.glob(os.path.join(directory, "*"), recursive=True)  # list all files
    pattern = re.compile(regex_filter)
    filtered = [ckpt for ckpt in all_files if pattern.match(ckpt)]
    print("Current checkpoints: ", filtered)
    return filtered


def watch_job(
    existing_checkpoints,
    evaluator_path,
    watch_queue_name,
    eval_queue_name,
    polling_interval,
    directory,
    regex_filter,
    redis_host="localhost",
    redis_port=6379,
):
    redis = Redis(host=redis_host, port=redis_port)

    # fetch queues
    watch_q = Queue(watch_queue_name, connection=redis)
    eval_q = Queue(eval_queue_name, connection=redis)

    # check new checkpoints
    checkpoints = retrieve_checkpoints(directory, regex_filter)
    new_checkpoints = list(set(checkpoints).difference(set(existing_checkpoints)))

    # submit eval job
    print(f"New checkpoints found: {len(new_checkpoints)}")
    if len(new_checkpoints) > 0:
        for checkpoint in new_checkpoints:
            # NOTE: we don't launch any evals in case of deletions!
            # The state after deletion is treated as the new directory state to monitor
            # and if new checkpoints are added to this state, they are evaluated.
            if checkpoint not in existing_checkpoints:
                eval_q.enqueue(launch_eval, evaluator_path, checkpoint)

    # submit watch job
    time.sleep(polling_interval)
    watch_q.enqueue(
        watch_job,
        checkpoints,
        evaluator_path,
        watch_queue_name,
        eval_queue_name,
        polling_interval,
        directory,
        regex_filter,
        redis_host,
        redis_port,
        result_ttl=0,  # don't keep watch job results
    )
    return checkpoints
