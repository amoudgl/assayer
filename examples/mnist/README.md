# MNIST example

On a single GPU node, launch training from `examples/mnist` directory:
```
python train.py
```
which will create checkpoints in `examples/mnist/checkpoints/` directory.

In a separate terminal, start redis server:
```
redis-server
```

Launch assayer watch from MNIST example directory `examples/mnist`:
```
python -m assayer.watch --directory ./checkpoints/ --evaluator eval.py:eval_from_checkpoint
```

In this MNIST example, assayer will use `eval_from_checkpoint` method implemented in `eval.py`.

> [!CAUTION]
> If Redis server is not launched, you'll get "Connection refused" error in assayer watch command.

As new checkpoints are created, you should be able to see evaluation running in watch command logs. Moreover, eval results will dumped to `examples/mnist/evals` directory as json files:
```
evals/
    model_epoch0.json
    model_epoch1.json
    ...
```

Shutdown assayer with:
```
python -m assayer.shutdown
```