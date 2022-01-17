import pandas as pd
from scripts.python.routines.manifest import get_manifest
import numpy as np
import os
import pickle
from sklearn.metrics import mean_squared_error, mean_absolute_error
from scripts.python.pheno.datasets.filter import filter_pheno, get_passed_fields
from scipy.stats import spearmanr
import matplotlib.pyplot as plt
from scripts.python.pheno.datasets.features import get_column_name, get_status_dict, get_sex_dict
from scripts.python.routines.plot.scatter import add_scatter_trace
from matplotlib import colors
from scipy.stats import mannwhitneyu
import plotly.graph_objects as go
from scipy import stats
from scripts.python.routines.plot.save import save_figure
from scripts.python.routines.plot.violin import add_violin_trace
from scripts.python.routines.plot.box import add_box_trace
from scripts.python.routines.plot.layout import add_layout
import pathlib
import string
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from functools import reduce
import plotly
from sklearn.decomposition import PCA
import statsmodels.formula.api as smf
from scripts.python.routines.manifest import get_manifest
from scripts.python.routines.plot.save import save_figure
from scripts.python.routines.plot.histogram import add_histogram_trace
from scripts.python.routines.plot.layout import add_layout
from scripts.python.routines.plot.p_value import add_p_value_annotation
from scripts.python.EWAS.routines.correction import correct_pvalues
from statsmodels.stats.multitest import multipletests
import plotly.express as px
import matplotlib


dataset = "GSEUNN"
path = f"E:/YandexDisk/Work/pydnameth/datasets"
datasets_info = pd.read_excel(f"{path}/datasets.xlsx", index_col='dataset')
platform = datasets_info.loc[dataset, 'platform']
manifest = get_manifest(platform)
status_col = get_column_name(dataset, 'Status').replace(' ','_')
age_col = get_column_name(dataset, 'Age').replace(' ','_')
sex_col = get_column_name(dataset, 'Sex').replace(' ','_')
status_dict = get_status_dict(dataset)
status_passed_fields = status_dict['Control'] + status_dict['Case']
sex_dict = get_sex_dict(dataset)
continuous_vars = {}
categorical_vars = {status_col: [x.column for x in status_passed_fields], sex_col: list(sex_dict.values())}
pheno = pd.read_pickle(f"{path}/{platform}/{dataset}/pheno_xtd.pkl")
pheno = filter_pheno(dataset, pheno, continuous_vars, categorical_vars)
ctrl = pheno.loc[pheno['Group'] == 'Control']
esrd = pheno.loc[pheno['Group'] == 'ESRD']

ctrl_color = 'lime'
ctrl_test_color = 'cyan'
esrd_color = 'fuchsia'
dist_num_bins = 25

path_save = f"{path}/{platform}/{dataset}/special/012_GeroScience_revision"
pathlib.Path(f"{path_save}/SupplementaryFigure2").mkdir(parents=True, exist_ok=True)
pathlib.Path(f"{path_save}/Figure2").mkdir(parents=True, exist_ok=True)
pathlib.Path(f"{path_save}/Figure3").mkdir(parents=True, exist_ok=True)
pathlib.Path(f"{path_save}/Figure4").mkdir(parents=True, exist_ok=True)
pathlib.Path(f"{path_save}/Figure5").mkdir(parents=True, exist_ok=True)
pathlib.Path(f"{path_save}/Figure6").mkdir(parents=True, exist_ok=True)
pathlib.Path(f"{path_save}/Figure7").mkdir(parents=True, exist_ok=True)
pathlib.Path(f"{path_save}/SupplementaryTable9").mkdir(parents=True, exist_ok=True)

# Supplementary Figure 2 ===============================================================================================
result_dict = {'feature': ['CD4T', 'CD8naive', 'CD8pCD28nCD45RAn', 'Gran', 'Mono', 'NK', 'PlasmaBlast']}
result_dict['pval_mv'] = np.zeros(len(result_dict['feature']))
for f_id, f in enumerate(result_dict['feature']):
    values_ctrl = ctrl.loc[:, f].values
    values_esrd = esrd.loc[:, f].values
    stat, pval = mannwhitneyu(values_ctrl, values_esrd, alternative='two-sided')
    result_dict['pval_mv'][f_id] = pval

result_dict = correct_pvalues(result_dict, ['pval_mv'])
result_df = pd.DataFrame(result_dict)
result_df.set_index('feature', inplace=True)
result_df.sort_values(['pval_mv'], ascending=[True], inplace=True)
result_df.to_excel(f"{path_save}/SupplementaryFigure2/result.xlsx", index=True)

for f_id, f in enumerate(result_dict['feature']):
    values_ctrl = ctrl.loc[:, f].values
    values_esrd = esrd.loc[:, f].values
    fig = go.Figure()
    fig.add_trace(
        go.Violin(
            y=values_ctrl,
            name=f"Control",
            box_visible=True,
            meanline_visible=True,
            showlegend=True,
            line_color='black',
            fillcolor=ctrl_color,
            marker = dict(color=ctrl_color, line=dict(color='black',width=0.3), opacity=0.8),
            points='all',
            bandwidth = np.ptp(values_ctrl) / dist_num_bins,
            opacity=0.8
        )
    )
    fig.add_trace(
        go.Violin(
            y=values_esrd,
            name=f"ESRD",
            box_visible=True,
            meanline_visible=True,
            showlegend=True,
            line_color='black',
            fillcolor=esrd_color,
            marker=dict(color=esrd_color, line=dict(color='black',width=0.3), opacity=0.8),
            points='all',
            bandwidth=np.ptp(values_esrd) / dist_num_bins,
            opacity=0.8
        )
    )
    add_layout(fig, "", f"{f}", f"p-value: {result_df.at[f, 'pval_mv_fdr_bh']:0.2e}")
    fig.update_layout({'colorway': ['lime', 'fuchsia']})
    fig.update_layout(title_xref='paper')
    fig.update_layout(legend_font_size=20)
    fig.update_layout(
        margin=go.layout.Margin(
            l=110,
            r=20,
            b=50,
            t=90,
            pad=0
        )
    )
    fig.update_layout(legend_y=1.01)
    fig.add_annotation(dict(font=dict(color='black', size=45),
                            x=-0.18,
                            y=1.25,
                            showarrow=False,
                            text=f"({string.ascii_lowercase[f_id]})",
                            textangle=0,
                            yanchor='top',
                            xanchor='left',
                            xref="paper",
                            yref="paper"))
    save_figure(fig, f"{path_save}/SupplementaryFigure2/{string.ascii_lowercase[f_id]}_{f}")

# Figure 2 =============================================================================================================
result_dict = {
    'feature': ['DNAmAgeHannumAA', 'DNAmAgeAA', 'IEAA', 'EEAA', 'DNAmPhenoAgeAA', 'DNAmGrimAgeAA'],
    'name': ['DNAmAgeHannum acceleration', 'DNAmAge acceleration', 'IEAA', 'EEAA', 'DNAmPhenoAge acceleration', 'DNAmGrimAge acceleration']
}
result_dict['pval_mv'] = np.zeros(len(result_dict['feature']))
for f_id, f in enumerate(result_dict['feature']):
    values_ctrl = ctrl.loc[:, f].values
    values_esrd = esrd.loc[:, f].values
    stat, pval = mannwhitneyu(values_ctrl, values_esrd, alternative='two-sided')
    result_dict['pval_mv'][f_id] = pval

result_dict = correct_pvalues(result_dict, ['pval_mv'])
result_df = pd.DataFrame(result_dict)
result_df.set_index('feature', inplace=True)
result_df.to_excel(f"{path_save}/Figure2/result.xlsx", index=True)

for f_id, f in enumerate(result_dict['feature']):
    values_ctrl = ctrl.loc[:, f].values
    values_esrd = esrd.loc[:, f].values
    fig = go.Figure()
    fig.add_trace(
        go.Violin(
            y=values_ctrl,
            name=f"Control",
            box_visible=True,
            meanline_visible=True,
            showlegend=True,
            line_color='black',
            fillcolor=ctrl_color,
            marker = dict(color=ctrl_color, line=dict(color='black',width=0.3), opacity=0.8),
            points='all',
            bandwidth = np.ptp(values_ctrl) / dist_num_bins,
            opacity=0.8
        )
    )
    fig.add_trace(
        go.Violin(
            y=values_esrd,
            name=f"ESRD",
            box_visible=True,
            meanline_visible=True,
            showlegend=True,
            line_color='black',
            fillcolor=esrd_color,
            marker=dict(color=esrd_color, line=dict(color='black',width=0.3), opacity=0.8),
            points='all',
            bandwidth=np.ptp(values_esrd) / dist_num_bins,
            opacity=0.8
        )
    )
    add_layout(fig, "", f"{result_dict['name'][f_id]}", f"p-value: {result_df.at[f, 'pval_mv_fdr_bh']:0.2e}")
    fig.update_layout({'colorway': ['lime', 'fuchsia']})
    fig.update_layout(title_xref='paper')
    fig.update_layout(legend_font_size=20)
    fig.update_layout(
        margin=go.layout.Margin(
            l=110,
            r=20,
            b=50,
            t=90,
            pad=0
        )
    )
    fig.update_layout(legend_y=1.01)
    fig.add_annotation(dict(font=dict(color='black', size=45),
                            x=-0.18,
                            y=1.25,
                            showarrow=False,
                            text=f"({string.ascii_lowercase[f_id]})",
                            textangle=0,
                            yanchor='top',
                            xanchor='left',
                            xref="paper",
                            yref="paper"))
    save_figure(fig, f"{path_save}/Figure2/{string.ascii_lowercase[f_id]}_{f}")

# Figure 3 =============================================================================================================
result_dict = {
    'feature': ['PhenoAgeAA',
                'White_blood_cell_count_(10^9/L)',
                'Lymphocyte_percent_(%)',
                'Creatinine_(umol/L)',
                'Mean_cell_volume_(fL)',
                'Albumin_(g/L)',
                'Alkaline_phosphatase_(U/L)',
                'Red_cell_distribution_width_(%)',
                'Glucose._serum_(mmol/L)_',
                'Log_C-reactive_protein_(mg/L)',
                ],
    'name': ['Phenotypic Age Acceleration',
             'White blood cell count (10^9/L)',
             'Lymphocyte percent (%)',
             'Creatinine (umol/L)',
             'Mean cell volume (fL)',
             'Albumin (g/L)',
             'Alkaline phosphatase (U/L)',
             'Red cell distribution width (%)',
             'Glucose. serum (mmol/L)',
             'Log C-reactive protein (mg/L)',
             ]
}
result_dict['pval_mv'] = np.zeros(len(result_dict['feature']))
for f_id, f in enumerate(result_dict['feature']):
    values_ctrl = ctrl.loc[:, f].values
    values_esrd = esrd.loc[:, f].values
    stat, pval = mannwhitneyu(values_ctrl, values_esrd, alternative='two-sided')
    result_dict['pval_mv'][f_id] = pval

result_dict = correct_pvalues(result_dict, ['pval_mv'])
result_df = pd.DataFrame(result_dict)
result_df.set_index('feature', inplace=True)
result_df.to_excel(f"{path_save}/Figure3/result.xlsx", index=True)

for f_id, f in enumerate(result_dict['feature']):
    values_ctrl = ctrl.loc[:, f].values
    values_esrd = esrd.loc[:, f].values
    fig = go.Figure()
    fig.add_trace(
        go.Violin(
            y=values_ctrl,
            name=f"Control",
            box_visible=True,
            meanline_visible=True,
            showlegend=True,
            line_color='black',
            fillcolor=ctrl_color,
            marker = dict(color=ctrl_color, line=dict(color='black',width=0.3), opacity=0.8),
            points='all',
            bandwidth = np.ptp(values_ctrl) / dist_num_bins,
            opacity=0.8
        )
    )
    fig.add_trace(
        go.Violin(
            y=values_esrd,
            name=f"ESRD",
            box_visible=True,
            meanline_visible=True,
            showlegend=True,
            line_color='black',
            fillcolor=esrd_color,
            marker=dict(color=esrd_color, line=dict(color='black',width=0.3), opacity=0.8),
            points='all',
            bandwidth=np.ptp(values_esrd) / dist_num_bins,
            opacity=0.8
        )
    )
    if f == 'PhenoAgeAA':
        add_layout(fig, "", f"{result_dict['name'][f_id]}", f"p-value: {result_df.at[f, 'pval_mv']:0.2e}")
    else:
        add_layout(fig, "", f"{result_dict['name'][f_id]}", f"p-value: {result_df.at[f, 'pval_mv_fdr_bh']:0.2e}")
    fig.update_layout({'colorway': ['lime', 'fuchsia']})
    fig.update_layout(title_xref='paper')
    fig.update_layout(legend_font_size=20)
    fig.update_layout(
        margin=go.layout.Margin(
            l=110,
            r=20,
            b=50,
            t=90,
            pad=0
        )
    )
    fig.update_layout(legend_y=1.01)
    fig.add_annotation(dict(font=dict(color='black', size=45),
                            x=-0.18,
                            y=1.25,
                            showarrow=False,
                            text=f"({string.ascii_lowercase[f_id]})",
                            textangle=0,
                            yanchor='top',
                            xanchor='left',
                            xref="paper",
                            yref="paper"))
    save_figure(fig, f"{path_save}/Figure3/{string.ascii_lowercase[f_id]}")

# Figure 4 =============================================================================================================
ctrl_test = pd.read_excel(f"{path}/{platform}/{dataset}/special/011_immuno_part3_and_part4_check_clocks/part3_part4_filtered_with_age_sex_16.xlsx", index_col='ID')

rmse = np.sqrt(mean_squared_error(ctrl_test.loc[:, 'Age'].values, ctrl_test.loc[:, 'ImmunoAge'].values))
mae = mean_absolute_error(ctrl_test.loc[:, 'Age'].values, ctrl_test.loc[:, 'ImmunoAge'].values)
print(f"RMSE in test controls: {rmse}")
print(f"MAE in test controls: {mae}")

values_ctrl = ctrl.loc[:, 'ImmunoAgeAA'].values
values_ctrl_test = ctrl_test.loc[:, 'ImmunoAgeAcc'].values
values_esrd = esrd.loc[:, 'ImmunoAgeAA'].values

stat_01, pval_01 = mannwhitneyu(values_ctrl, values_ctrl_test, alternative='two-sided')
stat_02, pval_02 = mannwhitneyu(values_ctrl, values_esrd, alternative='two-sided')
stat_12, pval_12 = mannwhitneyu(values_ctrl_test, values_esrd, alternative='two-sided')

fig = go.Figure()
fig.add_trace(
    go.Violin(
        y=values_ctrl,
        name=f"Control",
        box_visible=True,
        meanline_visible=True,
        showlegend=True,
        line_color='black',
        fillcolor=ctrl_color,
        marker=dict(color=ctrl_color, line=dict(color='black', width=0.3), opacity=0.8),
        points='all',
        bandwidth=np.ptp(values_ctrl) / dist_num_bins,
        opacity=0.8
    )
)
fig.add_trace(
    go.Violin(
        y=values_ctrl_test,
        name=f"Control (test)",
        box_visible=True,
        meanline_visible=True,
        showlegend=True,
        line_color='black',
        fillcolor=ctrl_test_color,
        marker=dict(color=ctrl_test_color, line=dict(color='black', width=0.3), opacity=0.8),
        points='all',
        bandwidth=np.ptp(values_ctrl_test) / dist_num_bins,
        opacity=0.8
    )
)
fig.add_trace(
    go.Violin(
        y=values_esrd,
        name=f"ESRD",
        box_visible=True,
        meanline_visible=True,
        showlegend=True,
        line_color='black',
        fillcolor=esrd_color,
        marker=dict(color=esrd_color, line=dict(color='black', width=0.3), opacity=0.8),
        points='all',
        bandwidth=np.ptp(values_esrd) / 50,
        opacity=0.8
    )
)

add_layout(fig, "", "ipAGE acceleration", f"")
fig.update_layout({'colorway': ['lime', 'cyan', 'fuchsia']})
fig = add_p_value_annotation(fig, {(0,1): pval_01, (1, 2) : pval_12, (0,2): pval_02})
fig.update_yaxes(autorange=False)
fig.update_layout(yaxis_range=[-50, 200])
fig.update_layout(title_xref='paper')
fig.update_layout(legend_font_size=20)
fig.update_layout(
    margin=go.layout.Margin(
        l=110,
        r=20,
        b=50,
        t=90,
        pad=0
    )
)
fig.update_layout(
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.25,
        xanchor="center",
        x=0.5
    )
)
fig.add_annotation(dict(font=dict(color='black', size=45),
                        x=-0.18,
                        y=1.4,
                        showarrow=False,
                        text=f"(b)",
                        textangle=0,
                        yanchor='top',
                        xanchor='left',
                        xref="paper",
                        yref="paper"))
save_figure(fig, f"{path_save}/Figure4/b")

formula = f"ImmunoAge ~ Age"
model_linear = smf.ols(formula=formula, data=ctrl).fit()
fig = go.Figure()
add_scatter_trace(fig, ctrl.loc[:, 'Age'].values, ctrl.loc[:, 'ImmunoAge'].values, f"Control")
add_scatter_trace(fig, ctrl.loc[:, 'Age'].values, model_linear.fittedvalues.values, "", "lines")
add_scatter_trace(fig, ctrl_test.loc[:, 'Age'].values, ctrl_test.loc[:, 'ImmunoAge'].values, f"Control (test)")
add_scatter_trace(fig, esrd.loc[:, 'Age'].values, esrd.loc[:, 'ImmunoAge'].values, f"ESRD")
add_layout(fig, f"Age", 'ipAGE', f"")
fig.update_layout({'colorway': ['lime', 'lime', 'cyan', 'fuchsia']})
fig.update_layout(legend_font_size=20)
fig.update_layout(
    margin=go.layout.Margin(
        l=80,
        r=20,
        b=80,
        t=65,
        pad=0
    )
)
fig.update_yaxes(autorange=False)
fig.update_xaxes(autorange=False)
fig.update_layout(yaxis_range=[10, 110])
fig.update_layout(xaxis_range=[10, 100])
fig.add_annotation(dict(font=dict(color='black', size=45),
                        x=-0.13,
                        y=1.20,
                        showarrow=False,
                        text=f"(a)",
                        textangle=0,
                        yanchor='top',
                        xanchor='left',
                        xref="paper",
                        yref="paper"))
save_figure(fig, f"{path_save}/Figure4/a")

# Figure 5 a,b =========================================================================================================
result_dict = {
    'feature': ['Age', 'DNAmAgeHannum', 'DNAmAge', 'DNAmPhenoAge', 'DNAmGrimAge', 'PhenoAge', 'ImmunoAge'],
    'name': ['Age', 'DNAmAgeHannum', 'DNAmAge', 'DNAmPhenoAge', 'DNAmGrimAge', 'PhenotypicAge', 'ipAGE']
}

corr_df_ctrl = pd.DataFrame(data=np.zeros(shape=(len(result_dict['feature']), len(result_dict['feature']))), index=result_dict['name'], columns=result_dict['name'])
pval_df_ctrl = pd.DataFrame(data=np.zeros(shape=(len(result_dict['feature']), len(result_dict['feature']))), index=result_dict['name'], columns=result_dict['name'])
corr_df_esrd = pd.DataFrame(data=np.zeros(shape=(len(result_dict['feature']), len(result_dict['feature']))), index=result_dict['name'], columns=result_dict['name'])
pval_df_esrd = pd.DataFrame(data=np.zeros(shape=(len(result_dict['feature']), len(result_dict['feature']))), index=result_dict['name'], columns=result_dict['name'])

for f_id_1, f_1 in enumerate(result_dict['feature']):
    for f_id_2, f_2 in enumerate(result_dict['feature']):
        values_1_ctrl = ctrl.loc[:, f_1].values
        values_2_ctrl = ctrl.loc[:, f_2].values
        values_1_esrd = esrd.loc[:, f_1].values
        values_2_esrd = esrd.loc[:, f_2].values

        corr_ctrl, pval_ctrl = stats.pearsonr(values_1_ctrl, values_2_ctrl)
        corr_df_ctrl.loc[result_dict['name'][f_id_1], result_dict['name'][f_id_2]] = corr_ctrl
        pval_df_ctrl.loc[result_dict['name'][f_id_1], result_dict['name'][f_id_2]] = pval_ctrl
        corr_esrd, pval_esrd = stats.pearsonr(values_1_esrd, values_2_esrd)
        corr_df_esrd.loc[result_dict['name'][f_id_1], result_dict['name'][f_id_2]] = corr_esrd
        pval_df_esrd.loc[result_dict['name'][f_id_1], result_dict['name'][f_id_2]] = pval_esrd

selection = np.tri(pval_df_ctrl.shape[0], pval_df_ctrl.shape[1], -1, dtype=np.bool)

pval_df_ctrl_fdr = pval_df_ctrl.where(selection).stack().reset_index()
pval_df_ctrl_fdr.columns = ['row', 'col', 'pval']
_, pvals_corr, _, _ = multipletests(pval_df_ctrl_fdr.loc[:, 'pval'].values, 0.05, method='fdr_bh')
pval_df_ctrl_fdr['pval_fdr_bh'] = pvals_corr

pval_df_esrd_fdr = pval_df_esrd.where(selection).stack().reset_index()
pval_df_esrd_fdr.columns = ['row', 'col', 'pval']
_, pvals_corr, _, _ = multipletests(pval_df_esrd_fdr.loc[:, 'pval'].values, 0.05, method='fdr_bh')
pval_df_esrd_fdr['pval_fdr_bh'] = pvals_corr

for line_id in range(pval_df_ctrl_fdr.shape[0]):
    pval_df_ctrl.loc[pval_df_ctrl_fdr.at[line_id, 'row'], pval_df_ctrl_fdr.at[line_id, 'col']] = pval_df_ctrl_fdr.at[line_id, 'pval_fdr_bh']
    pval_df_ctrl.loc[pval_df_ctrl_fdr.at[line_id, 'col'], pval_df_ctrl_fdr.at[line_id, 'row']] = pval_df_ctrl_fdr.at[line_id, 'pval_fdr_bh']
    pval_df_esrd.loc[pval_df_esrd_fdr.at[line_id, 'row'], pval_df_esrd_fdr.at[line_id, 'col']] = pval_df_esrd_fdr.at[line_id, 'pval_fdr_bh']
    pval_df_esrd.loc[pval_df_esrd_fdr.at[line_id, 'col'], pval_df_esrd_fdr.at[line_id, 'row']] = pval_df_esrd_fdr.at[line_id, 'pval_fdr_bh']

for f_id_1, f_1 in enumerate(result_dict['feature']):
    pval_df_ctrl.loc[result_dict['name'][f_id_1], :] = -np.log10(pval_df_ctrl.loc[result_dict['name'][f_id_1], :])
    pval_df_esrd.loc[result_dict['name'][f_id_1], :] = -np.log10(pval_df_esrd.loc[result_dict['name'][f_id_1], :])

corr_df_ctrl = corr_df_ctrl.iloc[::-1]
mtx_to_plot = corr_df_ctrl.to_numpy()
cmap = plt.get_cmap("bwr").copy()
fig, ax = plt.subplots()
im = ax.imshow(mtx_to_plot, cmap=cmap, vmin=-1, vmax=1)
cbar = ax.figure.colorbar(im, ax=ax, location='top', fraction=0.046, pad=0.04)
cbar.set_label(r"$\mathrm{Correlation}$", horizontalalignment='center', fontsize=15)
ax.set_aspect("equal")
ax.set_xticks(np.arange(corr_df_ctrl.shape[0]))
ax.set_yticks(np.arange(corr_df_ctrl.shape[0]))
ax.set_xticklabels(corr_df_ctrl.columns.values)
ax.set_yticklabels(corr_df_ctrl.index.values)
plt.setp(ax.get_xticklabels(), rotation=90)
data = im.get_array()
threshold = im.norm(data.max()) / 2.
ax.tick_params(axis='both', which='major', labelsize=12)
ax.tick_params(axis='both', which='minor', labelsize=12)
textcolors = ("black", "white")
for i in range(corr_df_ctrl.shape[0]):
    for j in range(corr_df_ctrl.shape[0]):
        color = 'black'
        text = ax.text(j, i, f"{mtx_to_plot[i, j]:0.2f}", ha="center", va="center", color=color, fontsize=7)
fig.tight_layout()
plt.savefig(f"{path_save}/Figure5/a_1.png", bbox_inches='tight', dpi=400)
plt.savefig(f"{path_save}/Figure5/a_1.pdf", bbox_inches='tight', dpi=400)

pval_df_ctrl = pval_df_ctrl.iloc[::-1]
mtx_to_plot = pval_df_ctrl.to_numpy()
cmap = plt.get_cmap("Reds").copy()
cmap.set_under('lightseagreen')
fig, ax = plt.subplots()
im = ax.imshow(mtx_to_plot, cmap=cmap, vmin=-np.log10(0.05))
cbar = ax.figure.colorbar(im, ax=ax, location='top', fraction=0.046, pad=0.04)
cbar.set_label(r"$-\log_{10}(\mathrm{p-value})$", horizontalalignment='center', fontsize=15)
ax.set_aspect("equal")
ax.set_xticks(np.arange(pval_df_ctrl.shape[0]))
ax.set_yticks(np.arange(pval_df_ctrl.shape[0]))
ax.set_xticklabels(pval_df_ctrl.columns.values)
ax.set_yticklabels(pval_df_ctrl.index.values)
plt.setp(ax.get_xticklabels(), rotation=90)
data = im.get_array()
threshold = im.norm(data.max()) / 2.
ax.tick_params(axis='both', which='major', labelsize=12)
ax.tick_params(axis='both', which='minor', labelsize=12)
textcolors = ("black", "white")
for i in range(pval_df_ctrl.shape[0]):
    for j in range(pval_df_ctrl.shape[0]):
        color = textcolors[int(im.norm(data[i, j]) > threshold)]
        if np.isinf(mtx_to_plot[i, j]):
            text = ax.text(j, i, f"", ha="center", va="center", color=color, fontsize=7)
        else:
            text = ax.text(j, i, f"{mtx_to_plot[i, j]:0.2f}", ha="center", va="center", color=color, fontsize=7)
fig.tight_layout()
plt.savefig(f"{path_save}/Figure5/a_2.png", bbox_inches='tight', dpi=400)
plt.savefig(f"{path_save}/Figure5/a_2.pdf", bbox_inches='tight', dpi=400)

corr_df_esrd = corr_df_esrd.iloc[::-1]
mtx_to_plot = corr_df_esrd.to_numpy()
cmap = plt.get_cmap("bwr").copy()
fig, ax = plt.subplots()
im = ax.imshow(mtx_to_plot, cmap=cmap, vmin=-1, vmax=1)
cbar = ax.figure.colorbar(im, ax=ax, location='top', fraction=0.046, pad=0.04)
cbar.set_label(r"$\mathrm{Correlation}$", horizontalalignment='center', fontsize=15)
ax.set_aspect("equal")
ax.set_xticks(np.arange(corr_df_esrd.shape[0]))
ax.set_yticks(np.arange(corr_df_esrd.shape[0]))
ax.set_xticklabels(corr_df_esrd.columns.values)
ax.set_yticklabels(corr_df_esrd.index.values)
plt.setp(ax.get_xticklabels(), rotation=90)
data = im.get_array()
threshold = im.norm(data.max()) / 2.
ax.tick_params(axis='both', which='major', labelsize=12)
ax.tick_params(axis='both', which='minor', labelsize=12)
textcolors = ("black", "white")
for i in range(corr_df_esrd.shape[0]):
    for j in range(corr_df_esrd.shape[0]):
        color = 'black'
        text = ax.text(j, i, f"{mtx_to_plot[i, j]:0.2f}", ha="center", va="center", color=color, fontsize=7)
fig.tight_layout()
plt.savefig(f"{path_save}/Figure5/b_1.png", bbox_inches='tight', dpi=400)
plt.savefig(f"{path_save}/Figure5/b_1.pdf", bbox_inches='tight', dpi=400)

pval_df_esrd = pval_df_esrd.iloc[::-1]
mtx_to_plot = pval_df_esrd.to_numpy()
cmap = plt.get_cmap("Reds").copy()
cmap.set_under('lightseagreen')
fig, ax = plt.subplots()
im = ax.imshow(mtx_to_plot, cmap=cmap, vmin=-np.log10(0.05))
cbar = ax.figure.colorbar(im, ax=ax, location='top', fraction=0.046, pad=0.04)
cbar.set_label(r"$-\log_{10}(\mathrm{p-value})$", horizontalalignment='center', fontsize=15)
ax.set_aspect("equal")
ax.set_xticks(np.arange(pval_df_esrd.shape[0]))
ax.set_yticks(np.arange(pval_df_esrd.shape[0]))
ax.set_xticklabels(pval_df_esrd.columns.values)
ax.set_yticklabels(pval_df_esrd.index.values)
plt.setp(ax.get_xticklabels(), rotation=90)
data = im.get_array()
threshold = im.norm(data.max()) / 2.
ax.tick_params(axis='both', which='major', labelsize=12)
ax.tick_params(axis='both', which='minor', labelsize=12)
textcolors = ("black", "white")
for i in range(pval_df_esrd.shape[0]):
    for j in range(pval_df_esrd.shape[0]):
        color = textcolors[int(im.norm(data[i, j]) > threshold)]
        if np.isinf(mtx_to_plot[i, j]):
            text = ax.text(j, i, f"", ha="center", va="center", color=color, fontsize=7)
        else:
            text = ax.text(j, i, f"{mtx_to_plot[i, j]:0.2f}", ha="center", va="center", color=color, fontsize=7)
fig.tight_layout()
plt.savefig(f"{path_save}/Figure5/b_2.png", bbox_inches='tight', dpi=400)
plt.savefig(f"{path_save}/Figure5/b_2.pdf", bbox_inches='tight', dpi=400)

# Figure 5 c,d =========================================================================================================
result_dict = {
    'feature': ['DNAmAgeHannumAA', 'DNAmAgeAA', 'IEAA', 'EEAA', 'DNAmPhenoAgeAA', 'DNAmGrimAgeAA', 'PhenoAgeAA', 'ImmunoAgeAA'],
    'name': ['DNAmAgeHannumAcc', 'DNAmAgeAcc', 'IEAA', 'EEAA', 'DNAmPhenoAgeAcc', 'DNAmGrimAgeAcc', 'PhenotypicAgeAcc', 'ipAGEAcc']
}

corr_df_ctrl = pd.DataFrame(data=np.zeros(shape=(len(result_dict['feature']), len(result_dict['feature']))), index=result_dict['name'], columns=result_dict['name'])
pval_df_ctrl = pd.DataFrame(data=np.zeros(shape=(len(result_dict['feature']), len(result_dict['feature']))), index=result_dict['name'], columns=result_dict['name'])
corr_df_esrd = pd.DataFrame(data=np.zeros(shape=(len(result_dict['feature']), len(result_dict['feature']))), index=result_dict['name'], columns=result_dict['name'])
pval_df_esrd = pd.DataFrame(data=np.zeros(shape=(len(result_dict['feature']), len(result_dict['feature']))), index=result_dict['name'], columns=result_dict['name'])

for f_id_1, f_1 in enumerate(result_dict['feature']):
    for f_id_2, f_2 in enumerate(result_dict['feature']):
        values_1_ctrl = ctrl.loc[:, f_1].values
        values_2_ctrl = ctrl.loc[:, f_2].values
        values_1_esrd = esrd.loc[:, f_1].values
        values_2_esrd = esrd.loc[:, f_2].values

        corr_ctrl, pval_ctrl = stats.pearsonr(values_1_ctrl, values_2_ctrl)
        corr_df_ctrl.loc[result_dict['name'][f_id_1], result_dict['name'][f_id_2]] = corr_ctrl
        pval_df_ctrl.loc[result_dict['name'][f_id_1], result_dict['name'][f_id_2]] = pval_ctrl
        corr_esrd, pval_esrd = stats.pearsonr(values_1_esrd, values_2_esrd)
        corr_df_esrd.loc[result_dict['name'][f_id_1], result_dict['name'][f_id_2]] = corr_esrd
        pval_df_esrd.loc[result_dict['name'][f_id_1], result_dict['name'][f_id_2]] = pval_esrd

selection = np.tri(pval_df_ctrl.shape[0], pval_df_ctrl.shape[1], -1, dtype=np.bool)

pval_df_ctrl_fdr = pval_df_ctrl.where(selection).stack().reset_index()
pval_df_ctrl_fdr.columns = ['row', 'col', 'pval']
_, pvals_corr, _, _ = multipletests(pval_df_ctrl_fdr.loc[:, 'pval'].values, 0.05, method='fdr_bh')
pval_df_ctrl_fdr['pval_fdr_bh'] = pvals_corr

pval_df_esrd_fdr = pval_df_esrd.where(selection).stack().reset_index()
pval_df_esrd_fdr.columns = ['row', 'col', 'pval']
_, pvals_corr, _, _ = multipletests(pval_df_esrd_fdr.loc[:, 'pval'].values, 0.05, method='fdr_bh')
pval_df_esrd_fdr['pval_fdr_bh'] = pvals_corr

for line_id in range(pval_df_ctrl_fdr.shape[0]):
    pval_df_ctrl.loc[pval_df_ctrl_fdr.at[line_id, 'row'], pval_df_ctrl_fdr.at[line_id, 'col']] = pval_df_ctrl_fdr.at[line_id, 'pval_fdr_bh']
    pval_df_ctrl.loc[pval_df_ctrl_fdr.at[line_id, 'col'], pval_df_ctrl_fdr.at[line_id, 'row']] = pval_df_ctrl_fdr.at[line_id, 'pval_fdr_bh']
    pval_df_esrd.loc[pval_df_esrd_fdr.at[line_id, 'row'], pval_df_esrd_fdr.at[line_id, 'col']] = pval_df_esrd_fdr.at[line_id, 'pval_fdr_bh']
    pval_df_esrd.loc[pval_df_esrd_fdr.at[line_id, 'col'], pval_df_esrd_fdr.at[line_id, 'row']] = pval_df_esrd_fdr.at[line_id, 'pval_fdr_bh']

for f_id_1, f_1 in enumerate(result_dict['feature']):
    pval_df_ctrl.loc[result_dict['name'][f_id_1], :] = -np.log10(pval_df_ctrl.loc[result_dict['name'][f_id_1], :])
    pval_df_esrd.loc[result_dict['name'][f_id_1], :] = -np.log10(pval_df_esrd.loc[result_dict['name'][f_id_1], :])

corr_df_ctrl = corr_df_ctrl.iloc[::-1]
mtx_to_plot = corr_df_ctrl.to_numpy()
cmap = plt.get_cmap("bwr").copy()
fig, ax = plt.subplots()
im = ax.imshow(mtx_to_plot, cmap=cmap, vmin=-1, vmax=1)
cbar = ax.figure.colorbar(im, ax=ax, location='top', fraction=0.046, pad=0.04)
cbar.set_label(r"$\mathrm{Correlation}$", horizontalalignment='center', fontsize=15)
ax.set_aspect("equal")
ax.set_xticks(np.arange(corr_df_ctrl.shape[0]))
ax.set_yticks(np.arange(corr_df_ctrl.shape[0]))
ax.set_xticklabels(corr_df_ctrl.columns.values)
ax.set_yticklabels(corr_df_ctrl.index.values)
plt.setp(ax.get_xticklabels(), rotation=90)
data = im.get_array()
threshold = im.norm(data.max()) / 2.
ax.tick_params(axis='both', which='major', labelsize=12)
ax.tick_params(axis='both', which='minor', labelsize=12)
textcolors = ("black", "white")
for i in range(corr_df_ctrl.shape[0]):
    for j in range(corr_df_ctrl.shape[0]):
        color = 'black'
        text = ax.text(j, i, f"{mtx_to_plot[i, j]:0.2f}", ha="center", va="center", color=color, fontsize=6)
fig.tight_layout()
plt.savefig(f"{path_save}/Figure5/c_1.png", bbox_inches='tight', dpi=400)
plt.savefig(f"{path_save}/Figure5/c_1.pdf", bbox_inches='tight', dpi=400)

pval_df_ctrl = pval_df_ctrl.iloc[::-1]
mtx_to_plot = pval_df_ctrl.to_numpy()
cmap = plt.get_cmap("Reds").copy()
cmap.set_under('lightseagreen')
fig, ax = plt.subplots()
im = ax.imshow(mtx_to_plot, cmap=cmap, vmin=-np.log10(0.05))
cbar = ax.figure.colorbar(im, ax=ax, location='top', fraction=0.046, pad=0.04)
cbar.set_label(r"$-\log_{10}(\mathrm{p-value})$", horizontalalignment='center', fontsize=15)
ax.set_aspect("equal")
ax.set_xticks(np.arange(pval_df_ctrl.shape[0]))
ax.set_yticks(np.arange(pval_df_ctrl.shape[0]))
ax.set_xticklabels(pval_df_ctrl.columns.values)
ax.set_yticklabels(pval_df_ctrl.index.values)
plt.setp(ax.get_xticklabels(), rotation=90)
data = im.get_array()
threshold = im.norm(data.max()) / 2.
ax.tick_params(axis='both', which='major', labelsize=12)
ax.tick_params(axis='both', which='minor', labelsize=12)
textcolors = ("black", "white")
for i in range(pval_df_ctrl.shape[0]):
    for j in range(pval_df_ctrl.shape[0]):
        color = textcolors[int(im.norm(data[i, j]) > threshold)]
        if np.isinf(mtx_to_plot[i, j]):
            text = ax.text(j, i, f"", ha="center", va="center", color=color, fontsize=7)
        else:
            text = ax.text(j, i, f"{mtx_to_plot[i, j]:0.2f}", ha="center", va="center", color=color, fontsize=6)
fig.tight_layout()
plt.savefig(f"{path_save}/Figure5/c_2.png", bbox_inches='tight', dpi=400)
plt.savefig(f"{path_save}/Figure5/c_2.pdf", bbox_inches='tight', dpi=400)

corr_df_esrd = corr_df_esrd.iloc[::-1]
mtx_to_plot = corr_df_esrd.to_numpy()
cmap = plt.get_cmap("bwr").copy()
fig, ax = plt.subplots()
im = ax.imshow(mtx_to_plot, cmap=cmap, vmin=-1, vmax=1)
cbar = ax.figure.colorbar(im, ax=ax, location='top', fraction=0.046, pad=0.04)
cbar.set_label(r"$\mathrm{Correlation}$", horizontalalignment='center', fontsize=15)
ax.set_aspect("equal")
ax.set_xticks(np.arange(corr_df_esrd.shape[0]))
ax.set_yticks(np.arange(corr_df_esrd.shape[0]))
ax.set_xticklabels(corr_df_esrd.columns.values)
ax.set_yticklabels(corr_df_esrd.index.values)
plt.setp(ax.get_xticklabels(), rotation=90)
data = im.get_array()
threshold = im.norm(data.max()) / 2.
ax.tick_params(axis='both', which='major', labelsize=12)
ax.tick_params(axis='both', which='minor', labelsize=12)
textcolors = ("black", "white")
for i in range(corr_df_esrd.shape[0]):
    for j in range(corr_df_esrd.shape[0]):
        color = 'black'
        text = ax.text(j, i, f"{mtx_to_plot[i, j]:0.2f}", ha="center", va="center", color=color, fontsize=6)
fig.tight_layout()
plt.savefig(f"{path_save}/Figure5/d_1.png", bbox_inches='tight', dpi=400)
plt.savefig(f"{path_save}/Figure5/d_1.pdf", bbox_inches='tight', dpi=400)

pval_df_esrd = pval_df_esrd.iloc[::-1]
mtx_to_plot = pval_df_esrd.to_numpy()
cmap = plt.get_cmap("Reds").copy()
cmap.set_under('lightseagreen')
fig, ax = plt.subplots()
im = ax.imshow(mtx_to_plot, cmap=cmap, vmin=-np.log10(0.05))
cbar = ax.figure.colorbar(im, ax=ax, location='top', fraction=0.046, pad=0.04)
cbar.set_label(r"$-\log_{10}(\mathrm{p-value})$", horizontalalignment='center', fontsize=15)
ax.set_aspect("equal")
ax.set_xticks(np.arange(pval_df_esrd.shape[0]))
ax.set_yticks(np.arange(pval_df_esrd.shape[0]))
ax.set_xticklabels(pval_df_esrd.columns.values)
ax.set_yticklabels(pval_df_esrd.index.values)
plt.setp(ax.get_xticklabels(), rotation=90)
data = im.get_array()
threshold = im.norm(data.max()) / 2.
ax.tick_params(axis='both', which='major', labelsize=12)
ax.tick_params(axis='both', which='minor', labelsize=12)
textcolors = ("black", "white")
for i in range(pval_df_esrd.shape[0]):
    for j in range(pval_df_esrd.shape[0]):
        color = textcolors[int(im.norm(data[i, j]) > threshold)]
        if np.isinf(mtx_to_plot[i, j]):
            text = ax.text(j, i, f"", ha="center", va="center", color=color, fontsize=7)
        else:
            text = ax.text(j, i, f"{mtx_to_plot[i, j]:0.2f}", ha="center", va="center", color=color, fontsize=6)
fig.tight_layout()
plt.savefig(f"{path_save}/Figure5/d_2.png", bbox_inches='tight', dpi=400)
plt.savefig(f"{path_save}/Figure5/d_2.pdf", bbox_inches='tight', dpi=400)

# Figure 6 =============================================================================================================
# SupplementaryTable9 ==================================================================================================
with open(f'{path}/{platform}/{dataset}/features/immuno.txt') as f:
    immuno_features = f.read().splitlines()
result_dict = {'feature': immuno_features}
result_dict['pval_mv'] = np.zeros(len(result_dict['feature']))
for f_id, f in enumerate(result_dict['feature']):
    values_ctrl = ctrl.loc[:, f].values
    values_esrd = esrd.loc[:, f].values
    stat, pval = mannwhitneyu(values_ctrl, values_esrd, alternative='two-sided')
    result_dict['pval_mv'][f_id] = pval

result_dict = correct_pvalues(result_dict, ['pval_mv'])
result_df = pd.DataFrame(result_dict)
result_df.set_index('feature', inplace=True)
result_df.sort_values(['pval_mv'], ascending=[True], inplace=True)
result_df.rename(
    columns={'pval_mv': 'Mann–Whitney U test p-value', 'pval_mv_fdr_bh': 'Mann–Whitney U test p-value (FDR)'},
    inplace=True
)
result_df.drop('pval_mv_bonferroni', axis=1, inplace=True)
result_df.to_excel(f"{path_save}/SupplementaryTable9/Disease.xlsx", index=True)
top_features = ['CSF1', 'CXCL9']
top_features_ranges = {'CSF1': [-100, 2500], 'CXCL9': [-1000, 20000]}
top_features_bandwidth={'CSF1': {'Control': 50, 'ESRD': 90}, 'CXCL9': {'Control': 800, 'ESRD': 800}}

for f_id, f in enumerate(top_features):
    values_ctrl = ctrl.loc[:, f].values
    values_esrd = esrd.loc[:, f].values
    fig = go.Figure()
    fig.add_trace(
        go.Violin(
            y=values_ctrl,
            name=f"Control",
            box_visible=True,
            meanline_visible=True,
            showlegend=True,
            line_color='black',
            fillcolor=ctrl_color,
            marker = dict(color=ctrl_color, line=dict(color='black',width=0.3), opacity=0.8),
            points='all',
            bandwidth=top_features_bandwidth[f]['Control'],
            opacity=0.8
        )
    )
    fig.add_trace(
        go.Violin(
            y=values_esrd,
            name=f"ESRD",
            box_visible=True,
            meanline_visible=True,
            showlegend=True,
            line_color='black',
            fillcolor=esrd_color,
            marker=dict(color=esrd_color, line=dict(color='black',width=0.3), opacity=0.8),
            points='all',
            bandwidth=top_features_bandwidth[f]['ESRD'],
            opacity=0.8
        )
    )
    add_layout(fig, "", f"{f}", f"p-value: {result_df.at[f, 'Mann–Whitney U test p-value (FDR)']:0.2e}")
    fig.update_layout({'colorway': ['lime', 'fuchsia']})
    fig.update_layout(title_xref='paper')
    fig.update_layout(legend_font_size=20)
    fig.update_yaxes(autorange=False)
    fig.update_layout(yaxis_range=top_features_ranges[f])
    fig.update_layout(
        margin=go.layout.Margin(
            l=130,
            r=20,
            b=50,
            t=90,
            pad=0
        )
    )
    fig.update_layout(legend_y=1.01)
    fig.add_annotation(dict(font=dict(color='black', size=45),
                            x=-0.18,
                            y=1.25,
                            showarrow=False,
                            text=f"({string.ascii_lowercase[f_id+1]})",
                            textangle=0,
                            yanchor='top',
                            xanchor='left',
                            xref="paper",
                            yref="paper"))
    save_figure(fig, f"{path_save}/Figure6/{string.ascii_lowercase[f_id+1]}_{f}")

xs = -np.log10(result_df.loc[:, 'Mann–Whitney U test p-value (FDR)'].values)[::-1]
ys = result_df.index.values[::-1]


fig = go.Figure()
fig.add_trace(
    go.Bar(
        x=xs,
        y=list(range(len(xs))),
        orientation='h',
        marker=dict(color='red', opacity=0.9)
    )
)
fig.add_trace(
    go.Scatter(
        x=[-np.log10(0.05), -np.log10(0.05)],
        y=[-1, len(xs)],
        showlegend=False,
        mode='lines',
        line = dict(color='black', width=2, dash='dash')
    )
)
add_layout(fig, "$\\huge{-\log_{10}(\\text{p-value})}$", "", f"")
fig.update_layout({'colorway': ['red', 'black']})
fig.update_layout(legend_font_size=20)
fig.update_layout(showlegend=False)
fig.update_layout(
    yaxis = dict(
        tickmode = 'array',
        tickvals = list(range(len(xs))),
        ticktext = ys
    )
)
fig.update_yaxes(autorange=False)
fig.update_layout(yaxis_range=[-1, len(xs)])
fig.update_yaxes(tickfont_size=24)
fig.update_xaxes(tickfont_size=30)
fig.update_layout(
    autosize=False,
    width=800,
    height=1400,
    margin=go.layout.Margin(
        l=175,
        r=20,
        b=100,
        t=40,
        pad=0
    )
)
fig.add_annotation(dict(font=dict(color='black', size=65),
                        x=-0.29,
                        y=1.04,
                        showarrow=False,
                        text=f"(a)",
                        textangle=0,
                        yanchor='top',
                        xanchor='left',
                        xref="paper",
                        yref="paper"))
save_figure(fig, f"{path_save}/Figure6/a")

# Figure 7a ============================================================================================================
features_2 = ['Age', 'DNAmAgeHannum', 'DNAmAge', 'DNAmPhenoAge', 'DNAmGrimAge', 'PhenoAge', 'ImmunoAge']
names_2 = ['Age', 'DNAmAgeHannum', 'DNAmAge', 'DNAmPhenoAge', 'DNAmGrimAge', 'PhenotypicAge', 'ipAGE']
with open(f'{path}/{platform}/{dataset}/features/immuno.txt') as f:
    features_1 = f.read().splitlines()
    names_1 = features_1.copy()

corr_df_ctrl = pd.DataFrame(data=np.zeros(shape=(len(names_1), len(names_2))), index=names_1, columns=names_2)
pval_df_ctrl = pd.DataFrame(data=np.zeros(shape=(len(names_1), len(names_2))), index=names_1, columns=names_2)

for f_id_2, f_2 in enumerate(features_2):
    for f_id_1, f_1 in enumerate(features_1):
        values_1_ctrl = ctrl.loc[:, f_1].values
        values_2_ctrl = ctrl.loc[:, f_2].values
        corr_ctrl, pval_ctrl = stats.pearsonr(values_1_ctrl, values_2_ctrl)
        corr_df_ctrl.loc[names_1[f_id_1], names_2[f_id_2]] = corr_ctrl
        pval_df_ctrl.loc[names_1[f_id_1], names_2[f_id_2]] = pval_ctrl

for f_id_2, f_2 in enumerate(features_2):
    _, pvals_corr, _, _ = multipletests(pval_df_ctrl.loc[:, names_2[f_id_2]].values, 0.05, method='fdr_bh')
    pval_df_ctrl.loc[:, names_2[f_id_2]] = -np.log10(pvals_corr)

corr_df_ctrl = corr_df_ctrl.iloc[::-1]
mtx_to_plot = corr_df_ctrl.to_numpy()
cmap = plt.get_cmap("bwr").copy()
fig, ax = plt.subplots()
im = ax.imshow(mtx_to_plot, cmap=cmap, vmin=-1, vmax=1)
cbar = ax.figure.colorbar(im, ax=ax, location='top', fraction=0.05, pad=0.03, shrink=0.155)
cbar.set_label(r"$\mathrm{Correlation}$", horizontalalignment='center', fontsize=8)
cbar.ax.tick_params(labelsize=8)
ax.set_aspect(0.5)
ax.set_xticks(np.arange(corr_df_ctrl.shape[1]))
ax.set_yticks(np.arange(corr_df_ctrl.shape[0]))
ax.set_xticklabels(corr_df_ctrl.columns.values)
ax.set_yticklabels(corr_df_ctrl.index.values)
plt.setp(ax.get_xticklabels(), rotation=90)
data = im.get_array()
threshold = im.norm(data.max()) / 2.
ax.tick_params(axis='x', which='major', labelsize=6)
ax.tick_params(axis='x', which='minor', labelsize=6)
ax.tick_params(axis='y', which='major', labelsize=5)
ax.tick_params(axis='y', which='minor', labelsize=5)
textcolors = ("black", "white")
for i in range(corr_df_ctrl.shape[0]):
    for j in range(corr_df_ctrl.shape[1]):
        color = 'black'
        text = ax.text(j, i, f"{mtx_to_plot[i, j]:0.2f}", ha="center", va="center", color=color, fontsize=3)
fig.tight_layout()
plt.savefig(f"{path_save}/Figure7/a_1.png", bbox_inches='tight', dpi=400)
plt.savefig(f"{path_save}/Figure7/a_1.pdf", bbox_inches='tight', dpi=400)

pval_df_ctrl = pval_df_ctrl.iloc[::-1]
mtx_to_plot = pval_df_ctrl.to_numpy()
cmap = plt.get_cmap("Reds").copy()
cmap.set_under('lightseagreen')
fig, ax = plt.subplots()
im = ax.imshow(mtx_to_plot, cmap=cmap, vmin=-np.log10(0.05))
cbar = ax.figure.colorbar(im, ax=ax, location='top', fraction=0.05, pad=0.03, shrink=0.155)
cbar.set_label(r"$-\log_{10}(\mathrm{p-value})$", horizontalalignment='center', fontsize=8)
cbar.ax.tick_params(labelsize=8)
ax.set_aspect(0.5)
ax.set_xticks(np.arange(pval_df_ctrl.shape[1]))
ax.set_yticks(np.arange(pval_df_ctrl.shape[0]))
ax.set_xticklabels(pval_df_ctrl.columns.values)
ax.set_yticklabels(pval_df_ctrl.index.values)
plt.setp(ax.get_xticklabels(), rotation=90)
data = im.get_array()
threshold = im.norm(data.max()) / 2.
ax.tick_params(axis='x', which='major', labelsize=6)
ax.tick_params(axis='x', which='minor', labelsize=6)
ax.tick_params(axis='y', which='major', labelsize=5)
ax.tick_params(axis='y', which='minor', labelsize=5)
textcolors = ("black", "white")
for i in range(pval_df_ctrl.shape[0]):
    for j in range(pval_df_ctrl.shape[1]):
        color = textcolors[int(im.norm(data[i, j]) > threshold)]
        if np.isinf(mtx_to_plot[i, j]):
            text = ax.text(j, i, f"", ha="center", va="center", color=color, fontsize=3)
        else:
            text = ax.text(j, i, f"{mtx_to_plot[i, j]:0.2f}", ha="center", va="center", color=color, fontsize=3)
fig.tight_layout()
plt.savefig(f"{path_save}/Figure7/a_2.png", bbox_inches='tight', dpi=400)
plt.savefig(f"{path_save}/Figure7/a_2.pdf", bbox_inches='tight', dpi=400)


# Figure 7b ============================================================================================================
features_2 = ['Age', 'DNAmAgeHannum', 'DNAmAge', 'DNAmPhenoAge', 'DNAmGrimAge', 'PhenoAge', 'ImmunoAge', 'Dialysis_(months)']
names_2 = ['Age', 'DNAmAgeHannum', 'DNAmAge', 'DNAmPhenoAge', 'DNAmGrimAge', 'PhenotypicAge', 'ipAGE', 'Dialysis(months)']
with open(f'{path}/{platform}/{dataset}/features/immuno.txt') as f:
    features_1 = f.read().splitlines()
    names_1 = features_1.copy()
features_1 += ['Dialysis_(months)']
names_1 += ['Dialysis(months)']

corr_df_esrd = pd.DataFrame(data=np.zeros(shape=(len(names_1), len(names_2))), index=names_1, columns=names_2)
pval_df_esrd = pd.DataFrame(data=np.zeros(shape=(len(names_1), len(names_2))), index=names_1, columns=names_2)

for f_id_2, f_2 in enumerate(features_2):
    for f_id_1, f_1 in enumerate(features_1):
        values_1_esrd = esrd.loc[:, f_1].values
        values_2_esrd = esrd.loc[:, f_2].values
        corr_esrd, pval_esrd = stats.pearsonr(values_1_esrd, values_2_esrd)
        corr_df_esrd.loc[names_1[f_id_1], names_2[f_id_2]] = corr_esrd
        pval_df_esrd.loc[names_1[f_id_1], names_2[f_id_2]] = pval_esrd

for f_id_2, f_2 in enumerate(features_2):
    _, pvals_corr, _, _ = multipletests(pval_df_esrd.loc[:, names_2[f_id_2]].values, 0.05, method='fdr_bh')
    pval_df_esrd.loc[:, names_2[f_id_2]] = -np.log10(pvals_corr)

corr_df_esrd = corr_df_esrd.iloc[::-1]
mtx_to_plot = corr_df_esrd.to_numpy()
cmap = plt.get_cmap("bwr").copy()
fig, ax = plt.subplots()
im = ax.imshow(mtx_to_plot, cmap=cmap, vmin=-1, vmax=1)
cbar = ax.figure.colorbar(im, ax=ax, location='top', fraction=0.05, pad=0.03, shrink=0.175)
cbar.set_label(r"$\mathrm{Correlation}$", horizontalalignment='center', fontsize=8)
cbar.ax.tick_params(labelsize=8)
ax.set_aspect(0.5)
ax.set_xticks(np.arange(corr_df_esrd.shape[1]))
ax.set_yticks(np.arange(corr_df_esrd.shape[0]))
ax.set_xticklabels(corr_df_esrd.columns.values)
ax.set_yticklabels(corr_df_esrd.index.values)
plt.setp(ax.get_xticklabels(), rotation=90)
data = im.get_array()
threshold = im.norm(data.max()) / 2.
ax.tick_params(axis='x', which='major', labelsize=6)
ax.tick_params(axis='x', which='minor', labelsize=6)
ax.tick_params(axis='y', which='major', labelsize=5)
ax.tick_params(axis='y', which='minor', labelsize=5)
textcolors = ("black", "white")
for i in range(corr_df_esrd.shape[0]):
    for j in range(corr_df_esrd.shape[1]):
        color = 'black'
        text = ax.text(j, i, f"{mtx_to_plot[i, j]:0.2f}", ha="center", va="center", color=color, fontsize=3)
fig.tight_layout()
plt.savefig(f"{path_save}/Figure7/b_1.png", bbox_inches='tight', dpi=400)
plt.savefig(f"{path_save}/Figure7/b_1.pdf", bbox_inches='tight', dpi=400)

pval_df_esrd = pval_df_esrd.iloc[::-1]
mtx_to_plot = pval_df_esrd.to_numpy()
cmap = plt.get_cmap("Reds").copy()
cmap.set_under('lightseagreen')
fig, ax = plt.subplots()
im = ax.imshow(mtx_to_plot, cmap=cmap, vmin=-np.log10(0.05))
cbar = ax.figure.colorbar(im, ax=ax, location='top', fraction=0.05, pad=0.03, shrink=0.175)
cbar.set_label(r"$-\log_{10}(\mathrm{p-value})$", horizontalalignment='center', fontsize=8)
cbar.ax.tick_params(labelsize=8)
ax.set_aspect(0.5)
ax.set_xticks(np.arange(pval_df_esrd.shape[1]))
ax.set_yticks(np.arange(pval_df_esrd.shape[0]))
ax.set_xticklabels(pval_df_esrd.columns.values)
ax.set_yticklabels(pval_df_esrd.index.values)
plt.setp(ax.get_xticklabels(), rotation=90)
data = im.get_array()
threshold = im.norm(data.max()) / 2.
ax.tick_params(axis='x', which='major', labelsize=6)
ax.tick_params(axis='x', which='minor', labelsize=6)
ax.tick_params(axis='y', which='major', labelsize=5)
ax.tick_params(axis='y', which='minor', labelsize=5)
textcolors = ("black", "white")
for i in range(pval_df_esrd.shape[0]):
    for j in range(pval_df_esrd.shape[1]):
        color = textcolors[int(im.norm(data[i, j]) > threshold)]
        if np.isinf(mtx_to_plot[i, j]):
            text = ax.text(j, i, f"", ha="center", va="center", color=color, fontsize=3)
        else:
            text = ax.text(j, i, f"{mtx_to_plot[i, j]:0.2f}", ha="center", va="center", color=color, fontsize=3)
fig.tight_layout()
plt.savefig(f"{path_save}/Figure7/b_2.png", bbox_inches='tight', dpi=400)
plt.savefig(f"{path_save}/Figure7/b_2.pdf", bbox_inches='tight', dpi=400)
