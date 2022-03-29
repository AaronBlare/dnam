import numpy as np
from src.models.dnam.tabnet import TabNetModel
import torch
import lightgbm as lgb
import pandas as pd
import hydra
from omegaconf import DictConfig
from pytorch_lightning import (
    LightningDataModule,
    seed_everything,
)
from experiment.logging import log_hyperparameters
from pytorch_lightning.loggers import LightningLoggerBase
from src.utils import utils
from experiment.routines import eval_classification_sa
from typing import List
import wandb
from catboost import CatBoost
import xgboost as xgb


log = utils.get_logger(__name__)

def inference(config: DictConfig):

    if "seed" in config:
        seed_everything(config.seed)

    if 'wandb' in config.logger:
        config.logger.wandb["project"] = config.project_name

    # Init lightning loggers
    loggers: List[LightningLoggerBase] = []
    if "logger" in config:
        for _, lg_conf in config.logger.items():
            if "_target_" in lg_conf:
                log.info(f"Instantiating logger <{lg_conf._target_}>")
                loggers.append(hydra.utils.instantiate(lg_conf))

    log.info("Logging hyperparameters!")
    log_hyperparameters(loggers, config)

    # Init Lightning datamodule for test
    log.info(f"Instantiating datamodule <{config.datamodule._target_}>")
    datamodule: LightningDataModule = hydra.utils.instantiate(config.datamodule)
    datamodule.setup()
    feature_names = datamodule.get_feature_names()
    class_names = datamodule.get_class_names()
    outcome_name = datamodule.get_outcome_name()
    df = datamodule.get_df()
    df['pred'] = 0
    X_test = df.loc[:, feature_names].values
    y_test = df.loc[:, outcome_name].values

    if config.model_type == "lightgbm":
        model = lgb.Booster(model_file=config.ckpt_path)
        y_test_pred_prob = model.predict(X_test)
    elif config.model_type == "catboost":
        model = CatBoost()
        model.load_model(config.ckpt_path)
        y_test_pred_prob = model.predict(X_test)
    elif config.model_type == "xgboost":
        model = xgb.Booster()
        model.load_model(config.ckpt_path)
        dmat_test = xgb.DMatrix(X_test, y_test, feature_names=feature_names)
        y_test_pred_prob = model.predict(dmat_test)
    elif config.model_type == "tabnet":
        model = TabNetModel.load_from_checkpoint(checkpoint_path=f"{config.ckpt_path}")
        model.produce_probabilities = True
        model.eval()
        model.freeze()
        X_test_pt = torch.from_numpy(X_test)
        y_test_pred_prob = model(X_test_pt).cpu().detach().numpy()
    else:
        raise ValueError(f"Unsupported sa_model")

    y_test_pred = np.argmax(y_test_pred_prob, 1)

    eval_classification_sa(config, class_names, y_test, y_test_pred, y_test_pred_prob, loggers, 'inference', is_log=True, is_save=True)
    df.loc[:, "pred"] = y_test_pred
    for cl_id, cl in enumerate(class_names):
        df.loc[:, f"pred_prob_{cl_id}"] = y_test_pred_prob[:, cl_id]

    predictions = df.loc[:, [outcome_name, "pred"] + [f"pred_prob_{cl_id}" for cl_id, cl in enumerate(class_names)]]
    predictions.to_excel(f"predictions.xlsx", index=True)

    for logger in loggers:
        logger.save()
    if 'wandb' in config.logger:
        wandb.finish()

