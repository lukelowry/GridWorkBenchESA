"""
Static Analysis Example
=======================

Advanced static analysis tools built on top of the esapp PowerWorld.
Provides continuation power flow, state chain management, ZIP load
injection, generator limit checking, and random load variation.

Example
-------
    >>> from esapp import PowerWorld
    >>> from statics import Statics  # with examples/ on sys.path
    >>> pw = PowerWorld("case.pwb")
    >>> s = Statics(pw)
    >>> interface = np.array([1, -1, 0, ...])
    >>> for mw in s.continuation_pf(interface, maxiter=100):
    ...     print(f"Converged at {mw:.2f} MW")
"""

import warnings
from typing import Optional, Iterator

import numpy as np
from numpy import exp, any
from pandas import DataFrame

from esapp.components import Gen, Load, Bus

warnings.simplefilter(action="ignore", category=FutureWarning)

__all__ = ['Statics']


class Statics:
    """
    Advanced static analysis application using a PowerWorld instance.

    Parameters
    ----------
    pw : PowerWorld
        An initialized PowerWorld instance.
    """

    def __init__(self, pw) -> None:
        self.pw = pw
        self._gen_limits_cached = False
        self._dispatch_initialized = False

    # ------------------------------------------------------------------
    # Lazy initialization helpers
    # ------------------------------------------------------------------

    def _ensure_gen_limits(self) -> None:
        """Cache generator limits from PowerWorld on first access."""
        if self._gen_limits_cached:
            return
        gens = self.pw[Gen, ['GenMVRMin', 'GenMVRMax', 'GenMWMax', 'GenMWMin']]
        self.genqmax = gens['GenMVRMax']
        self.genqmin = gens['GenMVRMin']
        self.genpmax = gens['GenMWMax']
        self.genpmin = gens['GenMWMin']
        self._gen_limits_cached = True

    _ZIP_FIELDS = ['LoadSMW', 'LoadSMVR', 'LoadIMW', 'LoadIMVR',
                    'LoadZMW', 'LoadZMVR']

    def _ensure_dispatch(self) -> None:
        """Create dispatch loads (LoadID='99') at every bus if not yet done."""
        if self._dispatch_initialized:
            return

        buses = self.pw[Bus, ['BusNum', 'BusName_NomVolt']]

        dispatch = DataFrame({
            'BusNum':          buses['BusNum'].values,
            'BusName_NomVolt': buses['BusName_NomVolt'].values,
            'LoadID':          '99',
            'LoadStatus':      'Closed',
            **{zf: 0.0 for zf in self._ZIP_FIELDS},
        })

        self.pw.esa.EnterMode('EDIT')
        try:
            self.pw[Load] = dispatch
        finally:
            self.pw.esa.EnterMode('RUN')

        self.DispatchPQ = dispatch[['BusNum', 'LoadID'] + self._ZIP_FIELDS].copy()
        self._dispatch_initialized = True

    # ------------------------------------------------------------------
    # Generator limit checking
    # ------------------------------------------------------------------

    def gens_above_pmax(
        self,
        p: Optional[np.ndarray] = None,
        is_closed: Optional[np.ndarray] = None,
        tol: float = 0.001,
    ) -> bool:
        """Check if any closed generators exceed P limits."""
        self._ensure_gen_limits()
        if p is None:
            p = self.pw[Gen, 'GenMW']['GenMW']
        is_high = p > self.genpmax + tol
        is_low = p < self.genpmin - tol
        if is_closed is None:
            is_closed = self.pw[Gen, 'GenStatus']['GenStatus'] == 'Closed'
        violation = is_closed & (is_high | is_low)
        return any(violation)

    def gens_above_qmax(
        self,
        q: Optional[np.ndarray] = None,
        is_closed: Optional[np.ndarray] = None,
        tol: float = 0.001,
    ) -> bool:
        """Check if any closed generators exceed Q limits."""
        self._ensure_gen_limits()
        if q is None:
            q = self.pw[Gen, 'GenMVR']['GenMVR']
        is_high = q > self.genqmax + tol
        is_low = q < self.genqmin - tol
        if is_closed is None:
            is_closed = self.pw[Gen, 'GenStatus']['GenStatus'] == 'Closed'
        violation = is_closed & (is_high | is_low)
        return any(violation)

    # ------------------------------------------------------------------
    # Continuation power flow (predictor-corrector)
    # ------------------------------------------------------------------

    @staticmethod
    def _build_cpf_dFdlam(
        interface: np.ndarray,
        bus_to_idx: dict,
        jac_ids: list,
        sbase: float,
        n_jac: int = 0,
    ) -> np.ndarray:
        """Map a bus-indexed interface vector into Jacobian row ordering."""
        dF = np.zeros(n_jac if n_jac > 0 else len(jac_ids))
        for row, raw_label in enumerate(jac_ids):
            parts = raw_label.strip().strip("'\"").split()
            if len(parts) < 2:
                continue
            if not parts[0].lower().startswith('dp'):
                continue
            try:
                bus = int(parts[1])
            except ValueError:
                continue
            idx = bus_to_idx.get(bus)
            if idx is not None:
                dF[row] = -interface[idx] / sbase
        return dF

    def _cpf_halve_step(self, step: float, min_step: float) -> float:
        """Return ``step / 2``, or ``-1`` if below *min_step*."""
        step *= 0.5
        return step if step >= min_step else -1.0

    def continuation_pf(
        self,
        interface: np.ndarray,
        initialmw: float = 0,
        step_size: float = 0.05,
        min_step: float = 0.001,
        max_step: float = 0.1,
        maxiter: int = 200,
        verbose: bool = False,
        restore_when_done: bool = False,
        qlim_tol: Optional[float] = 0,
        plim_tol: Optional[float] = None,
        sbase: float = 100.0,
    ) -> Iterator[float]:
        """Predictor-corrector continuation power flow.

        Yields
        ------
        float
            Interface transfer level (MW) after each converged solution.
        """
        self._ensure_gen_limits()
        self._ensure_dispatch()

        log = (lambda msg, **kw: print(msg, **kw)) if verbose else (lambda *a, **k: None)

        if restore_when_done:
            self.pw.esa.StoreState('CPF_BACKUP')

        lam_current = initialmw
        self.setload(SP=-lam_current * interface)
        self.pw.pflow(getvolts=False)
        self.pw.esa.StoreState('CPF_PREV')
        yield lam_current

        J0, jac_ids = self.pw.jacobian(dense=True, form='P', ids=True)
        n_jac = J0.shape[0]

        bus_nums = self.pw[Bus, 'BusNum']['BusNum'].to_numpy()
        bus_to_idx = {int(b): i for i, b in enumerate(bus_nums)}

        dF_dlam = self._build_cpf_dFdlam(interface, bus_to_idx, jac_ids, sbase, n_jac)

        step = step_size
        cont_param = n_jac
        tangent_prev = np.zeros(n_jac + 1)
        tangent_prev[-1] = 1.0
        crossed_nose = False

        for it in range(maxiter):
            J, _ = self.pw.jacobian(dense=True, form='P', ids=True)

            J_aug = np.zeros((n_jac + 1, n_jac + 1))
            J_aug[:n_jac, :n_jac] = J
            J_aug[:n_jac, n_jac]  = dF_dlam
            J_aug[n_jac, cont_param] = 1.0

            rhs = np.zeros(n_jac + 1)
            rhs[n_jac] = 1.0

            try:
                tangent = np.linalg.solve(J_aug, rhs)
            except np.linalg.LinAlgError:
                log(f'  [{it}] Singular augmented Jacobian')
                step = self._cpf_halve_step(step, min_step)
                if step < 0:
                    break
                continue

            tnorm = np.linalg.norm(tangent)
            if tnorm < 1e-15:
                break
            tangent /= tnorm
            if np.dot(tangent, tangent_prev) < 0:
                tangent = -tangent

            lam_pred = lam_current + step * tangent[-1]
            log(f'  [{it}] Predict: lam={lam_pred:.2f} MW  '
                f'(step={step:.4f}, dlam={step * tangent[-1]:.2f})',
                end='')

            self.setload(SP=-lam_pred * interface)
            try:
                self.pw.pflow(getvolts=False)
            except Exception:
                log(' FAIL', end='')
                step = self._cpf_halve_step(step, min_step)
                if step < 0:
                    log(f'\n  Step below minimum ({min_step})')
                    break
                self.pw.esa.RestoreState('CPF_PREV')
                log(f' -> retry (step={step:.4f})')
                continue

            reject = False
            if qlim_tol is not None:
                gen_df = self.pw[Gen, ['GenMVR', 'GenStatus']]
                closed = gen_df['GenStatus'] == 'Closed'
                if self.gens_above_qmax(gen_df['GenMVR'], closed, tol=qlim_tol):
                    log(' Q-LIM', end='')
                    reject = True

            if not reject and plim_tol is not None:
                if self.gens_above_pmax(tol=plim_tol):
                    log(' P-LIM', end='')
                    reject = True

            if reject:
                step = self._cpf_halve_step(step, min_step)
                if step < 0:
                    break
                self.pw.esa.RestoreState('CPF_PREV')
                continue

            if tangent_prev[-1] > 0 and tangent[-1] < 0:
                crossed_nose = True
                log(' NOSE', end='')

            if abs(tangent[-1]) < 0.1:
                n_half = n_jac // 2
                v_sens = np.abs(tangent[n_half:n_jac])
                if len(v_sens) > 0:
                    best = int(np.argmax(v_sens)) + n_half
                    if cont_param != best:
                        cont_param = best
                        log(f' SWITCH(V[{best - n_half}])', end='')
            else:
                cont_param = n_jac

            cos_angle = np.clip(np.dot(tangent, tangent_prev), -1.0, 1.0)
            angle = np.arccos(cos_angle)
            if angle < 0.05:
                step = min(step * 1.5, max_step)
            elif angle > 0.3:
                step = max(step * 0.5, min_step)

            self.pw.esa.StoreState('CPF_PREV')
            tangent_prev = tangent.copy()
            lam_current = lam_pred

            log(f'  OK (lam={lam_current:.2f})')
            yield lam_current

            if crossed_nose and lam_current < initialmw:
                log(f'  Lambda returned below initial ({initialmw})')
                break

        self.clearloads()
        if restore_when_done:
            self.pw.esa.RestoreState('CPF_BACKUP')

    # ------------------------------------------------------------------
    # State chain management
    # ------------------------------------------------------------------

    def chain(self, maxstates: int = 2) -> None:
        """Initialize state chain for iterative algorithms."""
        self.maxstates = maxstates
        self.stateidx = -1

    def pushstate(self, verbose: bool = False) -> None:
        """Push current state onto the state chain."""
        self.stateidx += 1
        self.pw.esa.StoreState(f'GWBState{self.stateidx}')
        if verbose:
            print(f'Pushed States -> {self.stateidx}')
        if self.stateidx >= self.maxstates:
            self.pw.esa.DeleteState(f'GWBState{self.stateidx - self.maxstates}')

    def irestore(self, n: int = 1, verbose: bool = False) -> None:
        """Restore the nth previous state from the chain."""
        if n > self.maxstates or n > self.stateidx:
            if verbose:
                print('Restoration Failure')
            raise Exception("State index out of range")
        if verbose:
            print(f'Restore -> {self.stateidx - n}')
        self.pw.esa.RestoreState(f'GWBState{self.stateidx - n}')

    # ------------------------------------------------------------------
    # ZIP load interface
    # ------------------------------------------------------------------

    def setload(
        self,
        SP: Optional[np.ndarray] = None,
        SQ: Optional[np.ndarray] = None,
        IP: Optional[np.ndarray] = None,
        IQ: Optional[np.ndarray] = None,
        ZP: Optional[np.ndarray] = None,
        ZQ: Optional[np.ndarray] = None,
    ) -> None:
        """Set ZIP load components on the dispatch loads (LoadID='99')."""
        self._ensure_dispatch()

        _col_map = {
            'LoadSMW': SP,  'LoadSMVR': SQ,
            'LoadIMW': IP,  'LoadIMVR': IQ,
            'LoadZMW': ZP,  'LoadZMVR': ZQ,
        }

        changed_cols = []
        for col, arr in _col_map.items():
            if arr is not None:
                self.DispatchPQ[col] = arr
                changed_cols.append(col)

        if not changed_cols:
            return

        write_cols = ['BusNum', 'LoadID'] + changed_cols
        self.pw[Load] = self.DispatchPQ[write_cols]

    def clearloads(self) -> None:
        """Zero all six ZIP components on the dispatch loads."""
        self._ensure_dispatch()
        self.DispatchPQ[self._ZIP_FIELDS] = 0.0
        self.pw[Load] = self.DispatchPQ

    # ------------------------------------------------------------------
    # Random load variation
    # ------------------------------------------------------------------

    load_nom = None
    load_df = None

    def randomize_load(self, scale: float = 1.0, sigma: float = 0.1) -> None:
        """Apply random variation to system loads."""
        if self.load_nom is None or self.load_df is None:
            self.load_df = self.pw[Load, 'LoadMW']
            self.load_nom = self.load_df['LoadMW']
        random_factors = exp(sigma * np.random.random(len(self.load_nom)))
        self.pw[Load, 'LoadMW'] = scale * self.load_nom * random_factors

    randload = randomize_load
