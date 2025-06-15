from absl import app, flags, logging
from redis import Redis
from rq import Queue, Worker
from rq.command import send_shutdown_command

flags.DEFINE_string("redis_host", "localhost", "redis host")
flags.DEFINE_integer("redis_port", 6379, "redis port")
flags.DEFINE_string("watch_queue_name", "watch", "watch queue name")
flags.DEFINE_string("eval_queue_name", "evaluation", "evaluation queue")
FLAGS = flags.FLAGS


def main(unused_argv):
    redis = Redis(host=FLAGS.redis_host, port=FLAGS.redis_port)

    # empty all the queues
    queues = (
        Queue(f"{FLAGS.watch_queue_name}", connection=redis),
        Queue(f"{FLAGS.eval_queue_name}", connection=redis),
    )
    for q in queues:
        q.empty()

    # shutdown all the workers
    workers = Worker.all(redis)
    logging.info(f"found active workers: {len(workers)}")
    for worker in workers:
        send_shutdown_command(redis, worker.name)


if __name__ == "__main__":
    app.run(main)
