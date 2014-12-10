"""Sparse approximate generalized eigenvalue problem
"""
from __future__ import print_function
import time
import numpy as np
import scipy.linalg
try:
    import cvxpy as cp
except:
    raise ImportError(
        "Could not import cvxpy, a required package for this module. "
        "See https://github.com/cvxgrp/cvxpy for details")

__all__ = ['scdeflate', 'speigh']


def scdeflate(A, x):
    """Schur complement matrix deflation

    Eliminate the influence of a psuedo-eigenvector of A using the Schur complement
    deflation technique from [1]::

        A_new = A - \frac{A x x^T A}{x^T A x}

    Parameters
    ----------
    A : np.ndarray, shape=(N, N)
        A matrix
    x : np.ndarray, shape=(N, )
        A vector, ideally one that is "close to" an eigenvector of A

    Returns
    -------
    A_new : np.ndarray, shape=(N, N)
        A new matrix, determined from A by eliminating the influence of x

    References
    .. [1] Mackey, Lester. "Deflation Methods for Sparse PCA." NIPS. Vol. 21. 2008.
    """
    return A - np.outer(np.dot(A, x), np.dot(x, A)) / np.dot(np.dot(x, A), x)


def speigh(A, B, v_init, rho, eps, tol, tau=None, maxiter=10000, greedy=True,
           verbose=True):
    """Find a sparse approximate generalized eigenpair.

    The generalized eigenvalue equation, :math:`Av = lambda Bv`,
    can be expressed as a variational optimization ::
    :math:`max_{x} x^T A x  s.t. x^T B x = 1`. We can search for sparse
    approximate eigenvectors then by adding a penalty to the optimization.
    This function solves an approximation to::

    max_{x}   x^T A x - \rho ||x||_0

        s.t.      x^T B x <= 1

    Where `||x||_0` is the number of nonzero elements in `x`. Note that
    because of the ||x||_0 term, that problem is NP-hard. Here, we replace
    the ||x||_0 term with

    rho * \sum_i^N \frac{\log(1 + |x_i|/eps)}{1 + 1/eps}

    which converges to ||x||_0 in the limit that eps goes to zero. This
    formulation can then be written as a d.c. (difference of convex) program
    and solved efficiently. The algorithm is due to [1], and is written
    on page 15 of the paper.

    Parameters
    ----------
    A : np.ndarray, shape=(N, N)
        A is symmetric matrix, the left-hand-side of the eigenvalue equation.
    B : np.ndarray, shape=(N, N)
        B is a positive semidefinite matrix, the right-hand-side of the
        eigenvalue equation.
    v_init : np.ndarray, shape=(N,)
        Initial guess for the eigenvector. This should probably be computed by
        running the standard generalized eigensolver first.
    rho : float
        Regularization strength. Larger values for rho will lead to more sparse
        solutions.
    eps : float
        Small number, used in the approximation to the L0. Smaller is better
        (closer to L0), but trickier from a numerical standpoint and can lead
        to the solver complaining when it gets too small.
    tol : float
        Convergence criteria for the eigensolver.

    Returns
    -------
    u : float
        The approximate eigenvalue.
    v_final : np.ndarray, shape=(N,)
        The sparse approximate eigenvector

    Notes
    -----
    This function requires the convex optimization library CVXPY [2].

    References
    ----------
    ..[1] Sriperumbudur, Bharath K., David A. Torres, and Gert RG Lanckriet.
    "A majorization-minimization approach to the sparse generalized eigenvalue
    problem." Machine learning 85.1-2 (2011): 3-39.
    ..[2] https://github.com/cvxgrp/cvxpy
    """


    pprint = print
    if not verbose:
        pprint = lambda *args : None
    length = A.shape[0]
    x = v_init

    old_x = np.empty(length)
    rho_e = rho / np.log(1 + 1.0/eps)
    b = np.diag(B)
    B_is_diagonal = np.all(np.diag(b) == B)

    if tau == 0:
        if B_is_diagonal:
            pprint('Path [1]: tau=0, diagonal B')
            old_x.fill(np.inf)
            for i in range(maxiter):
                norm = np.linalg.norm(x[np.abs(old_x) > tol] - old_x[np.abs(old_x) > tol])
                if norm < tol:
                    break
                pprint('x', x)
                old_x = x
                w = 1.0 / (np.abs(x) + eps)
                Ax = A.dot(x)
                absAx = np.abs(Ax)

                if rho_e < 2 * np.max(absAx.dot(w**(-1))):
                    # line 9 of Algorithim 1
                    gamma = absAx - (rho_e/2) * w
                    x_num = np.maximum(gamma, 0) * np.sign(Ax)
                    x_den = b * np.sqrt(np.sum(gamma**2 / b))
                    x = x_num / x_den
                else:
                    x = np.zeros(length)
        else:
            pprint('Path [2]: tau=0, general B')
            old_x.fill(np.inf)
            for i in range(maxiter):
                norm = np.linalg.norm(x[np.abs(old_x) > tol] - old_x[np.abs(old_x) > tol])
                if norm < tol:
                    break
                pprint('x: ', x)
                old_x = x
                w = 1.0 / (np.abs(x) + eps)
                Ax = A.dot(x)
                absAx = np.abs(Ax)

                if rho_e < 2 * np.max(absAx.dot(w**(-1))):
                    gamma = absAx - (rho_e / 2.0 * w)
                    S = np.diag(np.sign(Ax))
                    SBSInv = scipy.linalg.pinv(S.dot(B).dot(S))

                    # solve for lambda, line 20 of Algorithm 1
                    lambd = problem1(SBSinv, gamma)

                    temp = SBSInv.dot(gamma + lambd)
                    x_num = S.dot(temp)
                    x_den = np.sqrt((gamma + lambd).dot(temp))
                    x = x_num / x_den
                else:
                    x = np.zeros(length)

    else:
        pprint('Path [3]: tau != 0')
        old_x.fill(np.inf)
        scaledA = (A / tau + np.eye(length))
        problem2 = Problem2(B, rho_e / tau, sparse=greedy)
        for i in range(maxiter):
            norm = np.linalg.norm(x[np.abs(old_x) > tol] - old_x[np.abs(old_x) > tol])
            if norm < tol:
                break
            old_x = x
            y = scaledA.dot(x)
            w = 1.0 / (np.abs(x) + eps)
            start = time.time()

            x = problem2(y, w, x_mask=(np.abs(x)>tol))
            pprint('norm', norm, time.time()-start, '\nx', np.where(np.abs(x)>tol)[0])

    pprint('\nxf:', x)
    # return x.dot(A).dot(x), x

    # Proposition 1 and the "variational renormalization" described in [1].
    # Use the sparsity pattern in 'x', but ignore the loadings and rerun an
    # unconstrained GEV problem on the submatrices determined by the nonzero
    # entries in our optimized x

    # What cutoff to use for zeroing out entries in 'x'. We could hard-code
    # something, but reusing the `tolerance` parameter seems fine too.
    sparsecutoff = tol

    mask = (np.abs(x) > sparsecutoff)
    grid = np.ix_(mask, mask)
    Ak, Bk = A[grid], B[grid]  # form the submatrices

    if len(Ak) == 0:
        return 0, np.zeros(length)
    if len(Ak) == 1:
        v = np.zeros(length)
        v[mask] = 1.0
        return Ak[0,0] / Bk[0,0], v

    gevals, gevecs = scipy.sparse.linalg.eigsh(
        A=Ak, M=Bk, k=1, v0=x[mask], which='LA')

    u = gevals[-1]
    v = np.zeros(length)
    v[mask] = gevecs[:, -1]
    return u, v


def problem1(A, gamma):
    """Solve the problem from line 20 of Algorithm 1

    x = argmin_x (x + gamma)^T A (x + \gamma)
    s.t. x >= 0
    """
    assert A.ndim == 2 and gamma.ndim == 1 and A.shape[0] == gamma.shape[0] \
        and A.shape[1] == gamma.shape[0]

    x = cp.Variable(len(gamma))
    objective = cp.Minimize(cp.quad_form(gamma + x, A))
    constraints = [x >= 0]
    problem = cp.Problem(objective, constraints)

    result = problem.solve(solver=cp.SCS)
    if problem.status not in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
        raise ValueError(problem.status)
    return np.asarray(x.value).flatten()


class Problem2(object):
    """Solve the problem from line 31 of Algorithm 1

    x = argmin_x ||x-y||_2^2 + c||diag(w)*x||_1
    s.t. x^T B x <= 1
    """

    def __init__(self, B, c, sparse=True):
        assert B.ndim == 2 and np.isscalar(c)
        self.c = c
        self.B = B
        self.n = B.shape[0]
        self.sparse = sparse

    def __call__(self, y, w, x_mask=None):
        if x_mask is None or (not self.sparse):
            return self.solve(y, w)
        else:
            return self.solve_sparse(y, w, x_mask)
    
    def solve(self, y, w):
        assert y.ndim == 1 and w.ndim == 1 and y.shape == w.shape
        assert w.shape[0] == self.n

        x = cp.Variable(self.n)
        term1 = cp.square(cp.norm((x - y)))
        term2 = self.c * cp.norm1(cp.diag(w) * x)

        objective = cp.Minimize(term1 + term2)
        constraints = [cp.quad_form(x, self.B) <= 1]
        problem = cp.Problem(objective, constraints)

        result = problem.solve(solver=cp.SCS)
        if problem.status not in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
            raise ValueError(problem.status)
        return np.asarray(x.value).flatten()


    def solve_sparse(self, y, w, x_mask=None):
        assert y.ndim == 1 and w.ndim == 1 and y.shape == w.shape
        assert w.shape[0] == self.n
        
        x = cp.Variable(np.count_nonzero(x_mask))
        inv_mask = np.logical_not(x_mask)
        
        term1 = cp.square(cp.norm(x-y[x_mask]))# + cp.square(cp.norm(y[inv_mask]))
        term2 = self.c * cp.norm1(cp.diag(w[x_mask]) * x)

        objective = cp.Minimize(term1 + term2)
        constraints = [cp.quad_form(x, self.B[np.ix_(x_mask, x_mask)]) <= 1]
        problem = cp.Problem(objective, constraints)

        result = problem.solve(solver=cp.SCS)
        if problem.status not in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
            raise ValueError(problem.status)

        out = np.zeros(self.n)
        out[x_mask] = np.asarray(x.value).flatten()
        return out
