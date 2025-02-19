import numpy as np
from src.models.dnam.model import TabNetModel
import os
from scripts.python.routines.plot.save import save_figure
from scripts.python.routines.plot.violin import add_violin_trace
from scripts.python.routines.plot.layout import add_layout
import plotly.graph_objects as go
from tqdm import tqdm
import pandas as pd
import dotenv
from pytorch_lightning import LightningDataModule
from torch.utils.data import DataLoader, ConcatDataset
from pytorch_lightning import seed_everything
import hydra
from src.utils import utils
from omegaconf import DictConfig
from pathlib import Path
from glob import glob
import plotly.express as px
from sklearn.feature_selection import VarianceThreshold

log = utils.get_logger(__name__)

dotenv.load_dotenv(override=True)

@hydra.main(config_path="../../configs/", config_name="main_xai.yaml")
def main(config: DictConfig):

    num_top_features = 100

    input_dim = 24829
    output_dim = 4
    check_sum = '121da597d6d3fe7b3b1b22a0ddc26e61'
    model = "tabnetpl_unnhpc"
    date_time = '2021-11-18_13-47-38'

    folder_path = f"E:/YandexDisk/Work/pydnameth/datasets/meta/{check_sum}/models/{model}/logs/multiruns/{date_time}"

    # Init Lightning datamodule
    log.info(f"Instantiating datamodule <{config.datamodule._target_}>")
    datamodule: LightningDataModule = hydra.utils.instantiate(config.datamodule)
    datamodule.setup()

    statuses = datamodule.statuses

    train_dataloader = datamodule.train_dataloader()
    val_dataloader = datamodule.val_dataloader()
    test_dataloader = datamodule.test_dataloader()
    dataset = ConcatDataset([train_dataloader.dataset, val_dataloader.dataset, test_dataloader.dataset])
    all_dataloader = DataLoader(
        dataset,
        batch_size=config.datamodule.batch_size,
        num_workers=config.datamodule.num_workers,
        pin_memory=config.datamodule.pin_memory,
        shuffle=True
    )
    background_dataloader = train_dataloader
    common_df = pd.merge(datamodule.pheno, datamodule.betas, left_index=True, right_index=True)

    runs = next(os.walk(folder_path))[1]
    runs.sort()

    feat_importances = pd.DataFrame(data=np.zeros(shape=(input_dim, len(runs)), dtype=float), columns=runs)
    for run_id, run in enumerate(runs):
        checkpoint_fn = glob(f"{folder_path}/{run}/checkpoints/*.ckpt")

        if "seed" in config:
            seed_everything(config.seed)

        model = TabNetModel.load_from_checkpoint(checkpoint_path=checkpoint_fn[0])
        model.produce_probabilities = True
        model.eval()
        model.freeze()

        if run_id == 0:
            feat_importances.loc[:, 'feature'] = datamodule.betas.columns.values

        fis = np.zeros((model.hparams.input_dim))
        for data, targets, indexes in tqdm(background_dataloader):
            M_explain, masks = model.forward_masks(data)
            fis += M_explain.sum(dim=0).cpu().detach().numpy()
        fis = fis / np.sum(fis)
        feat_importances.loc[:, run] = fis

    feat_importances.set_index('feature', inplace=True)
    feat_importances['average'] = feat_importances.mean(numeric_only=True, axis=1)
    vt = VarianceThreshold(0.0)
    vt.fit(datamodule.betas)
    vt_metrics = vt.variances_
    feat_importances.loc[:, 'variance'] = vt_metrics

    feat_importances.sort_values(['average'], ascending=[False], inplace=True)
    feat_importances.to_excel("./feat_importances.xlsx", index=True)

    for feat_id, feat in enumerate(feat_importances.index.values[0:num_top_features]):
        curr_var = np.var(common_df.loc[:, feat].values)
        fig = go.Figure()
        for status, code_status in statuses.items():
            add_violin_trace(fig, common_df.loc[common_df['Status_Origin'] == status, feat].values, status, True)
        add_layout(fig, f"variance = {curr_var:0.2e}", f"{feat}", "")
        fig.update_layout({'colorway': px.colors.qualitative.Set1})
        fig.update_xaxes(showticklabels=False)
        Path(f"features/violin").mkdir(parents=True, exist_ok=True)
        save_figure(fig, f"features/violin/{feat_id}_{feat}")

    thresholds = [0.001, 0.005, 0.01]
    for th in thresholds:
        curr_feat_imp = feat_importances.loc[feat_importances['variance'] > th, :]
        curr_feat_imp.sort_values(['average'], ascending=[False], inplace=True)
        for feat_id, feat in enumerate(curr_feat_imp.index.values[0:num_top_features]):
            curr_var = np.var(common_df.loc[:, feat].values)
            fig = go.Figure()
            for status, code_status in statuses.items():
                add_violin_trace(fig, common_df.loc[common_df['Status_Origin'] == status, feat].values, status, True)
            add_layout(fig, f"variance = {curr_var:0.2e}", f"{feat}", "")
            fig.update_layout({'colorway': px.colors.qualitative.Set1})
            fig.update_xaxes(showticklabels=False)
            Path(f"features/{th}/violin").mkdir(parents=True, exist_ok=True)
            save_figure(fig, f"features/{th}/violin/{feat_id}_{feat}")


if __name__ == "__main__":
    main()
