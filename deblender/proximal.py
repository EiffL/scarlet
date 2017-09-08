from __future__ import print_function, division
import logging
from functools import partial

import numpy as np

from . import operators
from . import proximal_utils

def _prox_strict_monotonic(X, step, seeks, ref_idx, dist_idx, thresh=0, prox_chain=None, **kwargs):
    """Force an intensity profile to be monotonic
    """
    proximal_utils.prox_monotonic(X, step, seeks, ref_idx, dist_idx, thresh)

    # When we daisy-chain the operators, we need to primary ones
    # (positivity, sparsity) last so that they are certainly fulfilled
    if prox_chain is not None:
        X = prox_chain(X, step, **kwargs)
    return X

def build_prox_monotonic(shape, seeks, prox_chain=None, thresh=0):
    """Build the prox_monotonic operator
    """
    if not shape[0] % 2 or not shape[1] % 2:
        err = "Shape must have an odd width and height, received shape {0}".format(shape)
        raise ValueError(err)
    monotonicOp = operators.getRadialMonotonicOp(shape)
    _, refIdx = np.where(monotonicOp.toarray()==1)
    # Get the center pixels
    cx = (shape[1]-1) >> 1
    cy = (shape[0]-1) >> 1
    # Calculate the distance between each pixel and the peak
    x = np.arange(shape[1])
    y = np.arange(shape[0])
    X,Y = np.meshgrid(x,y)
    X = X - cx
    Y = Y - cy
    distance = np.sqrt(X**2+Y**2)
    # Get the indices of the pixels sorted by distance from the peak
    didx = np.argsort(distance.flatten())
    #update the strict proximal operators
    return partial(_prox_strict_monotonic, seeks=seeks, ref_idx=refIdx.tolist(), dist_idx=didx.tolist(), prox_chain=prox_chain, thresh=thresh)

def prox_cone(X, step, G=None):
    """Exact projection of components of X onto cone defined by Gx >= 0"""
    k, n = X.shape
    for i in range(k):
        Y = X[i]

        # Creating set of half-space defining vectors
        Vs = []
        for j in range(0, n):
            add = G[j]
            Vs.append(add)
        Q = find_Q(Vs, n)

        # Finding and using relevant dimensions until a point on the cone is found
        for j in range(n):
            index = find_relevant_dim(Y, Q, Vs)
            if index != -1:
                Y, Q, Vs = use_relevant_dim(Y, Q, Vs, index)
            else:
                break
        X[i] = Y
    return X

def proj(A,B):
    """Returns the projection of A onto the hyper-plane defined by B"""
    return A - (A*B).sum()*B/(B**2).sum()

def proj_dist(A,B):
    """Returns length of projection of A onto B"""
    return (A*B).sum()/(B**2).sum()**0.5

def use_relevant_dim(Y, Q, Vs, index):
    """Uses relevant dimension to reduce problem dimensionality (projects everything onto the
    new hyperplane"""
    projector = Vs[index]
    del Vs[index]
    Y = proj(Y, projector)
    Q = proj(Y, projector)
    for i in range(len(Vs)):
        Vs[i] = proj(Vs[i], projector)
    return Y, Q, Vs

def find_relevant_dim(Y, Q, Vs):
    """Finds a dimension relevant to the problem by 'raycasting' from Y to Q"""
    max_t = 0
    index = -1
    for i in range(len(Vs)):
        Y_p = proj_dist(Y, Vs[i])
        Q_p = proj_dist(Q, Vs[i])
        if Y_p < 0:
            t = -Y_p/(Q_p - Y_p)
        else:
            t = -2
        if t > max_t:
            max_t = t
            index = i
    return index

def find_Q(Vs, n):
    """Finds a Q that is within the solution space that can act as an appropriate target
    (could be rigorously constructed later)"""
    res = np.zeros(n)
    res[int((n-1)/2)] = n
    return res
