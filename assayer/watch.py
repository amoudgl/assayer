import subprocess

from absl import app, flags, logging
from redis import Redis
from rq import Queue

from assayer.jobs.eval_job import launch_eval, load_evaluator_func_from_path
from assayer.jobs.watch_job import retrieve_checkpoints, watch_job

# fmt: off
flags.DEFINE_string("directory", None, "checkpoints directory")
flags.DEFINE_string("evaluator", None, "path to evaluation script")
flags.DEFINE_string("regex_filter", "^.*\.(pt|pth|ckpt|model|state)$", "regex to filter checkpoints in checkpoints directory")
flags.DEFINE_integer("num_eval_workers", 5, "number of RQ workers used to evaluate checkpoints")
flags.DEFINE_integer("num_watch_workers", 1, "number of RQ workers used to monitor checkpoint directory")
flags.DEFINE_integer("polling_interval", 5, "polling interval in seconds")
flags.DEFINE_string("watch_queue_name", "watch", "watch queue name")
flags.DEFINE_string("eval_queue_name", "evaluation", "evaluation queue")
flags.DEFINE_boolean("eval_existing", False, "if true, evaluate existing checkpoints in directory")
flags.DEFINE_string("redis_host", "localhost", "redis server host")
flags.DEFINE_integer("redis_port", 6379, "redis server port")
flags.mark_flag_as_required("directory")
flags.mark_flag_as_required("evaluator")
FLAGS = flags.FLAGS
# fmt: on


def start_rq_worker(queue_name="default"):
    subprocess.Popen(["rq", "worker", f"{queue_name}"])
    logging.info(f"launched RQ watch worker in queue: {queue_name}")


def main(unused_argv):
    # check if evaluator fn can be loaded from given path by user
    load_evaluator_func_from_path(FLAGS.evaluator)

    # setup redis connection
    redis = Redis(host=FLAGS.redis_host, port=FLAGS.redis_port)

    # start watch workers in background
    for i in range(FLAGS.num_watch_workers):
        start_rq_worker(FLAGS.watch_queue_name)

    # start eval workers in background
    for i in range(FLAGS.num_eval_workers):
        start_rq_worker(FLAGS.eval_queue_name)

    # fetch queues
    watch_q = Queue(FLAGS.watch_queue_name, connection=redis)
    eval_q = Queue(FLAGS.eval_queue_name, connection=redis)

    # check for existing checkpoints
    checkpoints = retrieve_checkpoints(FLAGS.directory, FLAGS.regex_filter)
    if FLAGS.eval_existing:
        for checkpoint in checkpoints:
            eval_q.enqueue(launch_eval, FLAGS.evaluator, checkpoint)

    # submit recursive watch job
    watch_q.enqueue(
        watch_job,
        checkpoints,
        FLAGS.evaluator,
        FLAGS.watch_queue_name,
        FLAGS.eval_queue_name,
        FLAGS.polling_interval,
        FLAGS.directory,
        FLAGS.regex_filter,
        FLAGS.redis_host,
        FLAGS.redis_port,
        result_ttl=0,  # don't keep watch job results
    )


if __name__ == "__main__":
    app.run(main)
