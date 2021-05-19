import numpy as np
import torch
from torch import Tensor
import torch.nn.functional as F
from typing import Union, Tuple
import math


def correlate_downsample(image, filt, padding_mode="reflect"):
    """Correlate with a filter and downsample by 2

    Parameters
    ----------
    image: torch.Tensor of shape (batch, channel, height, width)
        Image, or batch of images. Channels are also treated as batches.
    filt: 2-D torch.Tensor
        The filter to correlate with the input image
    padding_mode: string, optional
        One of "constant", "reflect", "replicate", "circular" or "zero" (same as "constant")
    """

    if padding_mode == "zero":
        padding_mode = "constant"
    assert isinstance(image, torch.Tensor) and isinstance(filt, torch.Tensor)

    n_channels = image.shape[1]
    image_padded = same_padding(image, kernel_size=filt.shape, pad_mode=padding_mode)
    return F.conv2d(image_padded, filt.repeat(n_channels, 1, 1, 1), stride=2, groups=n_channels)


def upsample_convolve(image, odd, filt, padding_mode="reflect"):
    """Upsample by 2 and convolve with a filter

    Parameters
    ----------
    image: torch.Tensor of shape (batch, channel, height, width)
        Image, or batch of images. Channels are also treated as batches.
    odd: tuple, list or numpy.ndarray
        This should contain two integers of value 0 or 1, which determines whether
        the output height and width should be even (0) or odd (1).
    filt: 2-D torch.Tensor
        The filter to convolve with the upsampled image
    padding_mode: string, optional
        One of "constant", "reflect", "replicate", "circular" or "zero" (same as "constant")
    """

    if padding_mode == "zero":
        padding_mode = "constant"
    assert isinstance(image, torch.Tensor) and isinstance(filt, torch.Tensor)
    filt = filt.flip((0, 1))

    n_channels = image.shape[1]
    pad_start = np.array(filt.shape) // 2
    pad_end = np.array(filt.shape) - np.array(odd) - pad_start
    pad = np.array([pad_start[1], pad_end[1], pad_start[0], pad_end[0]])
    image_prepad = F.pad(image, tuple(pad // 2), mode=padding_mode)
    image_upsample = F.conv_transpose2d(image_prepad, weight=torch.ones((n_channels, 1, 1, 1), device=image.device),
                                        stride=2, groups=n_channels)
    image_postpad = F.pad(image_upsample, tuple(pad % 2))
    return F.conv2d(image_postpad, filt.repeat(n_channels, 1, 1, 1), groups=n_channels)


def binomial_filter(order_plus_one):
    """returns a vector of binomial coefficients of order (order_plus_one-1)."""
    assert order_plus_one >= 2, "order_plus_one argument must be at least 2"
    kernel = np.array([0.5, 0.5])
    for _ in range(order_plus_one - 2):
        kernel = np.convolve(np.array([0.5, 0.5]), kernel)
    return kernel


def blur_downsample(x, n_scales=1, order_plus_one=5, scale_filter=True):
    """Correlate with a binomial coefficient filter and downsample by 2

    Parameters
    ----------
    x: torch.Tensor of shape (batch, channel, height, width)
        Image, or batch of images. Channels are also treated as batches.
    n_scales: int, optional
        Apply the blur and downsample procedure recursively `n_scales` times.
    order_plus_one: int, optional
        One plus the order of the binomial coefficient filter. Must be at least 2.
        The 2D blurring filter is obtained by computing this 1D filter's outer
        product with itself, and has shape (order_plus_one, order_plus_one).
    scale_filter: bool, optional
        If true (default), the filter sums to 1 (ie. it does not affect the DC
        component of the signal). If false, the filter sums to 2.
    """

    f = np.sqrt(2) * binomial_filter(order_plus_one)
    filt = torch.tensor(np.outer(f, f), dtype=torch.float32, device=x.device)
    if scale_filter:
        filt = filt / 2

    if n_scales > 1:
        x = blur_downsample(x, n_scales-1, order_plus_one, scale_filter)

    if n_scales >= 1:
        res = correlate_downsample(x, filt)
    else:
        res = x

    return res


def upsample_blur(x, odd, order_plus_one=5, scale_filter=True):
    """Upsample by 2 and convolve with a binomial coefficient filter

    Parameters
    ----------
    x: torch.Tensor of shape (batch, channel, height, width)
        Image, or batch of images. Channels are also treated as batches.
    odd: tuple, list or numpy.ndarray
        This should contain two integers of value 0 or 1, which determines whether
        the output height and width should be even (0) or odd (1).
    order_plus_one: int, optional
        One plus the order of the binomial coefficient filter. Must be at least 2.
        The 2D blurring filter is obtained by computing this 1D filter's outer
        product with itself, and has shape (order_plus_one, order_plus_one).
    scale_filter: bool, optional
        If true (default), the filter sums to 4 (ie. it multiplies the signal
        by 4 before the blurring operation). If false, the filter sums to 2.
    """

    f = np.sqrt(2) * binomial_filter(order_plus_one)
    filt = torch.tensor(np.outer(f, f), dtype=torch.float32, device=x.device)
    if scale_filter:
        filt = filt * 2
    return upsample_convolve(x, odd, filt)


def _get_same_padding(
        x: int,
        kernel_size: int,
        stride: int,
        dilation: int
) -> int:
    """Helper function to determine integer padding for F.pad() given img and kernel"""
    pad = (math.ceil(x / stride) - 1) * stride + (kernel_size - 1) * dilation + 1 - x
    pad = max(pad, 0)
    return pad


def same_padding(
        x: Tensor,
        kernel_size: Union[int, Tuple[int, int]],
        stride: Union[int, Tuple[int, int]] = (1, 1),
        dilation: Union[int, Tuple[int, int]] = (1, 1),
        pad_mode: str = "circular",
) -> Tensor:
    """Pad a tensor so that 2D convolution will result in output with same dims."""
    assert len(x.shape) > 2, "Input must be tensor whose last dims are height x width"
    ih, iw = x.shape[-2:]
    pad_h = _get_same_padding(ih, kernel_size[0], stride[0], dilation[0])
    pad_w = _get_same_padding(iw, kernel_size[1], stride[1], dilation[1])
    if pad_h > 0 or pad_w > 0:
        x = F.pad(x,
                  [pad_w // 2, pad_w - pad_w // 2, pad_h // 2, pad_h - pad_h // 2],
                  mode=pad_mode)
    return x
