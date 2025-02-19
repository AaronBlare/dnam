import numpy as np
from src.models.tabnet.model import TabNetModel
import torch
import lightgbm as lgb
import hydra
from omegaconf import DictConfig
from pytorch_lightning import (
    LightningDataModule,
    seed_everything,
)
from experiment.logging import log_hyperparameters
from pytorch_lightning.loggers import LightningLoggerBase
from src.utils import utils
import wandb
import statsmodels.formula.api as smf
import xgboost as xgb
from experiment.regression.shap import explain_shap
import plotly.graph_objects as go
from scripts.python.routines.plot.save import save_figure
from scripts.python.routines.plot.layout import add_layout
from experiment.routines import eval_regression
from typing import List
from catboost import CatBoost
from scripts.python.routines.plot.scatter import add_scatter_trace


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
    feature_names = datamodule.get_feature_names()
    outcome_name = datamodule.get_outcome_name()
    df = datamodule.get_df()
    X_test = df.loc[:, feature_names].values
    y_test = df.loc[:, outcome_name].values

    if config.model_type == "lightgbm":
        model = lgb.Booster(model_file=config.ckpt_path)
        y_test_pred = model.predict(X_test, num_iteration=model.best_iteration).astype('float32')
        def shap_kernel(X):
            y = model.predict(X, num_iteration=model.best_iteration)
            return y
    elif config.model_type == "catboost":
        model = CatBoost()
        model.load_model(config.ckpt_path)
        y_test_pred = model.predict(X_test).astype('float32')
        def shap_kernel(X):
            y = model.predict(X)
            return y
    elif config.model_type == "xgboost":
        model = xgb.Booster()
        model.load_model(config.ckpt_path)
        dmat_test = xgb.DMatrix(X_test, y_test, feature_names=feature_names).astype('float32')
        y_test_pred = model.predict(dmat_test)
        def shap_kernel(X):
            X = xgb.DMatrix(X, feature_names=feature_names)
            y = model.predict(X)
            return y
    elif config.model_type == "tabnet":
        model = TabNetModel.load_from_checkpoint(checkpoint_path=f"{config.ckpt_path}")
        model.eval()
        model.freeze()
        X_test_pt = torch.from_numpy(X_test)
        y_test_pred = model(X_test_pt).cpu().detach().numpy()
        def shap_kernel(X):
            X = torch.from_numpy(X)
            tmp = model(X)
            return tmp.cpu().detach().numpy()
    else:
        raise ValueError(f"Unsupported sa_model")

    eval_regression(config, y_test, y_test_pred, loggers, 'inference', is_log=True, is_save=True)
    df.loc[:, "Estimation"] = y_test_pred
    predictions = df.loc[:, [outcome_name, "Estimation"]]
    predictions.to_excel(f"predictions.xlsx", index=True)

    formula = f"Estimation ~ {outcome_name}"
    model_linear = smf.ols(formula=formula, data=df).fit()
    fig = go.Figure()
    add_scatter_trace(fig, df.loc[:, outcome_name].values, df.loc[:, "Estimation"].values, f"Inference")
    add_scatter_trace(fig, df.loc[:, outcome_name].values, model_linear.fittedvalues.values, "", "lines")
    add_layout(fig, outcome_name, f"Estimation", f"")
    fig.update_layout({'colorway': ['blue']})
    fig.update_layout(legend_font_size=20)
    fig.update_layout(margin=go.layout.Margin(l=90, r=20, b=80, t=65, pad=0))
    save_figure(fig, f"scatter")

    if config.is_shap == True:
        shap_data = {
            'model': model,
            'shap_kernel': shap_kernel,
            'df': df,
            'feature_names': feature_names,
            'outcome_name': outcome_name,
            'ids_all': np.arange(df.shape[0]),
            'ids_trn': None,
            'ids_val': None,
            'ids_tst': None
        }
        explain_shap(config, shap_data)

    for logger in loggers:
        logger.save()
    if 'wandb' in config.logger:
        wandb.finish()

