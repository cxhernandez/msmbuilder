"""Subcommands of the `mixtape` script using the NumpydocClass command wrapper
"""
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


from __future__ import print_function, absolute_import

from ..dataset import dataset
from ..utils import verbosedump
from ..hmm import GaussianFusionHMM
from ..msm import MarkovStateModel, BayesianMarkovStateModel
from ..cmdline import NumpydocClassCommand, argument


class FitCommand(NumpydocClassCommand):
    inp = argument(
        '--inp', help='''Input dataset. This should be serialized
        list of numpy arrays.''', required=True)
    model = argument(
        '--out', help='''Output (fit) model. This will be a
        serialized instance of the fit model object.''', required=True)

    def start(self):
        print(self.instance)

        ds = dataset(self.inp, mode='r', fmt='dir-npy')
        self.instance.fit(ds)
        verbosedump(self.instance, self.out)

        print("*********\n*RESULTS*\n*********")
        print(self.instance.summarize())
        print('All done')


class GaussianFusionHMMCommand(FitCommand):
    klass = GaussianFusionHMM
    _concrete = True
    _group = 'MSM'


class MarkovStateModelCommand(FitCommand):
    klass = MarkovStateModel
    _concrete = True
    _group = 'MSM'


class BayesianMarkovStateModelCommand(FitCommand):
    klass = BayesianMarkovStateModel
    _concrete = True
    _group = 'MSM'

