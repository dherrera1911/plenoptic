import numpy as np
import pyrtools as pt
from pyrtools import synthetic_images
import torch
from torch.utils.data import Dataset
import matplotlib.pyplot as plt
import scipy.io as sio
from .signal import rescale

data_path = '../data/'

def make_basic_stimuli(size=256, requires_grad=True):
    impulse = np.zeros((size, size))
    impulse[size // 2, size // 2] = 1

    step_edge = synthetic_images.square_wave(size=size, period=size + 1, direction=0, amplitude=1, phase=0)

    ramp = synthetic_images.ramp(size=size, direction=np.pi / 2, slope=1)

    bar = np.zeros((size, size))
    bar[size // 2 - 20:size // 2 + 20, size // 2 - 2:size // 2 + 2] = 1

    curv_edge = synthetic_images.disk(size=size, radius=size / 1.2, origin=(size, size))

    sine_grading = synthetic_images.sine(size) * synthetic_images.gaussian(size, covariance=size)

    square_grading = synthetic_images.square_wave(size, frequency=(.5, .5), phase=2 * np.pi / 3.) \
                     * synthetic_images.gaussian(size, covariance=size)

    polar_angle = synthetic_images.polar_angle(size)

    angular_sine = synthetic_images.angular_sine(size, 6)

    zone_plate = synthetic_images.zone_plate(size)

    fract = synthetic_images.pink_noise(size, fract_dim=.8)

    checkerboard = plt.imread(data_path + 'checkerboard.pgm').astype(float)
    # checkerboard = pt.blurDn(checkerboard, 1, 'qmf9')

    sawtooth = plt.imread(data_path + 'sawtooth.pgm').astype(float)
    # sawtooth = pt.blurDn(sawtooth, 1, 'qmf9')

    reptil_skin = plt.imread(data_path + 'reptil_skin.pgm').astype(float)
    # reptil_skin = pt.blurDn(reptil_skin, 1, 'qmf9')

    # image = plt.imread('/Users/pe/Pictures/umbrella.jpg').astype(float)
    # image = image[500:500+2**11,1000:1000+2**11,0]
    # image = pt.blurDn(image, 4, 'qmf9')
    image = plt.imread(data_path + 'einstein.pgm').astype(float)
    # image = pt.blurDn(image, 1, 'qmf9')

    stim = [impulse, step_edge, ramp, bar, curv_edge,
            sine_grading, square_grading, polar_angle, angular_sine, zone_plate,
            checkerboard, sawtooth, reptil_skin, fract, image]
    stim = [rescale(s) for s in stim]

    stimuli = torch.cat(
        [torch.tensor(s, dtype=torch.float32, requires_grad=requires_grad).unsqueeze(0).unsqueeze(0) for s in stim],
        dim=0)

    return stimuli

if __name__ == '__main__':

    make_basic_stimuli()