import hydra
import numpy as np
from omegaconf import DictConfig
from pytorch_lightning import (
    LightningDataModule,
    seed_everything,
)
from experiment.logging import log_hyperparameters
from pytorch_lightning.loggers import LightningLoggerBase
import pandas as pd
from src.utils import utils
import xgboost as xgb
import plotly.graph_objects as go
from scripts.python.routines.plot.save import save_figure
from scripts.python.routines.plot.bar import add_bar_trace
from scripts.python.routines.plot.layout import add_layout
from experiment.routines import eval_classification
from experiment.routines import eval_loss
from typing import List
from catboost import CatBoost
from src.datamodules.cross_validation import RepeatedStratifiedKFoldCVSplitter
from experiment.binary.shap import perform_shap_explanation
import lightgbm as lgb
import wandb
from tqdm import tqdm
import shap


log = utils.get_logger(__name__)

def process(config: DictConfig):

    # Set seed for random number generators in pytorch, numpy and python.random
    if "seed" in config:
        seed_everything(config.seed, workers=True)

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

    # Init lightning datamodule
    log.info(f"Instantiating datamodule <{config.datamodule._target_}>")
    datamodule: LightningDataModule = hydra.utils.instantiate(config.datamodule)
    datamodule.setup()
    datamodule.perform_split()
    feature_names = datamodule.get_feature_names()
    class_names = datamodule.get_class_names()
    outcome_name = datamodule.get_outcome_name()
    df = datamodule.get_df()
    ids_tst = datamodule.ids_tst
    if ids_tst is not None:
        is_test = True
    else:
        is_test = False

    cv_datamodule = RepeatedStratifiedKFoldCVSplitter(
        data_module=datamodule,
        n_splits=config.cv_n_splits,
        n_repeats=config.cv_n_repeats,
        groups=config.cv_groups,
        random_state=config.seed,
        shuffle=config.is_shuffle
    )

    best = {}
    if config.direction == "min":
        best["optimized_metric"] = np.Inf
    elif config.direction == "max":
        best["optimized_metric"] = 0.0
    cv_progress = {'fold': [], 'optimized_metric': []}

    for fold_idx, (dl_trn, ids_trn, dl_val, ids_val) in tqdm(enumerate(cv_datamodule.split())):
        datamodule.ids_trn = ids_trn
        datamodule.ids_val = ids_val
        X_trn = df.loc[df.index[ids_trn], feature_names].values
        y_trn = df.loc[df.index[ids_trn], outcome_name].values
        df.loc[df.index[ids_trn], f"fold_{fold_idx:04d}"] = "Train"
        X_val = df.loc[df.index[ids_val], feature_names].values
        y_val = df.loc[df.index[ids_val], outcome_name].values
        df.loc[df.index[ids_val], f"fold_{fold_idx:04d}"] = "Val"
        if is_test:
            X_tst = df.loc[df.index[ids_tst], feature_names].values
            y_tst = df.loc[df.index[ids_tst], outcome_name].values
            df.loc[df.index[ids_tst], f"fold_{fold_idx:04d}"] = "Test"

        if config.model_type == "xgboost":
            model_params = {
                'booster': config.xgboost.booster,
                'eta': config.xgboost.learning_rate,
                'max_depth': config.xgboost.max_depth,
                'gamma': config.xgboost.gamma,
                'sampling_method': config.xgboost.sampling_method,
                'subsample': config.xgboost.subsample,
                'objective': config.xgboost.objective,
                'verbosity': config.xgboost.verbosity,
                'eval_metric': config.xgboost.eval_metric,
            }

            dmat_trn = xgb.DMatrix(X_trn, y_trn, feature_names=feature_names)
            dmat_val = xgb.DMatrix(X_val, y_val, feature_names=feature_names)
            if is_test:
                dmat_tst = xgb.DMatrix(X_tst, y_tst, feature_names=feature_names)

            evals_result = {}
            model = xgb.train(
                params=model_params,
                dtrain=dmat_trn,
                evals=[(dmat_trn, "train"), (dmat_val, "val")],
                num_boost_round=config.max_epochs,
                early_stopping_rounds=config.patience,
                evals_result=evals_result
            )

            y_trn_pred_prob = model.predict(dmat_trn)
            y_val_pred_prob = model.predict(dmat_val)
            y_trn_pred = np.array([1 if pred > 0.5 else 0 for pred in y_trn_pred_prob])
            y_val_pred = np.array([1 if pred > 0.5 else 0 for pred in y_val_pred_prob])
            y_trn_pred_raw = model.predict(dmat_trn, output_margin=True)
            y_val_pred_raw = model.predict(dmat_val, output_margin=True)
            if is_test:
                y_tst_pred_prob = model.predict(dmat_tst)
                y_tst_pred = np.array([1 if pred > 0.5 else 0 for pred in y_tst_pred_prob])
                y_tst_pred_raw = model.predict(dmat_tst, output_margin=True)

            loss_info = {
                'epoch': list(range(len(evals_result['train'][config.xgboost.eval_metric]))),
                'train/loss': evals_result['train'][config.xgboost.eval_metric],
                'val/loss': evals_result['val'][config.xgboost.eval_metric]
            }

            def shap_kernel(X):
                X = xgb.DMatrix(X, feature_names=feature_names)
                y = model.predict(X)
                return y

            fi = model.get_score(importance_type='weight')
            feature_importances = pd.DataFrame.from_dict({'feature': list(fi.keys()), 'importance': list(fi.values())})

        elif config.model_type == "catboost":
            model_params = {
                'loss_function': config.catboost.loss_function,
                'learning_rate': config.catboost.learning_rate,
                'depth': config.catboost.depth,
                'min_data_in_leaf': config.catboost.min_data_in_leaf,
                'max_leaves': config.catboost.max_leaves,
                'task_type': config.catboost.task_type,
                'verbose': config.catboost.verbose,
                'iterations': config.catboost.max_epochs,
                'early_stopping_rounds': config.catboost.patience
            }

            model = CatBoost(params=model_params)
            model.fit(X_trn, y_trn, eval_set=(X_val, y_val))
            model.set_feature_names(feature_names)

            y_trn_pred_prob = model.predict(X_trn, prediction_type="Probability")
            y_val_pred_prob = model.predict(X_val, prediction_type="Probability")
            y_trn_pred = np.argmax(y_trn_pred_prob, 1)
            y_val_pred = np.argmax(y_val_pred_prob, 1)
            y_trn_pred_raw = model.predict(X_trn, prediction_type="RawFormulaVal")
            y_val_pred_raw = model.predict(X_val, prediction_type="RawFormulaVal")
            if is_test:
                y_tst_pred_prob = model.predict(X_tst, prediction_type="Probability")
                y_tst_pred = np.argmax(y_tst_pred_prob, 1)
                y_tst_pred_raw = model.predict(X_tst, prediction_type="RawFormulaVal")

            metrics_trn = pd.read_csv(f"catboost_info/learn_error.tsv", delimiter="\t")
            metrics_val = pd.read_csv(f"catboost_info/test_error.tsv", delimiter="\t")
            loss_info = {
                'epoch': metrics_trn.iloc[:, 0],
                'train/loss': metrics_trn.iloc[:, 1],
                'val/loss': metrics_val.iloc[:, 1]
            }

            def shap_kernel(X):
                y = model.predict(X)
                return y

            feature_importances = pd.DataFrame.from_dict({'feature': model.feature_names_, 'importance': list(model.feature_importances_)})

        elif config.model_type == "lightgbm":
            model_params = {
                'objective': config.lightgbm.objective,
                'boosting': config.lightgbm.boosting,
                'learning_rate': config.lightgbm.learning_rate,
                'num_leaves': config.lightgbm.num_leaves,
                'device': config.lightgbm.device,
                'max_depth': config.lightgbm.max_depth,
                'min_data_in_leaf': config.lightgbm.min_data_in_leaf,
                'feature_fraction': config.lightgbm.feature_fraction,
                'bagging_fraction': config.lightgbm.bagging_fraction,
                'bagging_freq': config.lightgbm.bagging_freq,
                'verbose': config.lightgbm.verbose,
                'metric': config.lightgbm.metric
            }

            ds_trn = lgb.Dataset(X_trn, label=y_trn, feature_name=feature_names)
            ds_val = lgb.Dataset(X_val, label=y_val, reference=ds_trn, feature_name=feature_names)
            evals_result = {}
            model = lgb.train(
                params=model_params,
                train_set=ds_trn,
                num_boost_round=config.max_epochs,
                valid_sets=[ds_val, ds_trn],
                valid_names=['val', 'train'],
                evals_result=evals_result,
                early_stopping_rounds=config.patience,
                verbose_eval=False
            )

            y_trn_pred_prob = model.predict(X_trn, num_iteration=model.best_iteration)
            y_val_pred_prob = model.predict(X_val, num_iteration=model.best_iteration)
            y_trn_pred = np.array([1 if pred > 0.5 else 0 for pred in y_trn_pred_prob])
            y_val_pred = np.array([1 if pred > 0.5 else 0 for pred in y_val_pred_prob])
            y_trn_pred_raw = model.predict(X_trn, num_iteration=model.best_iteration, raw_score=True)
            y_val_pred_raw = model.predict(X_val, num_iteration=model.best_iteration, raw_score=True)
            if is_test:
                y_tst_pred_prob = model.predict(X_tst, num_iteration=model.best_iteration)
                y_tst_pred = np.array([1 if pred > 0.5 else 0 for pred in y_tst_pred_prob])
                y_tst_pred_raw = model.predict(X_tst, num_iteration=model.best_iteration, raw_score=True)

            loss_info = {
                'epoch': list(range(len(evals_result['train'][config.lightgbm.metric]))),
                'train/loss': evals_result['train'][config.lightgbm.metric],
                'val/loss': evals_result['val'][config.lightgbm.metric]
            }

            def shap_kernel(X):
                y = model.predict(X, num_iteration=model.best_iteration)
                return y

            feature_importances = pd.DataFrame.from_dict({'feature': model.feature_name(), 'importance': list(model.feature_importance())})

        else:
            raise ValueError(f"Model {config.model_type} is not supported")

        eval_classification(config, class_names, y_trn, y_trn_pred, y_trn_pred_prob, loggers, 'train', is_log=False, is_save=False)
        metrics_val = eval_classification(config, class_names, y_val, y_val_pred, y_val_pred_prob, loggers, 'val', is_log=False, is_save=False)
        if is_test:
            eval_classification(config, class_names, y_tst, y_tst_pred, y_tst_pred_prob, loggers, 'test', is_log=False, is_save=False)

        if config.direction == "min":
            if metrics_val.at[config.optimized_metric, 'val'] < best["optimized_metric"]:
                is_renew = True
            else:
                is_renew = False
        elif config.direction == "max":
            if metrics_val.at[config.optimized_metric, 'val'] > best["optimized_metric"]:
                is_renew = True
            else:
                is_renew = False

        if is_renew:
            best["optimized_metric"] = metrics_val.at[config.optimized_metric, 'val']
            best["model"] = model
            best['loss_info'] = loss_info
            best['shap_kernel'] = shap_kernel
            best['feature_importances'] = feature_importances
            best['fold'] = fold_idx
            best['ids_trn'] = ids_trn
            best['ids_val'] = ids_val
            df.loc[df.index[ids_trn], "pred"] = y_trn_pred
            df.loc[df.index[ids_val], "pred"] = y_val_pred
            df.loc[df.index[ids_trn], "pred_raw"] = y_trn_pred_raw
            df.loc[df.index[ids_val], "pred_raw"] = y_val_pred_raw
            if len(y_trn_pred_prob.shape) > 1 and y_trn_pred_prob.shape[1] == 2:
                for cl_id, cl in enumerate(class_names):
                    df.loc[df.index[ids_trn], f"pred_prob_{cl_id}"] = y_trn_pred_prob[:, cl_id]
                    df.loc[df.index[ids_val], f"pred_prob_{cl_id}"] = y_val_pred_prob[:, cl_id]
            else:
                df.loc[df.index[ids_trn], f"pred_prob_0"] = y_trn_pred_prob
                df.loc[df.index[ids_trn], f"pred_prob_1"] = 1 - y_trn_pred_prob
                df.loc[df.index[ids_val], f"pred_prob_0"] = y_val_pred_prob
                df.loc[df.index[ids_val], f"pred_prob_1"] = 1 - y_val_pred_prob
            if is_test:
                df.loc[df.index[ids_tst], "pred"] = y_tst_pred
                df.loc[df.index[ids_tst], "pred_raw"] = y_tst_pred_raw
                if len(y_trn_pred_prob.shape) > 1 and y_trn_pred_prob.shape[1] == 2:
                    for cl_id, cl in enumerate(class_names):
                        df.loc[df.index[ids_tst], f"pred_prob_{cl_id}"] = y_tst_pred_prob[:, cl_id]
                else:
                    df.loc[df.index[ids_tst], f"pred_prob_0"] = y_tst_pred_prob
                    df.loc[df.index[ids_tst], f"pred_prob_1"] = 1 - y_tst_pred_prob

        cv_progress['fold'].append(fold_idx)
        cv_progress['optimized_metric'].append(metrics_val.at[config.optimized_metric, 'val'])

    cv_progress_df = pd.DataFrame(cv_progress)
    cv_progress_df.set_index('fold', inplace=True)
    cv_progress_df.to_excel(f"cv_progress.xlsx", index=True)
    cv_ids = df.loc[:, [f"fold_{fold_idx:04d}" for fold_idx in cv_progress['fold']]]
    cv_ids.to_excel(f"cv_ids.xlsx", index=True)

    datamodule.ids_trn = best['ids_trn']
    datamodule.ids_val = best['ids_val']

    datamodule.plot_split(f"_best_{best['fold']:04d}")

    y_trn = df.loc[df.index[datamodule.ids_trn], outcome_name].values
    y_trn_pred = df.loc[df.index[datamodule.ids_trn], "pred"].values.astype('int32')
    y_trn_pred_prob = df.loc[df.index[datamodule.ids_trn], [f"pred_prob_{cl_id}" for cl_id, cl in enumerate(class_names)]].values
    y_val = df.loc[df.index[datamodule.ids_val], outcome_name].values
    y_val_pred = df.loc[df.index[datamodule.ids_val], "pred"].values.astype('int32')
    y_val_pred_prob = df.loc[df.index[datamodule.ids_val], [f"pred_prob_{cl_id}" for cl_id, cl in enumerate(class_names)]].values
    if is_test:
        y_tst = df.loc[df.index[datamodule.ids_tst], outcome_name].values
        y_tst_pred = df.loc[df.index[datamodule.ids_tst], "pred"].values.astype('int32')
        y_tst_pred_prob = df.loc[df.index[datamodule.ids_tst], [f"pred_prob_{cl_id}" for cl_id, cl in enumerate(class_names)]].values

    eval_classification(config, class_names, y_trn, y_trn_pred, y_trn_pred_prob, loggers, 'train', is_log=True, is_save=True, file_suffix=f"_best_{best['fold']:04d}")
    metrics_val = eval_classification(config, class_names, y_val, y_val_pred, y_val_pred_prob, loggers, 'val', is_log=True, is_save=True, file_suffix=f"_best_{best['fold']:04d}")
    if is_test:
        eval_classification(config, class_names, y_tst, y_tst_pred, y_tst_pred_prob, loggers, 'test', is_log=True, is_save=True, file_suffix=f"_best_{best['fold']:04d}")

    if config.model_type == "xgboost":
        best["model"].save_model(f"epoch_{best['model'].best_iteration}_best_{best['fold']:04d}.model")
    elif config.model_type == "catboost":
        best["model"].save_model(f"epoch_{best['model'].best_iteration_}_best_{best['fold']:04d}.model")
    elif config.model_type == "lightgbm":
        best["model"].save_model(f"epoch_{best['model'].best_iteration}_best_{best['fold']:04d}.txt", num_iteration=best['model'].best_iteration)
    else:
        raise ValueError(f"Model {config.model_type} is not supported")

    best['feature_importances'].sort_values(['importance'], ascending=[False], inplace=True)
    fig = go.Figure()
    ys = best['feature_importances']['feature'][0:config.num_top_features][::-1]
    xs = best['feature_importances']['importance'][0:config.num_top_features][::-1]
    add_bar_trace(fig, x=xs, y=ys, text=xs, orientation='h')
    add_layout(fig, f"Feature importance", f"", "")
    fig.update_yaxes(tickfont_size=10)
    fig.update_xaxes(showticklabels=True)
    fig.update_layout(margin=go.layout.Margin(l=110, r=20, b=75, t=25, pad=0))
    save_figure(fig, f"feature_importances")
    best['feature_importances'].set_index('feature', inplace=True)
    best['feature_importances'].to_excel("feature_importances.xlsx", index=True)

    if 'wandb' in config.logger:
        wandb.define_metric(f"epoch")
        wandb.define_metric(f"train/loss")
        wandb.define_metric(f"val/loss")
    eval_loss(best['loss_info'], loggers)

    for logger in loggers:
        logger.save()
    if 'wandb' in config.logger:
        wandb.finish()

    if config.is_shap == True:
        shap_data = {
            'model': best["model"],
            'shap_kernel': best['shap_kernel'],
            'df': df,
            'feature_names': feature_names,
            'class_names': class_names,
            'outcome_name': outcome_name,
            'ids_all': np.arange(df.shape[0]),
            'ids_trn': datamodule.ids_trn,
            'ids_val': datamodule.ids_val,
            'ids_tst': datamodule.ids_tst
        }
        perform_shap_explanation(config, shap_data)

    optimized_metric = config.get("optimized_metric")
    if optimized_metric:
        return metrics_val.at[optimized_metric, 'val']
