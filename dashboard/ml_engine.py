"""
ml_engine.py – WaveForm ML Inference Engine
Classifiers: Stress Level · Depression Score · Emotion State
"""

import os
import warnings
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────
_HERE = os.path.abspath(os.path.dirname(__file__))
MODEL_DIR = os.path.join(_HERE, "..", "models")

# ── Label / colour maps ────────────────────────────────────────
STRESS_LABELS     = ["Low",     "Moderate", "High"]
DEPRESSION_LABELS = ["Minimal", "Mild",     "Moderate", "Severe"]
EMOTION_LABELS    = ["Calm",    "Happy",    "Anxious",  "Sad",    "Focused", "Fatigued"]

STRESS_COLORS     = ["#10b981", "#f59e0b", "#ef4444"]
DEPRESSION_COLORS = ["#10b981", "#a3e635", "#f59e0b", "#ef4444"]
EMOTION_COLORS    = ["#10b981", "#facc15", "#f97316", "#818cf8", "#06b6d4", "#a855f7"]


# ── Feature extraction ─────────────────────────────────────────
def extract_features(bands: dict) -> np.ndarray:
    d = float(bands.get("delta", 1e-6))
    t = float(bands.get("theta", 1e-6))
    a = float(bands.get("alpha", 1e-6))
    b = float(bands.get("beta",  1e-6))
    g = float(bands.get("gamma", 1e-6))
    total = d + t + a + b + g + 1e-9
    return np.array([
        d, t, a, b, g,
        t / (a + 1e-9),   # theta/alpha  – drowsiness
        b / (a + 1e-9),   # beta/alpha   – stress/alertness
        a / total,         # alpha ratio  – relaxation
        d / (b + 1e-9),   # delta/beta   – sleep pressure
        (b - a) / total,  # asymmetry    – depression marker
    ], dtype=float)


# ── Synthetic training data ────────────────────────────────────
def _make_dataset():
    """
    9 profiles × 300 samples.
    Emotion labels: 0=Calm 1=Happy 2=Anxious 3=Sad 4=Focused 5=Fatigued
    All six emotion classes are represented → contiguous 0-5.
    """
    rng = np.random.default_rng(42)

    def noisy(mu, n=300):
        return np.abs(rng.normal(mu, mu * 0.22, n))

    # (delta, theta, alpha, beta, gamma, stress, depression, emotion)
    profiles = [
        (60, 25, 55, 15,  8,  0, 0, 0),  # Calm
        (50, 30, 45, 25, 10,  0, 0, 1),  # Happy
        (35, 40, 20, 70, 20,  2, 1, 2),  # Anxious
        (65, 48, 18, 20,  6,  1, 2, 3),  # Sad
        (45, 35, 30, 45, 15,  1, 0, 4),  # Focused
        (70, 45, 22, 22,  7,  1, 2, 5),  # Fatigued
        (30, 38, 18, 80, 22,  2, 1, 2),  # High stress
        (62, 42, 15, 25,  8,  1, 2, 3),  # Mild dep
        (70, 50, 10, 30,  5,  2, 3, 3),  # Severe dep
    ]

    X, ys, yd, ye = [], [], [], []
    for (dm, tm, am, bm, gm, sl, dl, el) in profiles:
        n = 300
        rows = [
            {"delta": noisy(dm, 1)[0], "theta": noisy(tm, 1)[0],
             "alpha": noisy(am, 1)[0], "beta":  noisy(bm, 1)[0],
             "gamma": noisy(gm, 1)[0]}
            for _ in range(n)
        ]
        for row in rows:
            X.append(extract_features(row))
            ys.append(sl); yd.append(dl); ye.append(el)

    return np.array(X), np.array(ys), np.array(yd), np.array(ye)


# ── Engine ─────────────────────────────────────────────────────
class MLEngine:
    _VERSION = "v2"   # bump to force model rebuild

    def __init__(self):
        os.makedirs(MODEL_DIR, exist_ok=True)
        self._sm = self._dm = self._em = None
        self._trained = False
        self._load_or_train()

    # ── load / train ───────────────────────────────────────────

    def _paths(self):
        return (
            os.path.join(MODEL_DIR, f"stress_{self._VERSION}.joblib"),
            os.path.join(MODEL_DIR, f"depression_{self._VERSION}.joblib"),
            os.path.join(MODEL_DIR, f"emotion_{self._VERSION}.joblib"),
        )

    def _load_or_train(self):
        sp, dp, ep = self._paths()
        try:
            if os.path.exists(sp) and os.path.exists(dp) and os.path.exists(ep):
                sm = joblib.load(sp)
                dm = joblib.load(dp)
                em = joblib.load(ep)
                # validate – all 6 emotion classes must exist
                assert set(em.classes_) == set(range(6)), "stale model"
                self._sm, self._dm, self._em = sm, dm, em
                self._trained = True
                return
        except Exception:
            pass
        self._train(sp, dp, ep)

    def _train(self, sp, dp, ep):
        X, ys, yd, ye = _make_dataset()

        def pipe(clf):
            return Pipeline([("sc", StandardScaler()), ("clf", clf)]).fit

        self._sm = pipe(RandomForestClassifier(n_estimators=120, random_state=0, n_jobs=-1))(X, ys)
        self._dm = pipe(GradientBoostingClassifier(n_estimators=100, random_state=0))(X, yd)
        self._em = pipe(RandomForestClassifier(n_estimators=120, random_state=1, n_jobs=-1))(X, ye)

        # verify before saving
        assert set(self._em.classes_) == set(range(6))

        joblib.dump(self._sm, sp)
        joblib.dump(self._dm, dp)
        joblib.dump(self._em, ep)
        self._trained = True

    # ── predict ────────────────────────────────────────────────

    def predict(self, bands: dict) -> dict:
        if not self._trained:
            return self._fallback(bands)
        try:
            feat = extract_features(bands).reshape(1, -1)

            si = int(self._sm.predict(feat)[0])
            di = int(self._dm.predict(feat)[0])
            ei = int(self._em.predict(feat)[0])

            sp = self._sm.predict_proba(feat)[0]
            dp = self._dm.predict_proba(feat)[0]
            ep = self._em.predict_proba(feat)[0]

            # classes_ → positional index in the proba array
            sc = list(self._sm.classes_)
            dc = list(self._dm.classes_)
            ec = list(self._em.classes_)

            si_safe = si if 0 <= si < len(STRESS_LABELS)     else 0
            di_safe = di if 0 <= di < len(DEPRESSION_LABELS) else 0
            ei_safe = ei if 0 <= ei < len(EMOTION_LABELS)    else 0

            s_pi = sc.index(si) if si in sc else 0
            d_pi = dc.index(di) if di in dc else 0
            e_pi = ec.index(ei) if ei in ec else 0

            return {
                "stress_level":          si_safe,
                "stress_label":          STRESS_LABELS[si_safe],
                "stress_color":          STRESS_COLORS[si_safe],
                "stress_confidence":     float(sp[s_pi]),
                "stress_proba":          sp.tolist(),

                "depression_level":      di_safe,
                "depression_label":      DEPRESSION_LABELS[di_safe],
                "depression_color":      DEPRESSION_COLORS[di_safe],
                "depression_confidence": float(dp[d_pi]),
                "depression_proba":      dp.tolist(),

                "emotion_idx":           ei_safe,
                "emotion_label":         EMOTION_LABELS[ei_safe],
                "emotion_color":         EMOTION_COLORS[ei_safe],
                "emotion_confidence":    float(ep[e_pi]),
                "emotion_proba":         ep.tolist(),
            }
        except Exception:
            return self._fallback(bands)

    # ── rule-based fallback ────────────────────────────────────

    def _fallback(self, bands: dict) -> dict:
        b = float(bands.get("beta",  1))
        a = float(bands.get("alpha", 1))
        r = b / (a + 1e-6)
        si = 0 if r < 1.2 else (1 if r < 2.5 else 2)
        di = 0 if a > 40 else (1 if a > 25 else (2 if a > 15 else 3))
        ei = 0
        return {
            "stress_level":          si,
            "stress_label":          STRESS_LABELS[si],
            "stress_color":          STRESS_COLORS[si],
            "stress_confidence":     0.65,
            "stress_proba":          [0.0] * 3,
            "depression_level":      di,
            "depression_label":      DEPRESSION_LABELS[di],
            "depression_color":      DEPRESSION_COLORS[di],
            "depression_confidence": 0.60,
            "depression_proba":      [0.0] * 4,
            "emotion_idx":           ei,
            "emotion_label":         EMOTION_LABELS[ei],
            "emotion_color":         EMOTION_COLORS[ei],
            "emotion_confidence":    0.60,
            "emotion_proba":         [0.0] * 6,
        }
