import numpy as np
import pandas as pd
import scipy.sparse as sp

BASE_YEAR = 2003
EDGES = np.array([0, 0.5, 1, 2, 5, 10, 25.01])


def qlabels(T):
    return [f"{BASE_YEAR + i // 4}Q{i % 4 + 1}" for i in range(T)]


def _qidx(d):
    return ((d.dt.year - BASE_YEAR) * 4 + (d.dt.quarter - 1)).to_numpy()


def _mad_sd(x):
    return 1.4826 * np.median(np.abs(x - np.median(x)))


def _fit(p, T, w=None):
    n = len(p)
    rows = np.r_[np.arange(n), np.arange(n)]
    cols = np.r_[p['q0'].to_numpy(), p['q1'].to_numpy()]
    vals = np.r_[-np.ones(n), np.ones(n)]
    D = sp.csr_matrix((vals, (rows, cols)), shape=(n, T))[:, 1:]      # first quarter fixed at 0
    y = p['log_ratio'].to_numpy()
    W = sp.diags(np.ones(n) if w is None else w)
    A = (D.T @ W @ D).toarray()
    b = D.T @ (W @ y)
    beta = np.r_[0.0, np.linalg.lstsq(A, b, rcond=None)[0]]
    return beta, y - D @ beta[1:]


def repeat_sales_index(pairs, T=92, min_touch=30, base='2004Q1', trim=3.0):
    """Bailey-Muth-Nourse index with per-holding-period weights and robust trimming."""
    p = pairs.copy()
    p['q0'], p['q1'] = _qidx(p['date0']), _qidx(p['date1'])
    p = p[p['q1'] > p['q0']].reset_index(drop=True)
    code = np.digitize(p['days'] / 365.25, EDGES) - 1
    _, r = _fit(p, T)
    for _ in range(2):
        sd = np.array([_mad_sd(r[code == k]) if (code == k).sum() >= 200 else _mad_sd(r)
                       for k in range(len(EDGES) - 1)])
        _, r = _fit(p, T, 1 / sd[code] ** 2)
    keep = np.abs(r) / sd[code] <= trim
    q, cq = p[keep].reset_index(drop=True), code[keep]
    b, _ = _fit(q, T, 1 / sd[cq] ** 2)
    touch = np.bincount(np.r_[q['q0'], q['q1']], minlength=T)
    out = pd.Series(100 * np.exp(b), index=qlabels(T))
    out[touch < min_touch] = np.nan
    return out / out[base] * 100