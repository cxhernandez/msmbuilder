import numpy as np
from mdtraj import compute_dihedrals, compute_phi
from mdtraj.testing import eq
from scipy.stats import vonmises as vm
from mdtraj.testing import eq
import pandas as pd
import itertools

from msmbuilder.example_datasets import AlanineDipeptide, MetEnkephalin,\
    MinimalFsPeptide
from msmbuilder.featurizer import get_atompair_indices, FunctionFeaturizer, \
    DihedralFeaturizer, AtomPairsFeaturizer, SuperposeFeaturizer, \
    RMSDFeaturizer, VonMisesFeaturizer, Slicer, CommonContactFeaturizer, \
    KappaAngleFeaturizer, AngleFeaturizer, SolventShellsFeaturizer


def test_function_featurizer():
    trajectories = AlanineDipeptide().get_cached().trajectories
    trj0 = trajectories[0]

    # use the dihedral to compute phi for ala
    atom_ind = [[4, 6, 8, 14]]
    func = compute_dihedrals
    # test with args
    f = FunctionFeaturizer(func, func_args={"indices": atom_ind})
    res1 = f.transform([trj0])

    # test with function in a function without any args
    def funcception(trj):
        return compute_phi(trj)[1]

    f = FunctionFeaturizer(funcception)
    res2 = f.transform([trj0])

    # know results
    f3 = DihedralFeaturizer(['phi'], sincos=False)
    res3 = f3.transform([trj0])

    # compare all
    for r in [res2, res3]:
        np.testing.assert_array_almost_equal(res1, r)


def test_that_all_featurizers_run():
    # TODO: include all featurizers, perhaps with generator tests

    trajectories = AlanineDipeptide().get_cached().trajectories
    trj0 = trajectories[0][0]
    atom_indices, pair_indices = get_atompair_indices(trj0)

    featurizer = AtomPairsFeaturizer(pair_indices)
    X_all = featurizer.transform(trajectories)

    featurizer = SuperposeFeaturizer(np.arange(15), trj0)
    X_all = featurizer.transform(trajectories)

    featurizer = DihedralFeaturizer(["phi", "psi"])
    X_all = featurizer.transform(trajectories)

    featurizer = VonMisesFeaturizer(["phi", "psi"])
    X_all = featurizer.transform(trajectories)

    # Below doesn't work on ALA dipeptide
    # featurizer = msmbuilder.featurizer.ContactFeaturizer()
    # X_all = featurizer.transform(trajectories)

    featurizer = RMSDFeaturizer(trj0)
    X_all = featurizer.transform(trajectories)


def test_common_contacts_featurizer_1():
    trajectories = MetEnkephalin().get_cached().trajectories
    top = trajectories[0].topology
    met_seq = top.to_fasta(0)
    # fake sequence has an insertion
    fake_met_eq = 'YGGFMF'
    alignment = {}
    # do "alignment "
    alignment["actual"] = met_seq + "-"
    alignment["fake"] = fake_met_eq
    max_len = max([len(alignment[i]) for i in alignment.keys()])
    contacts = [i for i in itertools.combinations(np.arange(max_len), 2)]
    feat = CommonContactFeaturizer(alignment=alignment, contacts=contacts,
                                   same_residue=True)
    rnd_traj = np.random.randint(len(trajectories))
    df = pd.DataFrame(feat.describe_features(trajectories[rnd_traj]))
    features = feat.transform([trajectories[rnd_traj]])


def test_common_contacts_featurizer_2():
    trajectories = MetEnkephalin().get_cached().trajectories
    top = trajectories[0].topology
    met_seq = top.to_fasta(0)

    # fake sequence
    fake_met_eq = 'FGGFM'
    alignment = {}
    # do "alignment "
    alignment["actual"] = met_seq
    alignment["fake"] = fake_met_eq
    max_len = max([len(alignment[i]) for i in alignment.keys()])
    contacts = [i for i in itertools.combinations(np.arange(max_len), 2)]
    feat = CommonContactFeaturizer(alignment=alignment, contacts=contacts,
                                   same_residue=True)

    rnd_traj = np.random.randint(len(trajectories))
    df = pd.DataFrame(feat.describe_features(trajectories[rnd_traj]))
    assert(np.all([j != 0 for i in df.resids for j in i]))


def test_common_contacts_featurizer_3():
    # test randomly mutates one of the residues to make sure that residues contacts are not
    # included
    trajectories = MetEnkephalin().get_cached().trajectories
    top = trajectories[0].topology
    met_seq = top.to_fasta(0)
    # randomly "mutate one of the residues to alanine
    rnd_loc = np.random.randint(len(met_seq))
    fake_met_eq = met_seq[:rnd_loc] + "A" + met_seq[rnd_loc + 1:]
    alignment = {}
    # do "alignment "
    alignment["actual"] = met_seq
    alignment["fake"] = fake_met_eq
    max_len = max([len(alignment[i]) for i in alignment.keys()])
    contacts = [i for i in itertools.combinations(np.arange(max_len), 2)]
    feat = CommonContactFeaturizer(alignment=alignment, contacts=contacts,
                                   same_residue=True)

    rnd_traj = np.random.randint(len(trajectories))
    df = pd.DataFrame(feat.describe_features(trajectories[rnd_traj]))
    assert(np.all([j != rnd_loc for i in df.resids for j in i]))


def test_von_mises_featurizer():
    trajectories = AlanineDipeptide().get_cached().trajectories

    featurizer = VonMisesFeaturizer(["phi"], n_bins=18)
    X_all = featurizer.transform(trajectories)
    n_frames = trajectories[0].n_frames
    assert X_all[0].shape == (n_frames, 18), (
        "unexpected shape returned: (%s, %s)" %
        X_all[0].shape)

    featurizer = VonMisesFeaturizer(["phi", "psi"], n_bins=18)
    X_all = featurizer.transform(trajectories)
    n_frames = trajectories[0].n_frames
    assert X_all[0].shape == (n_frames, 36), (
        "unexpected shape returned: (%s, %s)" %
        X_all[0].shape)

    featurizer = VonMisesFeaturizer(["phi", "psi"], n_bins=10)
    X_all = featurizer.transform(trajectories)
    assert X_all[0].shape == (n_frames, 20), (
        "unexpected shape returned: (%s, %s)" %
        X_all[0].shape)


def test_von_mises_featurizer_2():
    trajectories = MinimalFsPeptide().get_cached().trajectories
    # test to make sure results are being put in the right order
    feat = VonMisesFeaturizer(["phi", "psi"], n_bins=10)
    _, all_phi = compute_phi(trajectories[0])
    X_all = feat.transform(trajectories)
    all_res = []
    for frame in all_phi:
        for dihedral_value in frame:
            all_res.extend(vm.pdf(dihedral_value,
                                  loc=feat.loc, kappa=feat.kappa))

    print(len(all_res))

    # this checks 10 random dihedrals to make sure that they appear in the right columns
    # for the vonmises bins
    n_phi = all_phi.shape[1]
    for k in range(5):
        # pick a random phi dihedral
        rndint = np.random.choice(range(n_phi))
        # figure out where we expect it to be in X_all
        indices_to_expect = []
        for i in range(10):
            indices_to_expect += [n_phi * i + rndint]

        # we know the results in all_res are dihedral1(bin1-bin10) dihedral2(bin1 to bin10)
        # we are checking if X is alldihedrals(bin1) then all dihedrals(bin2)

        expected_res = all_res[rndint * 10:10 + rndint * 10]

        assert (np.array(
            [X_all[0][0, i] for i in indices_to_expect]) == expected_res).all()


def test_slicer():
    X = ([np.random.normal(size=(50, 5), loc=np.arange(5))] +
         [np.random.normal(size=(10, 5), loc=np.arange(5))])

    slicer = Slicer(index=[0, 1])

    Y = slicer.transform(X)
    eq(len(Y), len(X))
    eq(Y[0].shape, (50, 2))

    slicer = Slicer(first=2)

    Y2 = slicer.transform(X)
    eq(len(Y2), len(X))
    eq(Y2[0].shape, (50, 2))

    eq(Y[0], Y2[0])
    eq(Y[1], Y2[1])

def test_kappa_angle_featurizer_1():
    trajectories = MetEnkephalin().get_cached().trajectories
    top = trajectories[0].topology
    feat = KappaAngleFeaturizer(offset=1)
    df = pd.DataFrame(feat.describe_features(trajectories[0]))
    assert sorted(df.resids[0]) == [0,1,2]
    cas = [i.index for i in top.atoms if i.name=='CA']
    assert sorted(df.atominds[0]) == cas[:3]

def test_kappa_angle_featurizer_2():
    trajectories = MetEnkephalin().get_cached().trajectories
    top = trajectories[0].topology
    feat = KappaAngleFeaturizer(offset=2)
    df = pd.DataFrame(feat.describe_features(trajectories[0]))
    assert not sorted(df.resids[0]) == [0,1,2]
    assert sorted(df.resids[0]) == [0,2,4]

def test_angle_featurizer():
    trajectories = MetEnkephalin().get_cached().trajectories
    top = trajectories[0].topology
    feat = KappaAngleFeaturizer(offset=2)
    feat_1 = feat.transform([trajectories[0]])
    df = pd.DataFrame(feat.describe_features(trajectories[0]))
    atom_inds = np.vstack(df.atominds)
    feat = AngleFeaturizer(angle_indices=atom_inds)
    feat_2 = feat.transform([trajectories[0]])
    assert np.all(feat_1[0] == feat_2[0])


def make_traj_from_1d(*particles):
    """Take numpy arrays and turn it into trajectories in x / particle

    """

    # Make dummy trajectory with enough atoms
    top = md.Topology()
    chain = top.add_chain()
    resi = top.add_residue(None, chain)
    for _ in particles:
        top.add_atom(None, None, resi)

    # Make xyz
    for_concat = []
    for p in particles:
        p = np.asarray(p)
        p3 = np.hstack((p[:, np.newaxis], np.zeros((len(p), 2))))
        p3 = p3[:, np.newaxis, :]
        for_concat += [p3]
    xyz = np.concatenate(for_concat, axis=1)
    traj = md.Trajectory(xyz, top)
    return traj


class TestMakeTraj(unittest.TestCase):
    def setUp(self):
        traj = make_traj_from_1d(
            [0, 0, 0, 0, 0, 5, 5, 5, 5],
            [-1, -2, -3, -4, -5, -6, -7, -8, -9],
            [1, 2, 3, 4, 5, 6, 7, 8, 9]
        )
        self.traj = traj

    def test_make_traj(self):
        self.assertEqual(self.traj.n_frames, 9)
        self.assertEqual(self.traj.n_atoms, 3)


class TestShells(unittest.TestCase):
    def setUp(self):
        traj = make_traj_from_1d(
            [0, 0, 0, 0, 0, 5, 5, 5, 5],
            [-1, -2, -3, -4, -5, -6, -7, -8, -9],
            [1, 2, 3, 4, 5, 6, 7, 8, 9]
        )
        self.tmpdir = tempfile.mkdtemp()
        self.traj_fn = pjoin(self.tmpdir, 'traj.h5')
        traj.save(self.traj_fn)

        shell_computation = wetmsm.SolventShellsFeaturizer(
            n_shells=3, shell_width=1, solute_indices=np.array([0]),
            solvent_indices=np.array([1, 2])
        )
        self.shell_comp = shell_computation

    def test_featurization(self):
        counts = self.shell_comp.partial_transform(md.load(self.traj_fn))

        norm = np.asarray([4 * np.pi * r ** 2 for r in [0.5, 1.5, 2.5]])
        should_be = np.array([
            [2, 0, 0],
            [0, 2, 0],
            [0, 0, 2],
            [0, 0, 0],
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
            [0, 0, 0]
        ]) / norm

        np.testing.assert_array_equal(counts, should_be)


class TestMSMBuilder(unittest.TestCase):
    def setUp(self):
        traj = make_traj_from_1d(
            [0, 0, 0, 0, 0, 5, 5, 5, 5],
            [-1, -2, -3, -4, -5, -6, -7, -8, -9],
            [1, 2, 3, 4, 5, 6, 7, 8, 9]
        )
        self.tmpdir = tempfile.mkdtemp()
        self.traj_fn = pjoin(self.tmpdir, 'traj.h5')
        self.outfn = pjoin(self.tmpdir, 'feat')
        traj.save(self.traj_fn)

        self.ute_fn = pjoin(self.tmpdir, 'ute')
        self.vent_fn = pjoin(self.tmpdir, 'vent')
        np.savetxt(self.ute_fn, np.array([0]), fmt="%d")
        np.savetxt(self.vent_fn, np.array([1, 2]), fmt="%d")

    def test_partial_transform(self):
        with open(os.devnull) as dn:
            subprocess.call(
                [
                    'msmb', 'SolventShellsFeaturizer', '--trjs', self.traj_fn,
                    '--solute_indices', self.ute_fn, '--solvent_indices',
                    self.vent_fn, '--n_shells', '3', '--shell_width', '1',
                    '--out', self.outfn
                ], stdout=dn, stderr=dn
            )
        data = dataset(self.outfn)[0]

        norm = np.asarray([4 * np.pi * r ** 2 for r in [0.5, 1.5, 2.5]])
        should_be = np.array([
            [2, 0, 0],
            [0, 2, 0],
            [0, 0, 2],
            [0, 0, 0],
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
            [0, 0, 0]
        ]) / norm

        np.testing.assert_array_equal(data, should_be)

    def test_assign(self):
        with open(os.devnull) as dn:
            subprocess.call(
                [
                    'msmb', 'SolventShellsAssigner', '--trjs', self.traj_fn,
                    '--solute_indices', self.ute_fn, '--solvent_indices',
                    self.vent_fn, '--n_shells', '3', '--shell_width', '1',
                    '--out', self.outfn, '--chunk', '2'
                ], stdout=dn, stderr=dn
            )

        data = dataset(self.outfn)[0]

        should_be = np.array([
            [0, 0, 0, 0],
            [0, 1, 0, 0],
            [1, 0, 0, 1],
            [1, 1, 0, 1],
            [2, 0, 0, 2],
            [2, 1, 0, 2],
            # 3
            # 4
            [5, 1, 0, 0],
            [6, 1, 0, 1],
            [7, 1, 0, 2],
            # 8
        ])

        np.testing.assert_array_equal(data, should_be)
