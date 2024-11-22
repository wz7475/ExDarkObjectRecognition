import torch
import torchvision
from torch import nn
from torch.utils.tensorboard import SummaryWriter
from torchmetrics.detection.mean_ap import MeanAveragePrecision
from tqdm import tqdm

from exdark.config import DEVICE
from exdark.datamodule import ExDarkDataModule
from exdark.models.cocowrapperfasterrcnn import ExDarkFasterRCNNWrapper
from exdark.models.cocowrapperrtdetr import ExDarkRTDetrWrapper


def test_model(model: nn.Module, device: torch.device, batch_size: int, writer: SummaryWriter):
    """
    function to evaluate model independently of its architecture and way of training
    """
    test_loader = ExDarkDataModule(batch_size=batch_size).test_dataloader()
    model.eval()
    prog_bar = tqdm(test_loader, total=len(test_loader))
    all_targets = []
    all_preds = []
    for i, data in enumerate(prog_bar):
        images, targets = data

        images = list(image.to(device) for image in images)
        targets = [{k: v.to(device) for k, v in t.items()} for t in targets]

        with torch.no_grad():
            outputs = model(images, targets)

        for i in range(len(images)):
            true_dict = dict()
            preds_dict = dict()
            true_dict['boxes'] = targets[i]['boxes'].detach().cpu()
            true_dict['labels'] = targets[i]['labels'].detach().cpu()

            preds_dict['boxes'] = outputs[i]['boxes'].detach().cpu()
            preds_dict['scores'] = outputs[i]['scores'].detach().cpu()
            preds_dict['labels'] = outputs[i]['labels'].detach().cpu()
            all_preds.append(preds_dict)
            all_targets.append(true_dict)

    metric = MeanAveragePrecision()
    metric.update(all_preds, all_targets)
    metric_summary = metric.compute()
    writer.add_scalars("mAP", dict((k, v.item()) for k, v in metric_summary.items() if k != "classes"))
    return metric_summary


if __name__ == '__main__':
    device = torch.device("cuda" if torch.cuda.is_available() else "mps")
    print(device)
    # core_model = torchvision.models.detection.fasterrcnn_resnet50_fpn_v2(
    #     weights=torchvision.models.detection.FasterRCNN_ResNet50_FPN_V2_Weights.DEFAULT)
    # model = ExDarkFasterRCNNWrapper(core_model)
    model = ExDarkRTDetrWrapper()
    print(model.__class__)
    model = model.to(device)

    with SummaryWriter("ExDarkASCOCOWrapper_evaluation") as writer:
        metric_summary = test_model(model, DEVICE, 8, writer)
    print(f"mAP_50: {metric_summary['map_50'] * 100:.3f}")
    print(f"mAP_50_95: {metric_summary['map'] * 100:.3f}")
    print(metric_summary)
