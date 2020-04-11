"""
This is the module where the model is defined. It uses the nn.Module as a backbone to create the network structure
"""
# Own modules

# Built in
import math
import numpy as np

# Pytorch module
import torch.nn as nn
import torch.nn.functional as F
import torch
from torch import pow, add, mul, div, sqrt

class Forward(nn.Module):
    def __init__(self, flags):
        super(Forward, self).__init__()

        # Set up whether this uses a Lorentzian oscillator, this is a boolean value
        self.use_lorentz = flags.use_lorentz
        self.use_conv = flags.use_conv
        self.flags = flags

        # Assert the last entry of the fc_num is a multiple of 3 (This is for Lorentzian part)
        if flags.use_lorentz:
            # there is 1 extra parameter for lorentzian setting for epsilon_inf

            self.num_spec_point = 300

            # Create the constant for mapping the frequency w
            w_numpy = np.arange(flags.freq_low, flags.freq_high, (flags.freq_high - flags.freq_low) / self.num_spec_point)

            # Create the tensor from numpy array
            cuda = True if torch.cuda.is_available() else False
            if cuda:
                self.w = torch.tensor(w_numpy).cuda()
            else:
                self.w = torch.tensor(w_numpy)

        """
        General layer definitions:
        """
        # Linear Layer and Batch_norm Layer definitions here
        self.linears = nn.ModuleList([])
        self.bn_linears = nn.ModuleList([])
        for ind, fc_num in enumerate(flags.linear[0:-1]):               # Excluding the last one as we need intervals
            self.linears.append(nn.Linear(fc_num, flags.linear[ind + 1], bias=True))
            self.bn_linears.append(nn.BatchNorm1d(flags.linear[ind + 1], track_running_stats=True, affine=True))

        self.lin_w0 = nn.Linear(self.flags.linear[-1], self.flags.num_lorentz_osc, bias=False)
        self.lin_wp = nn.Linear(self.flags.linear[-1], self.flags.num_lorentz_osc, bias=False)
        self.lin_g = nn.Linear(self.flags.linear[-1], self.flags.num_lorentz_osc, bias=False)
        torch.nn.init.uniform_(self.lin_g.weight, a=0.0, b=0.1)

        if flags.use_conv:
            # Conv Layer definitions here
            self.convs = nn.ModuleList([])
            in_channel = 1                                                  # Initialize the in_channel number
            for ind, (out_channel, kernel_size, stride) in enumerate(zip(flags.conv_out_channel,
                                                                         flags.conv_kernel_size,
                                                                         flags.conv_stride)):
                if stride == 2:     # We want to double the number
                    pad = int(kernel_size/2 - 1)
                elif stride == 1:   # We want to keep the number unchanged
                    pad = int((kernel_size - 1)/2)
                else:
                    Exception("Now only support stride = 1 or 2, contact Ben")

                self.convs.append(nn.ConvTranspose1d(in_channel, out_channel, kernel_size,
                                    stride=stride, padding=pad)) # To make sure L_out double each time
                in_channel = out_channel # Update the out_channel

            self.convs.append(nn.Conv1d(in_channel, out_channels=1, kernel_size=1, stride=1, padding=0))

    def forward(self, G):
        """
        The forward function which defines how the network is connected
        :param G: The input geometry (Since this is a forward network)
        :return: S: The 300 dimension spectra
        """
        out = G

        # initialize the out
        # Monitor the gradient list
        # For the linear part
        for ind, (fc, bn) in enumerate(zip(self.linears, self.bn_linears)):
            #print(out.size())
            if ind < len(self.linears) - 0:
                out = F.relu(bn(fc(out)))                                   # ReLU + BN + Linear
            else:
                out = bn(fc(out))

        # for ind, fc in enumerate(self.linears):
        #     out = F.relu(fc(out))

        # If use lorentzian layer, pass this output to the lorentzian layer
        if self.use_lorentz:
            # out = torch.sigmoid(out)            # Lets say w0, wp is in range (0,5) for now
            # out = F.relu(out) + 0.00001

            # Get the out into (batch_size, num_lorentz_osc, 3) and the last epsilon_inf baseline
            # epsilon_inf = out[:,-1]  # For debugging purpose now

            # Set epsilon_inf to be a constant universal value here
            # epsilon_inf = torch.tensor([10], requires_grad=False).expand_as(epsilon_inf)
            # if torch.cuda.is_available():
            #     epsilon_inf = epsilon_inf.cuda()
            # out = last_Lor_layer.view([-1, int(out.size(1)/3), 3])

            # Get the list of params for lorentz, also add one extra dimension at 3rd one to
            # w0 = out[:, :, 0].unsqueeze(2) * 5
            # wp = out[:, :, 1].unsqueeze(2) * 5
            # g = out[:, :, 2].unsqueeze(2) * 0.5
            #nn.init.xavier_uniform_(g)
            # This is for debugging purpose (Very slow), recording the output tensors
            # self.w0s = w0.data.cpu().numpy()
            # self.wps = wp.data.cpu().numpy()
            # self.gs = g.data.cpu().numpy()

            #print(g.size())
            # self.eps_inf = epsilon_inf.data.cpu().numpy()

            w0 = F.relu(self.lin_w0(out).unsqueeze(2))
            wp = F.relu(self.lin_wp(out).unsqueeze(2))
            g = F.relu(self.lin_g(out).unsqueeze(2))
            # g = torch.sigmoid(self.lin_g(out).unsqueeze(2))


            # Expand them to the make the parallelism, (batch_size, #Lor, #spec_point)
            w0 = w0.expand(out.size(0), self.flags.num_lorentz_osc, self.num_spec_point)
            wp = wp.expand_as(w0)
            g = g.expand_as(w0)
            w_expand = self.w.expand_as(g)
            """
            Testing code
            #print("c1 size", self.c1.size())
            #print("w0 size", w0.size())
            End of testing module
            """

            # e1 = div(mul(pow(wp, 2), add(pow(w0, 2), -pow(w_expand, 2))),
            #          add(pow(add(pow(w0, 2), -pow(w_expand, 2)), 2), mul(pow(w_expand, 2), pow(g, 2))))
            e2 = div(mul(pow(wp, 2), mul(w_expand, g)),
                     add(pow(add(pow(w0, 2), -pow(w_expand, 2)), 2), mul(pow(w_expand, 2), pow(g, 2))))

            # self.e2 = e2.data.cpu().numpy()                 # This is for plotting the imaginary part
            # self.e1 = e1.data.cpu().numpy()                 # This is for plotting the imaginary part
            """
            debugging purposes: 2019.12.10 Bens code for debugging the addition of epsilon_inf
            print("size of e1", e1.size())
            print("size pf epsilon_inf", epsilon_inf.size())
            """
            # the correct calculation should be adding up the es
            # e1 = torch.sum(e1, 1)
            e2 = torch.sum(e2, 1)

            # epsilon_inf = epsilon_inf.unsqueeze(1).expand_as(e1)        #Change the shape of the epsilon_inf
            #
            #
            # e1 += epsilon_inf
            #
            # # print("e1 size", e1.size())
            # # print("e2 size", e2.size())
            # e12 = pow(e1, 2)
            # e22 = pow(e2, 2)
            #
            # n = sqrt(0.5 * add(sqrt(add(e12, e22)), e1))
            # k = sqrt(0.5 * add(sqrt(add(e12, e22)), -e1))
            # n_12 = pow(n+1, 2)
            # k2 = pow(k, 2)
            #
            # # T without absorption
            # # T = div(4*n, add(n_12, k2)).float()
            #
            #
            # d, _ = torch.max(G[:, 4:], dim=1)
            # #print(d)
            # if self.flags.normalize_input:
            #     d = d * (self.flags.geoboundary[-1]-self.flags.geoboundary[-2]) * 0.5 + (self.flags.geoboundary[-1]+self.flags.geoboundary[-2]) * 0.5
            # #print(d)
            # #print(d.size())
            # d = d.unsqueeze(1).expand_as(k)
            # #print(d.size())
            # ab = torch.exp(-0.0005 * 4 * math.pi * mul(d, k))
            # T_coeff = div(4*n, add(n_12, k2))
            # T = mul(T_coeff, ab).float()
            T = e2.float()

            """
            Debugging and plotting (This is very slow, comment to boost)
            """

            # print("T size",T.size())
            # Last step, sum up except for the 0th dimension of batch_size (deprecated since we sum at e above)
            # T = torch.sum(T, 1).float()
            return T

        # The normal mode to train without Lorentz
        if self.use_conv:
            out = out.unsqueeze(1)                                          # Add 1 dimension to get N,L_in, H
            # For the conv part
            for ind, conv in enumerate(self.convs):
                out = conv(out)

            # Final touch, because the input is normalized to [-1,1]
            # S = tanh(out.squeeze())
            out = out.squeeze()
        return out

