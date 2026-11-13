"""Which of the 6 screen cells (3 columns x 2 rows) is the user looking at?

Webcam gaze is too noisy to find an exact pixel, but it is good enough to tell
big cells apart. This module learns that from the calibration samples, picks
the best of several small models by testing on visits it did NOT train on, and
gives per-frame probabilities that the tracker averages over a few frames."""
import numpy as np

WINDOW = 8          # frames averaged when judging accuracy (same as runtime voting)
N_CELLS = 6


# ----------------------------------------------------------------- features
def _eyes3(F):
    F = np.atleast_2d(np.asarray(F, float))
    return np.column_stack([(F[:, 0] + F[:, 1]) / 2.0,
                            (F[:, 2] + F[:, 3]) / 2.0,
                            (F[:, 4] + F[:, 5]) / 2.0])


def _eyes3_head(F):
    F = np.atleast_2d(np.asarray(F, float))
    return np.column_stack([_eyes3(F), F[:, 6], F[:, 7]])


def _eyes6(F):
    return np.atleast_2d(np.asarray(F, float))[:, :6]


FEATURE_SETS = {"eyes3": _eyes3, "eyes3+head": _eyes3_head, "eyes6": _eyes6}


# ------------------------------------------------------------------- models
class _LDA:
    """Linear discriminant analysis with shrinkage (smooth, hard to overfit)."""

    def __init__(self, shrink=0.15):
        self.shrink = shrink

    def fit(self, X, y):
        self.mu, self.sd = X.mean(0), X.std(0) + 1e-9
        Z = (X - self.mu) / self.sd
        d = Z.shape[1]
        means = np.zeros((N_CELLS, d))
        resid = np.zeros_like(Z)
        for c in range(N_CELLS):
            idx = y == c
            means[c] = Z[idx].mean(0) if idx.any() else 0.0
            resid[idx] = Z[idx] - means[c]
        cov = resid.T @ resid / max(len(Z) - N_CELLS, 1)
        cov = (1 - self.shrink) * cov + self.shrink * np.trace(cov) / d * np.eye(d)
        P = np.linalg.inv(cov)
        self.W = means @ P
        self.b = -0.5 * np.sum(means @ P * means, axis=1)

    def proba(self, X):
        Z = (X - self.mu) / self.sd
        S = Z @ self.W.T + self.b
        S -= S.max(1, keepdims=True)
        E = np.exp(S)
        return E / E.sum(1, keepdims=True)


class _KNN:
    """k-nearest-neighbours vote (follows any shape, needs more data)."""

    def __init__(self, k=11):
        self.k = k

    def fit(self, X, y):
        self.mu, self.sd = X.mean(0), X.std(0) + 1e-9
        self.Z = (X - self.mu) / self.sd
        self.y = y

    def proba(self, X):
        Z = (X - self.mu) / self.sd
        out = np.full((len(Z), N_CELLS), 1e-3)
        for i, z in enumerate(Z):
            d = np.sum((self.Z - z) ** 2, axis=1)
            nn = self.y[np.argsort(d)[:self.k]]
            for c in nn:
                out[i, c] += 1.0
        return out / out.sum(1, keepdims=True)


MODELS = {"lda": lambda: _LDA(0.15), "knn": lambda: _KNN(11)}


# --------------------------------------------------------------- evaluation
def _rolling_mean(P, k):
    k = max(1, min(k, len(P)))
    return np.array([P[i - k + 1:i + 1].mean(0) for i in range(k - 1, len(P))])


def evaluate(F, labels, visits, feat_name, model_name):
    """Leave-one-visit-out accuracy: train on the other visits, test on this one.
    Returns (accuracy after 8-frame voting, plain per-frame accuracy)."""
    X = FEATURE_SETS[feat_name](F)
    win, frame = [], []
    for v in np.unique(visits):
        tr, te = visits != v, visits == v
        m = MODELS[model_name]()
        m.fit(X[tr], labels[tr])
        P = m.proba(X[te])
        frame.append(float((P.argmax(1) == labels[te]).mean()))
        R = _rolling_mean(P, WINDOW)
        win.append(float((R.argmax(1) == labels[te][WINDOW - 1:][:len(R)]).mean()))
    return float(np.mean(win)), float(np.mean(frame))


class CellClassifier:
    def __init__(self):
        self.feat = None
        self.model = None
        self.feat_name = ""
        self.model_name = ""
        self.accuracy = 0.0
        self.frame_accuracy = 0.0
        self.table = []

    def fit(self, F, labels, visits):
        F, labels, visits = np.asarray(F, float), np.asarray(labels, int), np.asarray(visits, int)
        if len(set(labels.tolist())) < N_CELLS:
            raise ValueError("not all cells were calibrated")
        best = None
        self.table = []
        for fn in FEATURE_SETS:                # order = simplest first (wins ties)
            for mn in MODELS:
                try:
                    acc, facc = evaluate(F, labels, visits, fn, mn)
                except Exception:
                    continue
                self.table.append((fn, mn, acc, facc))
                if best is None or acc > best[2] + 1e-9:
                    best = (fn, mn, acc, facc)
        if best is None:
            raise ValueError("no model could be fitted")
        self.feat_name, self.model_name, self.accuracy, self.frame_accuracy = best
        self.feat = FEATURE_SETS[self.feat_name]
        self.model = MODELS[self.model_name]()
        self.model.fit(self.feat(F), labels)

    def proba(self, f):
        return self.model.proba(self.feat(np.atleast_2d(f)))[0]