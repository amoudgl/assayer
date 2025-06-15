# assayer

`assayer` is a simple Python RQ-based tool that monitors ML model checkpoints in a given directory and launches evaluations offline as soon as new checkpoints are created during training. This tool can also be used to monitor multiple experiment directories simultaneously and launch evaluations for all of them in parallel.


## Installation

Install Redis server on [MacOS](https://redis.io/docs/latest/operate/oss_and_stack/install/archive/install-redis/install-redis-on-mac-os/) or [Linux](https://redis.io/docs/latest/operate/oss_and_stack/install/archive/install-redis/install-redis-on-linux/). 

For linux installation without root access like on a compute cluster, follow the instructions below (adapted from [here](https://techmonger.github.io/40/redis-without-root/)):

1. Download latest Redis tarball from [here](https://github.com/redis/redis-hashes). Example command below:
```
wget http://download.redis.io/releases/redis-8.0.0.tar.gz
```

2. Untar and make install:
```
tar -xf redis-8.0.0.tar.gz
cd redis-8.0.0
make
```

3. Test by starting redis server
```
cd redis-8.0.0/src
./redis-server
```

Install python dependencies:
```
pip install rq absl-py
```

Install assayer:
```
pip install git+https://github.com/amoudgl/assayer.git
```

## Usage

First, start Redis server in a terminal:
```
redis-server
```

Implement evaluation method (e.g. `my_eval` here) that **only** takes checkpoint path as argument:
```python
# in path/to/some_file.py:

def my_eval(checkpoint_path):
    # evaluation logic goes here...
```

See concrete example [here](#example-mnist).


> [!NOTE]
> You can implement rest of the evaluation logic anywhere as long as the evaluation method (e.g. `my_eval` above) that is passed to assayer can perform the evaluation as expected.


In a separate terminal, run the watch command below and provide path to implemented evaluation method mentioned above in `--evaluator` argument. Absolute or relative path to evaluation method can be provided either via file path:
```
python -m assayer.watch --directory path/to/watch_dir --evaluator path/to/some_file.py:my_eval
```
OR via installed module:
```
python -m assayer.watch --directory path/to/watch_dir --evaluator my_module.metrics.my_eval
```

Assayer watches the directory and evaluates new checkpoints created in it. Even if multiple checkpoints are created at the same time, eval jobs get submitted to Redis server which are fetched by different evaluation workers, leading to simultaneous evaluations of the checkpoints. 

> [!TIP]
> You can tweak `--evaluator` method to submit evaluation jobs to a compute cluster instead of doing the whole evaluation within the method itself. This will keep evaluation workers free and ready to quickly evaluate new checkpoints as soon as they get created during training.

The true power of this package is utilized when it is used to watch multiple directories simultaneously! All the specified directories (e.g. dir1, dir2, dir3 in commands below) will be monitored continuously and as soon as new checkpoints appear in directories, their respective evaluation jobs are launched in parallel:
```
python -m assayer.watch --directory dir1 --evaluator path/to/eval1.py:eval_fn1
python -m assayer.watch --directory dir2 --evaluator path/to/eval2.py:eval_fn2
python -m assayer.watch --directory dir3 --evaluator path/to/eval3.py:eval_fn3
```

Number of watch and eval workers can be tweaked with `--num_watch_workers` and `--num_eval_workers` arguments:
```
python -m assayer.watch --num_eval_workers 5 --num_watch_workers 1 --directory dir1 --evaluator path/to/eval1.py:eval_fn1
```

> [!TIP]
> If checkpoints are created once in a while like in standard training and evaluation doesn't take long, 1 eval and 1 wait worker should be sufficient per watch directory. However, if evaluations take longer than the interval between checkpoint creations, then eval workers can be scaled accordingly to avoid stalling evaluation of latest checkpoints. More details [here](#how-it-works-under-the-hood).


View all the configurable flags using the command below:
```
python -m assayer.watch --help
```

## Shutdown

To shutdown assayer, simply do:
```
python -m assayer.shutdown
```
which empties the queues and shutdowns workers.

You can watch a new directory if you'd like from this point or close Redis server to shutdown everything with keyboard interrupt (ctrl+c).

## How it works under the hood

assayer maintains two Redis queues: (1) `watch` (2) `evaluation`. Initially, a [watch job](assayer/jobs/watch_job.py) gets submitted to the `watch` queue when watch command is triggered by the user for a given directory. This watch job has info about existing checkpoints and simply checks if new files are created in the directory as per the regex filter passed by the user. If new checkpoints are found, a corresponding [eval job](assayer/jobs/eval_job.py) is submitted to the `evaluation` queue. Then, this watch job enqueues a new watch job containing updated list of checkpoints (recursion) and completes itself. Evaluation workers fetch jobs from evaluation queue leading to evaluation of new checkpoints. Watch workers fetch jobs from watch queue leading to continuous monitoring of checkpoints.

I considered using [watchdog](https://github.com/gorakhargosh/watchdog) package to monitor checkpoint directory but found [some](https://stackoverflow.com/questions/76491748/watchdog-is-not-monitoring-the-files-at-all) [good](https://stackoverflow.com/questions/65206223/python-watchdog-stops-capturing-events-after-a-few-mins) [excuses](https://github.com/gorakhargosh/watchdog/issues/700) to not use it. Moreover, I wanted to keep the implementation simple with minimum dependencies for longevity and low maintenance, hence stuck to pure RQ framework. However, I'd be very much open to improvements. If you think the implementation can be further optimized or sped up, create an issue to start the discussion (please be kind, thanks). Note that this is just a personal side project, so most likely won't be able to spend a lot of time on it.

## Example: MNIST

Navigate to `examples/mnist/` directory for instructions to try out assayer with MNIST training.

The example launches CNN training on MNIST task and checkpoints are saved to a directory. These checkpoints are fetched by assayer to do evaluation on MNIST test set. In this example, a simple evaluation method (passed to assayer watch command as `--evaluator`) is implemented that loads model checkpoint from a given path, computes average loss + accuracy on MNIST test set and saves metrics as a json file in `examples/mnist/evals/` directory.


## FAQs

<details>
<summary>How frequently is the checkpoint directory monitored?</summary>
<br>

By default, assayer monitors checkpoints every 5 seconds which can be configured by setting `--polling_interval` (in seconds) in assayer watch command.
<br>
</details>

<details>
<summary>Can I monitor all the evaluation and watch jobs in assayer?</summary>
<br>

Yes! Use the command below:
```
rq info
```

You can also monitor RQ jobs on a web-based dashboard by following the instructions [here](https://github.com/Parallels/rq-dashboard). More details regarding RQ jobs monitoring can be found [here](https://python-rq.org/docs/monitoring/). 
<br>
</details>

<details>
<summary>How does assayer handle checkpoint deletions?</summary>
<br>

assayer only launches evaluation for new checkpoints that are created during training, hence deletions won't mess up or launch any new evaluations. The detailed logic of assayer watch job is described below:

assayer watch job receives a list of checkpoints from its predecessor job (from 5s before by default, specified by `--polling_interval`). The watch job fetches a fresh list of checkpoints from directory specified and compares this list with its predecessor checkpoints list. Then, it launches evaluations for new checkpoints that are NOT there in predecessor checkpoints list. Checkout `assayer/jobs/watch_job.py` for code implementing this logic.
<br>
</details>

<details>
<summary>Are the evaluation results stored somewhere?</summary>
<br>

It is recommended to save evaluation results to disk  in `--evaluator` method since python RQ [saves](https://python-rq.org/docs/results/#job-results) upto 10 latest job results for sometime (500 seconds by default, can be configured by `result_ttl` argument in RQ [enqueue method](https://python-rq.org/docs/#enqueueing-jobs)). RQ enqueue method is used in `assayer/jobs/watch_job.py` to enqueue eval and watch jobs.
<br>
</details>

## License

[MIT](./LICENSE)