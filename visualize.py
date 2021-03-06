import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np
import sys
import pandas as pd
import plotly.express as px
import os
import seaborn as sns; sns.set()
import shutil

class HMpoint(object):
    """
    This is a HeatMap point class where each object is a point in the heat map
    properties:
    1. BV_loss: best_validation_loss of this run
    2. feature_1: feature_1 value
    3. feature_2: feature_2 value, none is there is no feature 2
    """

    def __init__(self, bv_loss, f1, f2=None, f1_name='f1', f2_name='f2'):
        self.bv_loss = bv_loss
        self.feature_1 = f1
        self.feature_2 = f2
        self.f1_name = f1_name
        self.f2_name = f2_name
        # print(type(f1))

    def to_dict(self):
        return {
            self.f1_name: self.feature_1,
            self.f2_name: self.feature_2,
            self.bv_loss: self.bv_loss
        }

class Data_Walker():
    def __init__(self, dir, thresh, skip=None, end=None):
        self.skip = skip
        self.end = end
        self.dir = dir
        self.thresh = thresh
        self.Pop = [2000,1500,1000, 500]#[50, 100, 200, 500]
        self.Trunc = [0.1,0.2,0.4,0.5]#[0.02, 0.05,0.1,0.15,0.2]
        self.Mut = [0.02,0.01,0.001,0.1,0.5,1]
        self.Insertion = [0.05, 0.3, 0.45] #[0.01,0.05,0.1,0.2,0.5]
        self.K_Nearest = [0.1, 0.05, 0.005, 0.025] #self.Trunc


    def exp_walk2(self, func_string):
        pre_frame = []
        for folder in os.listdir(self.dir):
            if folder == "imgs":
                continue
            if func_string.find('h') != -1:
                d_row = self.add_pc_data('/'+folder)
                pre_frame.append(d_row)
        return pre_frame

    """
    def count_successful_gen(self, folder):
        with open(self.dir+folder+'/parameters.txt', "r") as f:
            content = f.read()
            p_dict = eval(content)
            d_ratio = np.array(p_dict['distance_ratio'])

        bool_count = d_ratio < self.thresh
        gen_count = np.sum(bool_count)
        p_dict['suc_gen'] = gen_count

        with open(self.dir+folder+'/parameters.txt','w') as f:
            f.truncate()
            print(p_dict,file=f)"""

    def add_pc_data(self, folder):
        print("Folder: ", folder)
        row = None
        with open(self.dir+folder+'/parameters.txt','r') as f:
            content = f.read()
            p_dict = eval(content)
            #row = [p_dict['pop_size'], p_dict['trunc_threshold'],p_dict['mutation_power'],p_dict['insertion'],p_dict['k']]
            num_hidden_layers = len(p_dict['linear']) - 2
            num_nodes = p_dict['linear'][1]
            row = [p_dict['reg_scale'], p_dict['lr'], num_nodes,num_hidden_layers,p_dict['best_validation_loss']]

        return(row)


    def plot(self, func_string):
        preFrame = self.exp_walk2(func_string)
        cols = ['Regularization', 'LRate', 'Nodes', 'Hidden_Layers', 'Validation_Loss']
        dFrame = pd.DataFrame(np.array(preFrame), columns=cols)
        print(dFrame)

        self.pc(dFrame,cols)
        #self.heat_map(dFrame,cols)


    def pc(self, dFrame,cols):
        for up_bound in [15,1,0.1,0.025,0.015]:
            dplot = dFrame[dFrame.Validation_Loss.between(0, up_bound)]
            print(dplot)
            fig = px.parallel_coordinates(dplot, color='Validation_Loss', dimensions=[cols[0],cols[2],cols[3],cols[1]],
                                      title="Plot restricted to Gradient Descent Runs below MSE {}".format(up_bound))
            fig.write_image(self.dir + '/imgs/GD_upperbounded_{}.jpg'.format(up_bound))
            fig.show()

        '''
        for i in range(lw_bound,0,-1):
            dplot = dFrame[dFrame.Metric.between(i,483)]
            fig = px.parallel_coordinates(dplot, color='Metric', dimensions=cols[0:5],
                                title="Plot with threshold at {}, restricted to metrics above {}".format(self.thresh,i))
            fig.write_image(self.dir+'/imgs/fig_{}.jpg'.format(i))
        '''

        fig.show()

    def heat_map(self, dFrame,cols):
        HeatMap_dir = self.dir+'/../Heat_Maps'
        folders = os.listdir(self.dir)
        folders.append('P5000_T0.5_M0.03_K0.0005')
        for i in range(len(dFrame)):
            print(dFrame.iloc[i], folders[i])
        muts = dFrame.Mutation.unique()

        for m in muts:
            filept1 = 'Mutation_{}_'.format(m)
            mframe = dFrame[dFrame['Mutation'] == m]

            ' Create heatmaps with pop vs. top for each k'
            ks = mframe.K_ratio.unique()
            for k in ks:
                filept2 = 'K-Ratio_{}/'.format(k)
                frame = mframe[mframe['K_ratio'] == k]
                frame = frame[['Metric','Pop','Truncation_ratio']]
                print(frame)
                indices = frame.index.values.tolist()

                for idx in indices:
                    print(idx)
                    shutil.copytree(self.dir+'/'+folders[idx],HeatMap_dir+'/'+filept1+filept2+folders[idx])

            ' Create heatmaps with pop vs. k for each top'
            ts = mframe.Truncation_ratio.unique()
            for t in ts:
                filept2 = 'Truncation-Ratio_{}/'.format(t)
                frame = mframe[mframe['Truncation_ratio'] == t]
                frame = frame[['Metric','Pop','K_ratio']]
                print(frame)
                indices = frame.index.values.tolist()

                for idx in indices:
                    print(idx)
                    shutil.copytree(self.dir+'/'+folders[idx],HeatMap_dir+'/'+filept1+filept2+folders[idx])


            ' Create heatmaps with top vs. k for each pop'
            ps = mframe.Pop.unique()
            for p in ps:
                filept2 = 'Population_{}/'.format(p)
                frame = mframe[mframe['Pop'] == p]
                frame = frame[['Metric','K_ratio','Truncation_ratio']]
                print(frame)
                indices = frame.index.values.tolist()

                for idx in indices:
                    print(idx)
                    shutil.copytree(self.dir+'/'+folders[idx],HeatMap_dir+'/'+filept1+filept2+folders[idx])

        '''
            ' Create heatmaps with pop vs. k for each top'
            ts = mframe.Truncation_ratio.unique()
            for t in ts:
                tframe = mframe[mframe['Truncation_ratio'] == t]
                print(tframe.head())

            ' Create heatmaps with top vs. k for each pop'
            pops = mframe.Pop.unique()
            for p in pops:
                pframe = mframe[mframe['Pop'] == p]
                print(pframe.head())
        '''

class Scatter_Animator():
    def __init__(self, name, total_time,x_lim,y_lim):
        super(Scatter_Animator, self).__init__()
        self.name = name
        self.total_time = total_time
        self.x_lim = y_lim
        self.y_lim = x_lim

    def animate(self):
        ' Create 2d Parameter Scatter Animation '

        # Load stored data
        arcv_mod = np.load(self.name+"/arcv_mod.npz")["arr_0"]
        pop = np.load(self.name+"/pop.npz")["arr_0"]
        elite_idx = np.load(self.name+"/elite_idx.npz")["arr_0"]
        arcv_term_idx = np.load(self.name+"/arcv_term_idx.npz")["arr_0"]
        avg_top = np.load(self.name+"/avg_top.npz")['arr_0']
        furthest = np.load(self.name+"/furthest.npz")["arr_0"]

        avg_top = np.squeeze(np.array(avg_top))
        furthest = np.squeeze(np.array(furthest))

        '''
        mutates = []
        for gen in range(len(pop)):
            mutates.append([])
            for el in range(len(elite_idx[0])):
                mutates[gen].append(np.load(self.name+"/mutates/gen_{}_elite_{}.npz".format(gen,el))["arr_0"])
        mutates = np.array(mutates)
        '''

        # Setting Up master frame array
        master = np.empty((1, 2))
        colormap = np.array([(0, 0, 1, 1), (1, 0, 0, 0.5), (0, 1, 0, 1), (1, 1, 1, 1), (1, 1, 0, 1), (0,1,1,1)])
        m_c = np.array([0], dtype=np.int32)
        master_frame_len = [0]

        for gen in range(len(pop)):
            # Frame 1: master = array of pop (blue) followed by archive (red)
            gen_pop = pop[gen]
            gen_arcv = arcv_mod[0:arcv_term_idx[gen]]
            champions = np.empty((1, 2))

            # Add population in this generation to master
            master = np.vstack((master, gen_pop))
            m_c = np.concatenate((m_c, np.array([0] * len(gen_pop), dtype=np.int32)))
            # Add archived models from 0 up until this generation to master
            if np.any(gen_arcv):
                master = np.vstack((master, gen_arcv))
                m_c = np.concatenate((m_c, np.array([1] * arcv_term_idx[gen], dtype=np.int32)))

            if gen == 0:
                master = np.delete(master, 0, 0)
                m_c = np.delete(m_c, 0, 0)
            else:
                for g in range(gen):
                    champ = pop[g][elite_idx[g][0]]
                    champions = np.vstack((champions, champ))
                champions = np.delete(champions, 0, 0)
                master = np.vstack((master, champions))
                m_c = np.concatenate((m_c, np.array([4] * len(champions), dtype=np.int32)))

            master = np.vstack((master,avg_top[0:gen]))
            master = np.vstack((master,furthest[gen]))
            m_c = np.concatenate((m_c, np.array([3] * gen + [5], dtype=np.int32)))

            master_frame_len.append(len(master))

            # Frame 2: Master = array of truncation survivors (blue) followed by archive (red)
            gen_elite = pop[gen][elite_idx[gen][0:len(elite_idx[gen])]]

            master = np.vstack((master, gen_elite))
            m_c = np.concatenate((m_c, np.array([2] * len(gen_elite), dtype=np.int32)))

            if np.any(gen_arcv):
                master = np.vstack((master, gen_arcv))
                m_c = np.concatenate((m_c, np.array([1] * arcv_term_idx[gen], dtype=np.int32)))

            if gen > 0:
                master = np.vstack((master, champions))
                m_c = np.concatenate((m_c, np.array([4] * len(champions), dtype=np.int32)))

            master = np.vstack((master,avg_top[0:gen]))
            m_c = np.concatenate((m_c, np.array([3] * gen, dtype=np.int32)))

            master_frame_len.append(len(master))

        '''
            # Frames 3 -> 3 + trunc_threshold: Master = array of top, mutations, and archive
            for i in range(len(elite_idx[0])):
                hi_lite = gen_elite[1:i + 1]
                muts = mutates[gen][i]

                lited = np.empty((1, 2))
                for m in mutates[gen][0:i]:
                    if not np.any(m):
                        continue
                    z = np.array(m)
                    lited = np.vstack((lited, z))
                lited = np.delete(lited, 0, 0)

                not_lit = gen_elite[i + 1:len(gen_elite)]

                champions = np.empty((1, 2))
                for g in range(gen + 1):
                    champ = pop[g][elite_idx[g][0]]
                    champions = np.vstack((champions, champ))
                champions = np.delete(champions, 0, 0)

                master = np.vstack((master, lited))
                master = np.vstack((master, not_lit))
                m_c = np.concatenate((m_c, np.array([0] * len(lited) + [0] * len(not_lit), dtype=np.int32)))

                if np.any(gen_arcv):
                    master = np.vstack((master, gen_arcv))
                    m_c = np.concatenate((m_c, np.array([1] * arcv_term_idx[gen], dtype=np.int32)))

                master = np.vstack((master, hi_lite))
                m_c = np.concatenate((m_c, np.array([2] * len(hi_lite), dtype=np.int32)))

                if np.any(muts):
                    master = np.vstack((master, muts))
                    m_c = np.concatenate((m_c, np.array([3] * len(muts), dtype=np.int32)))

                master = np.vstack((master, champions))
                m_c = np.concatenate((m_c, np.array([4] * len(champions), dtype=np.int32)))

                master_frame_len.append(len(master))
        '''

        # Initial Figure frame
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.set(xlim=self.x_lim, ylim=self.y_lim)
        scat = ax.scatter(master[0:master_frame_len[1]][:, 0], master[0:master_frame_len[1]][:, 1],
                          c=colormap[m_c[0:master_frame_len[1]]])
        gen_text = ax.text(self.x_lim[0]+0.1, self.y_lim[1]-0.2, 'gen 0')
        gen_text.set_backgroundcolor((1, 1, 1))
        ax.set_facecolor((0, 0, 0))
        plt.xlabel("p1")
        plt.ylabel("p2")


        # Update Function
        def animate_scatter(i):
            step = ['Population', 'Truncation'] + ['Mutation'] * len(elite_idx[0]) # = truncation threshold
            modulus = i % 2#(2 + len(elite_idx[0]))
            gen = int(i / 2)#(2 + len(elite_idx[0])))

            scat.set_offsets(master[master_frame_len[i]:master_frame_len[i + 1]])
            scat.set_color(colormap[m_c[master_frame_len[i]:master_frame_len[i + 1]]])
            gen_text.set_text('Gen {}: {}'.format(gen, step[modulus]))


        # Animation Writer
        num_frames = len(pop) * 2 #(2 + len(elite_idx[0]))
        Scatter_animation = FuncAnimation(fig, animate_scatter, interval=1, frames=num_frames)
                                          #frames=len(pop) * (2 + len(elite_idx[0])))

        fps = num_frames/self.total_time
        Scatter_animation.save("{}/Run.gif".format(self.name, self.name), fps=fps, writer='Pillow')

if __name__ == '__main__':
    #name = './ga-pytorch/results/sweeps/sweep_03'
    name = './models/sweep'
    if len(sys.argv) > 1:
        func = sys.argv[1]
    if len(sys.argv) > 2:
        name = sys.argv[2]

    print("Function: ",func,"\tDirectory: ",name," is being used")

    thresh = 0.4
    skip = None
    end = None

    if func =='a':
        total_time = 5
        x_lim = (-10, 10)
        y_lim = (-10, 10)
        s = Scatter_Animator(name, total_time, x_lim, y_lim)
        s.animate()
    if func =='e':
        d = Data_Walker(name, thresh, skip, end)
        d.exp_walk2(func)
    if func =='h' or func=='eh':
        d = Data_Walker(name, thresh, skip, end)
        d.plot(func)