"""Gaze -> screen mapping: regression calibration + One-Euro smoothing.
Pure numpy (no cv2/mediapipe), so it is easy to test."""
import math
import time
import numpy as np


class OneEuroFilter:
    """Adaptive low-pass: heavy smoothing when still (steady dwell),
    light smoothing when moving fast (little lag)."""

    def __init__(self, min_cutoff=0.5, beta=0.003, d_cutoff=1.0):
        self.min_cutoff, self.beta, self.d_cutoff = min_cutoff, beta, d_cutoff
        self.reset()

    def reset(self):
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None

    @staticmethod
    def _alpha(cutoff, dt):
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, x, t=None):
        t = time.perf_counter() if t is None else t
        if self.x_prev is None:
            self.x_prev, self.t_prev = x, t
            return x
        dt = max(t - self.t_prev, 1e-3)
        dx = (x - self.x_prev) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        dx_hat = a_d * dx + (1 - a_d) * self.dx_prev
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._alpha(cutoff, dt)
        x_hat = a * x + (1 - a) * self.x_prev
        self.x_prev, self.dx_prev, self.t_prev = x_hat, dx_hat, t
        return x_hat


class GazeMapper:
    """Simple, robust mapping: average both eyes into 3 numbers (horizontal,
    vertical, eyelid-relative vertical) and fit a ridge-regularised quadratic to
    screen pixels. Inputs are clipped to the calibrated range, so the cursor can
    never run away. (Per-eye + head terms were tried and made it noisier.)"""

    def __init__(self, ridge=5e-2):
        self.ridge = ridge
        self.W = self.mu = self.sd = self.lo = self.hi = None

    @staticmethod
    def _eyes(F):
        F = np.atleast_2d(np.asarray(F, float))
        return np.column_stack([(F[:, 0] + F[:, 1]) / 2.0,
                                (F[:, 2] + F[:, 3]) / 2.0,
                                (F[:, 4] + F[:, 5]) / 2.0])

    @staticmethod
    def _design(Z):
        Z = np.atleast_2d(Z)
        gx, gy, g2 = Z[:, 0], Z[:, 1], Z[:, 2]
        return np.column_stack([np.ones(len(Z)), gx, gy, g2,
                                gx * gx, gy * gy, gx * gy, gx * g2])

    def fit(self, F, S):
        G, S = self._eyes(F), np.asarray(S, float)
        self.mu, self.sd = G.mean(0), G.std(0) + 1e-9
        Z = (G - self.mu) / self.sd
        self.lo, self.hi = Z.min(0) - 0.25, Z.max(0) + 0.25
        X = self._design(Z)
        reg = self.ridge * np.eye(X.shape[1])
        reg[0, 0] = 0
        self.W = np.linalg.solve(X.T @ X + reg * len(X), X.T @ S)

    def predict(self, f):
        Z = np.clip((self._eyes(f)[0] - self.mu) / self.sd, self.lo, self.hi)
        return (self._design(Z) @ self.W)[0]

    def cross_validate(self, F, S, groups):
        """Leave-one-calibration-point-out error in pixels (pessimistic: the
        left-out dot is often at an edge, so the model must extrapolate)."""
        F, S, groups = np.asarray(F), np.asarray(S), np.asarray(groups)
        errs = []
        for g in np.unique(groups):
            tr, te = groups != g, groups == g
            m = GazeMapper(self.ridge)
            m.fit(F[tr], S[tr])
            pred = np.array([m.predict(f) for f in F[te]])
            errs.append(np.median(np.hypot(*(pred - S[te]).T)))
        return float(np.mean(errs))