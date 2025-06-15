"""
Implements evaluation method `eval_from_checkpoint` for MNIST
example that assayer can use.

Test method is adapted from:
https://github.com/pytorch/examples/blob/abfa4f9cc4379de12f6c340538ef9a697332cccb/mnist/main.py
"""

import json
import os

import torch
import torch.nn.functional as F
from torchvision import datasets, transforms
from train import Net


def test(model, device, test_loader):
    model.eval()
    test_loss = 0
    correct = 0
    with torch.no_grad():
        for data, target in test_loader:
            data, target = data.to(device), target.to(device)
            output = model(data)
            test_loss += F.nll_loss(output, target, reduction="sum").item()  # sum up batch loss
            pred = output.argmax(dim=1, keepdim=True)  # get the index of the max log-probability
            correct += pred.eq(target.view_as(pred)).sum().item()

    test_loss /= len(test_loader.dataset)

    print(
        "\nTest set: Average loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)\n".format(
            test_loss, correct, len(test_loader.dataset), 100.0 * correct / len(test_loader.dataset)
        )
    )
    return {"test_loss": test_loss, "test_acc": 100.0 * correct / len(test_loader.dataset)}


# --- used by assayer --- #
def eval_from_checkpoint(checkpoint_path):
    # setup objects needed for evaluation
    if torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
    transform = transforms.Compose(
        [transforms.ToTensor(), transforms.Normalize((0.1307,), (0.3081,))]
    )
    dataset = datasets.MNIST("../data", train=False, transform=transform)
    test_kwargs = {"batch_size": 1000, "num_workers": 1, "pin_memory": True, "shuffle": True}
    test_loader = torch.utils.data.DataLoader(dataset, **test_kwargs)
    model = Net().to(device)
    model.load_state_dict(torch.load(checkpoint_path, weights_only=True))
    model.eval()

    # launch evaluation!
    print(f"Evaluating checkpoint from path: {checkpoint_path}")
    metrics = test(model, device, test_loader)

    # dump evaluation results
    metrics["checkpoint_path"] = checkpoint_path
    os.makedirs("./evals/", exist_ok=True)
    checkpoint_name = os.path.basename(checkpoint_path).split(".")[0]
    save_path = f"./evals/{checkpoint_name}.json"
    with open(save_path, "w") as f:
        json.dump(metrics, f, indent=4)
        print(f"Saved eval results to: {save_path}")
    return metrics


if __name__ == "__main__":
    # test evaluation method used by assayer
    eval_from_checkpoint("checkpoints/model_epoch1.pt")
