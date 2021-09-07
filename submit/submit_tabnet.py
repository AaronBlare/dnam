import os


data_path = "/home/yusipov_i/data/dnam/datasets/meta/BrainDiseases/variance(0.005)"

n_d = [8, 16, 32]
n_a = [8, 16, 32]
n_steps = [3, 6, 9]
gamma = [1.3, 1.5, 1.7]
n_independent = [1, 2, 4]
n_shared = [1, 2, 4]
momentum = [0.01, 0.02, 0.05]
lambda_sparse  = [0.0001, 0.001, 0.01]
optimizer_lr = [0.00001, 0.0001, 0.001, 0.01]
optimizer_weight_decay = [0.0, 0.0001, 0.001]

args = f"--multirun hparams_search=tabnet_grid " \
       f"experiment=tabnet work_dir=\"{data_path}/models/tabnet\" " \
       f"data_dir=\"{data_path}\" " \
       f"datamodule.path=\"{data_path}\""

os.system(f"sbatch run_tabnet_unn.sh {args}")

#srun python $code_dir/run_tabnet.py --multirun hparams_search=tabnet_grid experiment=tabnet work_dir="/common/home/yusipov_i/data/dnam/datasets/meta/BrainDiseases/variance(0.005)/models/tabnet" data_dir="/common/home/yusipov_i/data/dnam/datasets/meta/BrainDiseases/variance(0.005)" datamodule.path="/common/home/yusipov_i/data/dnam/datasets/meta/BrainDiseases/variance(0.005)"
