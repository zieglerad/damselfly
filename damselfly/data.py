import h5py
import numpy as np
import os
import pickle as pkl
import torch

def EggReader(pathtoegg, Vrange=5.5e-8, nbit=8):

    f=h5py.File(pathtoegg,'r')
    dset=f['streams']['stream0']['acquisitions']['0']
    channels=list(f['channels'].keys())

    Nsamp=dset.shape[1]//(2*len(channels))
    ind=[]
    for ch in channels:
        ind.append(int(ch.split('l')[1]))
        #print(ch.split('l'))
    ind=np.array(ind)

    data=dset[0,:].reshape(ind.size,2*Nsamp)

    Idata=np.float64(data[:,np.arange(0,2*Nsamp,2)])
    Qdata=np.float64(data[:,np.arange(1,2*Nsamp,2)])

    for i in range(len(channels)):
        Idata[i,:]-=np.mean(Idata[i,:])
        Qdata[i,:]-=np.mean(Qdata[i,:])

    for i in range(len(channels)):
        Idata[i,:]*=Vrange/(2**nbit)
        Qdata[i,:]*=Vrange/(2**nbit)

    complexdata=Idata+1j*Qdata

    f.close()

    return complexdata
    
def SumSignals(data): # only works for on axis

    return data.sum(0)
    
def GenerateLabeledBinaryDataset(summed_signals, path, n_copies_train = 32, n_copies_test = 8, percent_noise = 0.2, T = 10, domain = 'time'):

    data_list = np.asarray(summed_signals['x'])[np.argsort(summed_signals['pa'])]
    energies = np.asarray(summed_signals['E'])[np.argsort(summed_signals['pa'])]
    pitch_angles = np.sort(summed_signals['pa'])


    train_list = data_list[np.arange(0, len(pitch_angles), 2)]
    test_list = data_list[np.arange(1, len(pitch_angles), 2)]
    
    N_train = len(train_list)
    N_test = len(test_list)
    N_samp = len(train_list[0])
    
    train_data_list = []
    train_pa = []
    
    test_data_list = []
    test_pa = []
    
    val_data_list = []
    
    for n in range(N_train):
        for m in range(n_copies_train):
            signal = train_list[n]
            noisy_signal = AddNoise(signal, T, domain = domain, N_samp = N_samp)
            
            train_data_list.append(np.array([noisy_signal.real, noisy_signal.imag]))
            train_pa.append((pitch_angles[np.arange(0,len(pitch_angles), 2)])[n])
    print('Done with training data.')
    for n in range(N_test):
        for m in range(n_copies_test):
            signal = test_list[n]
            noisy_signal = AddNoise(signal, T, domain = domain, N_samp = N_samp)
            
            test_data_list.append(np.array([noisy_signal.real, noisy_signal.imag]))
            test_pa.append((pitch_angles[np.arange(1, len(pitch_angles), 2)])[n])
    print('Done with test data.')
    for n in range(N_test):
        for m in range(n_copies_test):
            signal = test_list[n]
            noisy_signal = AddNoise(signal, T, domain = domain, N_samp = N_samp)
            
            val_data_list.append(np.array([noisy_signal.real, noisy_signal.imag]))
    print('Done with validation data.')
    for n in range(int((percent_noise / (1-percent_noise)) * len(train_data_list))):
        signal = np.zeros(N_samp)
        noisy_signal = AddNoise(signal, T, domain = domain, N_samp = N_samp)
        train_data_list.append(np.array([noisy_signal.real, noisy_signal.imag]))
    for n in range(int(1.0 * len(test_data_list))):
        signal = np.zeros(N_samp)
        noisy_signal = AddNoise(signal, T, domain = domain, N_samp = N_samp)
        test_data_list.append(np.array([noisy_signal.real, noisy_signal.imag]))
    for n in range(int(1.0 * len(val_data_list))):
        signal = np.zeros(N_samp)
        noisy_signal = AddNoise(signal, T, domain = domain, N_samp = N_samp)
        val_data_list.append(np.array([noisy_signal.real, noisy_signal.imag]))
    
    meta = {'train_pa': train_pa, 'test_pa': test_pa, 'temp': T}
    
    print('Converting to tensors')
    data_set = {'train': torch.tensor(train_data_list, dtype=torch.float32), 'test': torch.tensor(test_data_list, dtype=torch.float32),
    'val': torch.tensor(val_data_list, dtype=torch.float32), 'meta': meta}
    return data_set
    
def GenerateLabeledMulticlassDataset(summed_signals, path, class_type = 'pa', n_copies = 32, n_copies_train = 32, n_copies_test = 8, percent_noise = 0.2, T = 10, domain = 'time', split = True, binary = False, Nch=2, N_multiclass = 1):

    class_params_unique = np.unique(summed_signals[class_type])
    class_params = np.array(summed_signals[class_type])
    
    signal_list = np.asarray(summed_signals['x'])[np.argsort(class_params)]
    class_params = np.sort(class_params)
    
    if not binary:
        if N_multiclass > 1:
            class_params_split = np.array_split(class_params_unique, N_multiclass)
        else:
            raise ValueError('Trying to generate multiclass data, but N_multiclass is not greater than 1.')
    
    data_set = {}
    #print(class_params_split)
    
    if split:
        set_splits = ['train', 'test', 'val']
        train_inds = np.arange(0, len(class_params), 2)
        test_inds = np.arange(1, len(class_params), 2)
        
        train_list = signal_list[train_inds]
        train_params = class_params[train_inds]
        
        val_list = signal_list[test_inds]
        test_list = signal_list[test_inds]
        
        val_params = class_params[test_inds]
        test_params = class_params[test_inds]
        
        dset_list = [train_list, val_list, test_list]
        dset_param_list = [train_params, val_params, test_params]
    else:
        dset_list = [signal_list]
        dset_param_list = [class_params]

    for iset, dset in enumerate(dset_list):
        N_dset = len(dset)
        N_samp = len(dset[0])
        
        data_list = []
        label_list = []

        if iset == 0:
            for n in range(N_dset):
                if split:
                    n_copies_set0 = n_copies_train
                else:
                    n_copies_set0 = n_copies
                for m in range(n_copies_set0):
                    signal = dset[n]
                    noisy_signal = AddNoise(signal, T, domain = domain, N_samp = N_samp)
                    if Nch == 3:
                        data_list.append(
                            np.array([noisy_signal.real, 
                                    noisy_signal.imag, 
                                    noisy_signal.real ** 2 + noisy_signal.imag ** 2
                                    ]))
                    else:
                        data_list.append(
                            np.array([noisy_signal.real,
                                    noisy_signal.imag
                                    ]))
                    if binary:
                        label_list.append(1)
                    else:
                        for l, class_param_range in enumerate(class_params_split):
                            where_signal_param_close_to_class_param = np.where(
                                                                      abs(class_param_range -dset_param_list[iset][n]) <= 1e-5
                                                                      )[0]
                            if len(where_signal_param_close_to_class_param) > 0:
                                #print(l + 1, where_signal_param_close_to_class_param)
                                label_list.append(l + 1)
                        #label_list.append(np.where(abs(class_params_unique - dset_param_list[iset][n]) <= 1e-5)[0][0] + 1)
            for n in range(int((percent_noise / (1-percent_noise)) * len(data_list))):
                signal = np.zeros(N_samp)
                noisy_signal = AddNoise(signal, T, domain = domain, N_samp = N_samp)
                if Nch == 3:
                    data_list.append(
                        np.array([noisy_signal.real,
                                 noisy_signal.imag,
                                 noisy_signal.real ** 2 + noisy_signal.imag ** 2
                                 ]))
                else:
                    data_list.append(
                        np.array([noisy_signal.real,
                                noisy_signal.imag
                                ]))
                label_list.append(0)
            print(f'Done with set {iset + 1}.')
            
        if iset > 0:
            for n in range(N_dset):
                n_copies_set12 = n_copies_test
                for m in range(n_copies_set12):
                    signal = dset[n]
                    noisy_signal = AddNoise(signal, T, domain = domain, N_samp = N_samp)
                    if Nch == 3:
                        data_list.append(
                            np.array([noisy_signal.real,
                                     noisy_signal.imag,
                                     noisy_signal.real ** 2 + noisy_signal.imag ** 2
                                     ]))
                    else:
                        data_list.append(
                            np.array([noisy_signal.real,
                                    noisy_signal.imag
                                    ]))
                    if binary:
                        label_list.append(1)
                    else:
                        for l, class_param_range in enumerate(class_params_split):
                            where_signal_param_close_to_class_param = np.where(
                                                                      abs(class_param_range -dset_param_list[iset][n]) <= 1e-5
                                                                      )[0]
                            if len(where_signal_param_close_to_class_param) > 0:
                                label_list.append(l + 1)
                        #label_list.append(np.where(abs(class_params_unique - dset_param_list[iset][n]) <= 1e-5)[0][0] + 1)
            for n in range(len(data_list)):
                signal = np.zeros(N_samp)
                noisy_signal = AddNoise(signal, T, domain = domain, N_samp = N_samp)
                if Nch == 3:
                    data_list.append(
                        np.array([noisy_signal.real,
                                 noisy_signal.imag,
                                 noisy_signal.real ** 2 + noisy_signal.imag ** 2
                                 ]))
                else:
                    data_list.append(
                        np.array([noisy_signal.real,
                                noisy_signal.imag
                                ]))
                label_list.append(0)
            print(f'Done with set {iset + 1}.')

        print('Converting to tensor')
        if split:
            data_set.update({set_splits[iset]: 
                                {
                                'X': torch.tensor(data_list, dtype=torch.float32),
                                'y': torch.tensor(label_list, dtype=torch.long)
                                }
                            })
        else:
            data_set.update({
                            'X': torch.tensor(data_list, dtype=torch.float32),
                            'y': torch.tensor(label_list, dtype=torch.long)
                            })
    return data_set
    
def AddNoise(data, T):

    size = data.size
    shape = data.shape
    var = 1.38e-23 * 200e6 * 50 * T / 8192
    
    noise = np.random.multivariate_normal([0, 0], np.eye(2) * var / 2, size)
    noise = noise[:, 0] + 1j * noise[:, 1]
    

    return data + noise.reshape(shape)
        
    

class DFDataset(torch.utils.data.Dataset):

    # class to interface hdf5 datafile with pytorch dataloader class
    # specify the path to the h5 file and the dataset type i.e. 'train', 'test', or 'val'
    # option to normalize the data to [-1, 1] (default)
    # loads data into RAM (torch tensor) automatically, could be changed to load lazily
    
    def __init__(self, filepath, dset_type, norm=True):
        super().__init__
        
        self.data = []
        self.label = []
        self.norm = norm
        self._load_data(filepath, dset_type, self.norm)
        
        
    def __get_item__(self, index):
        
        x = self.data['data'][index, :, :]
        y = self.data['label'][index]
        
        return (x,y)
    
    def __len__(self):
        return len(self.data['label'][:])

    def _load_data(self, filepath, dset_type, norm):
    
        h5file = h5py.File(filepath, 'r')
        h5group = h5file[dset_type]
        
        for key in h5group.keys():

            if key == 'data':

                if norm:
                    self.data = torch.tensor(self._norm_data(h5group[key][:, :, :]), dtype=torch.float)
                else:
                    self.data = torch.tensor(h5group[key][:, :, :], dtype=torch.float)
                
            elif key == 'label':
                self.label = torch.tensor(h5group[key][:], dtype=torch.long)
                
        h5file.close()
        
    def _norm_data(self, data):
        norm = (1 / np.max(abs(data), 2)).reshape((data.shape[0], data.shape[1], 1)).repeat(data.shape[2], axis=2)
        return norm * data



