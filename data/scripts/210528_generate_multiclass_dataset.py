import numpy as np
import matplotlib.pyplot
import pickle as pkl
import damselfly as df
import os

domain = 'freq'
split_data = False
Nch = 3
raw_data_path = '/home/az396/project/damselfly/data/raw_summed_signals'
raw_data_name = f'{domain}/210528_df2.pkl'

dataset_date = '210607'
dataset_type = 'df2_multiclass_val'
multiclass_parameter = 'pa'
save_data_path = '/home/az396/project/damselfly/data/datasets'
binary = False


with open(os.path.join(raw_data_path, raw_data_name), 'rb') as infile:
	summed_signals = pkl.load(infile)

noise_temps = [10.0]

for temp in noise_temps:
    print(temp)
    save_data_name = f'{domain}/{dataset_date}_{dataset_type}_ch{Nch}_class_{multiclass_parameter}_split_{split_data}_temp{temp}.pkl'
    data_set = df.data.GenerateLabeledMulticlassDataset(
                                                        summed_signals, 
                                                        os.path.join(save_data_path, save_data_name), 
                                                        multiclass_parameter, 
                                                        T=temp, 
                                                        domain=domain, 
                                                        n_copies_train=25, 
                                                        n_copies_test=10,
                                                        n_copies=8,
                                                        percent_noise=0.2,
                                                        split=split_data,
                                                        binary=binary,
                                                        Nch=Nch, 
                                                        N_multiclass = 4
                                                      )
    
    #print(data_set['train']['y'].sum(dim=0))
    #print(data_set['test']['y'].sum(dim=0))
    with open(os.path.join(save_data_path, save_data_name), 'wb') as outfile:
        pkl.dump(data_set, outfile)





