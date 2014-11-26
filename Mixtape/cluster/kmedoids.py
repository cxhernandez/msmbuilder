# Author: Robert McGibbon <rmcgibbo@gmail.com>
# Contributors:
# Copyright (c) 2014, Stanford University
# All rights reserved.

# Mixtape is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 2.1
# of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with Mixtape. If not, see <http://www.gnu.org/licenses/>.

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

from __future__ import absolute_import, print_function, division

from operator import itemgetter
import numpy as np
from sklearn.base import ClusterMixin, TransformerMixin

from . import MultiSequenceClusterMixin
from . import _kmedoids
from .. import libdistance
from ..base import BaseEstimator


class _KMedoids(ClusterMixin, TransformerMixin):
    """K-Medoids clustering

    Parameters
    ----------
    n_clusters : int, optional, default: 8
        The number of clusters to be found.
    n_passes : int, default=1
        The number of times clustering is performed. Clustering is performed
        n_passes times, each time starting from a different (random) initial
        assignment.
    metric : {"euclidean", "sqeuclidean", "cityblock", "chebyshev", "canberra",
              "braycurtis", "hamming", "jaccard", "cityblock", "rmsd"}
        The distance metric to use. metric = "rmsd" requires that sequences
        passed to ``fit()`` be ```md.Trajectory```; other distance metrics
        require ``np.ndarray``s.
    random_state : integer or numpy.RandomState, optional
        The generator used to initialize the centers. If an integer is
        given, it fixes the seed. Defaults to the global numpy random
        number generator.

    Attributes
    ----------
    cluster_ids_ : array, [n_clusters]
        Index of the data point that each cluster label corresponds to.
    labels_ : array, [n_samples,]
        The label of each point is an integer in [0, n_clusters).
    inertia_ : float
        Sum of distances of samples to their closest cluster center.
    """

    def __init__(self, n_clusters=8, n_passes=1, metric='euclidean',
                 random_state=None):
        self.n_clusters = n_clusters
        self.n_passes = n_passes
        self.metric = metric
        self.random_state = random_state

    def fit(self, X, y=None):
        if self.n_passes < 1:
            raise ValueError('n_passes must be greater than 0. got %s' %
                             self.n_passes)
        if self.n_clusters < 1:
            raise ValueError('n_passes must be greater than 0. got %s' %
                             self.n_clusters)

        dmat = libdistance.pdist(X, metric=self.metric)
        ids, self.inertia_, _ = _kmedoids.kmedoids(
            self.n_clusters, dmat, self.n_passes,
            random_state=self.random_state)

        self.labels_, mapping = _kmedoids.contigify_ids(ids)
        smapping = sorted(mapping.items(), key=itemgetter(1))
        self.cluster_ids_ = np.array(smapping)[:, 0]
        self.cluster_centers_ = X[self.cluster_ids_]

        return self

    def predict(self, X):
        """Predict the closest cluster each sample in X belongs to.

        In the vector quantization literature, `cluster_centers_` is called
        the code book and each value returned by `predict` is the index of
        the closest code in the code book.

        Parameters
        ----------
        X : array-like, shape = [n_samples, n_features]
            New data to predict.

        Returns
        -------
        Y : array, shape [n_samples,]
            Index of the closest center each sample belongs to.
        """
        labels, inertia = libdistance.assign_nearest(
            X, self.cluster_centers_, metric=self.metric)
        return labels

    def fit_predict(self, X, y=None):
        return self.fit(X, y).labels_


class KMedoids(MultiSequenceClusterMixin, _KMedoids, BaseEstimator):
    _allow_trajectory = True
    __doc__ = _KMedoids.__doc__[: _KMedoids.__doc__.find('Attributes')] + \
    '''
    Attributes
    ----------
    `cluster_centers_` : array, [n_clusters, n_features]
        Coordinates of cluster centers

    `labels_` : list of arrays, each of shape [sequence_length, ]
        `labels_[i]` is an array of the labels of each point in
        sequence `i`. The label of each point is an integer in
        [0, n_clusters).
    '''

    def fit(self, sequences, y=None):
        """Fit the kcenters clustering on the data

        Parameters
        ----------
        sequences : list of array-like, each of shape [sequence_length, n_features]
            A list of multivariate timeseries, or ``md.Trajectory``. Each
            sequence may have a different length, but they all must have the
            same number of features, or the same number of atoms if they are
            ``md.Trajectory``s.

        Returns
        -------
        self
        """
        MultiSequenceClusterMixin.fit(self, sequences)
        return self
