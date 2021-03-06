# -*- coding: utf-8 -*-
"""
Created on 10 Oct 2019
author: Dylan Jones

project: qsim
version: 1.0
"""
import numpy as np
import scipy.linalg as la
from itertools import product
from .utils import ZERO, ONE, Basis, kron, expectation, get_projector
from .utils import EIGVALS, EV_X, EV_Y, EV_Z
from .register import Qubit, QuRegister
from .gates import GATE_DICT


# =========================================================================
#                             STATEVECTOR
# =========================================================================


class StateVector:

    name = "statevector"
    GATE_DICT = GATE_DICT

    def __init__(self, qubits, basis=None, amp=None):
        self.n_qubits = 0
        self.n = 0
        self.qubits = None
        self.basis = None
        self.amp = None
        self.snapshots = list()
        self.set_qubits(qubits, basis, amp)

    def set_qubits(self, qubits, basis=None, amp=None):
        """ Initialize the statevector for the given qubits.

        Parameters
        ----------
        qubits: array_like of Qubit
            The Qubits of the system.
        basis: Basis, optional
            Basis object of the Qubits containing the state descriptions.
            If not specified the Basis will be initialized.
        amp: array_like, optional
            Coefficients of the initial state. The default is the .math:'|0>' state.
        """
        if isinstance(qubits, QuRegister):
            qubits = qubits.bits
        self.qubits = qubits
        self.n_qubits = len(qubits)
        self.basis = basis or Basis(len(qubits))
        self.n = 2 ** self.n_qubits
        self.set(amp)

    def set(self, amp=None):
        """ Set the current state-vector

        Parameters
        ----------
        amp: array_like, optional
            Coefficients of the state. The default is the .math:'|0>' state.
        """
        state = kron([ZERO] * self.n_qubits) if amp is None else np.copy(amp)
        if len(state) != self.n:
            raise ValueError(f"Dimensions dont't match: {len(state)} != {self.n}")
        if np.round(la.norm(state), decimals=10) != 1.0:
            raise ValueError(f"State not normalized: |s|={np.round(la.norm(state), decimals=15)}")
        self.amp = state / la.norm(state)

    def prepare(self, *states):
        """ Prepare the current state using single qubit states.

        Parameters
        ----------
        states: array_like of (2) array_like
            Single qubit state-vectors.
        """
        amp = kron(*states)
        self.set(amp)

    @property
    def norm(self):
        """ float: The norm of the state vector"""
        return la.norm(self.amp)

    @property
    def last(self):
        """ np.ndarray: The last saved snapshot of the state vector """
        return self.snapshots[-1]

    @property
    def dtype(self):
        """ np.dtype: The data type of the state vector """
        return self.amp.dtype

    def __getitem__(self, item):
        return self.amp[item]

    def __setitem__(self, item, value):
        self.amp[item] = value

    def __str__(self):
        amps = self.amplitudes(decimals=10)
        strings = [f"{self.basis.labels[i]} {amps[i]}" for i in range(self.n)]
        n_max = max([len(x) for x in strings])
        n = max(int((n_max - 6) // 2), 1) + 1
        head = "-" * n + "Vector" + "-" * n
        strings.insert(0, head)
        return "\n".join(strings) + "\n"

    def save_state(self, file):
        """ Save the current state vector to a file.

        Parameters
        ----------
        file: file-like or str
            File or filename to which the data is saved. If file is a string or Path,
            a .npy extension will be appended to the file name if it does not already have one.
        """
        np.save(file, self.amp)

    def load_state(self, file):
        """ Load a state vector from a file.

        Parameters
        ----------
        file: file-like or str
            File or filename from which the data is loaded.
        """
        self.amp = np.load(file)

    def save_snapshot(self):
        """ Save the current state vector as snapshot. """
        s = StateVector(self.qubits, self.basis, self.amp)
        self.snapshots.append(s)

    def add_custom_gate(self, name, item):
        """ Add custom Gate to the gate-dictionary """
        self.GATE_DICT.update({name: item})

    def density_matrix(self):
        """ Constructs the density matrix from the current state vector

        Returns
        -------
        rho: (N, N) np.array_like
        """
        return np.dot(self.amp[:, np.newaxis], self.amp[np.newaxis, :])

    def amplitudes(self, decimals=10):
        """ Computes the amplitudes from the state coefficients.

        Parameters
        ----------
        decimals: int, optional
            Decimals for rounding amplitudes.

        Returns
        -------
        amps: (N) np.ndarray
        """
        return np.round(self.amp, decimals)

    def probabilities(self, decimals=10):
        """ Computes the state probabilities from the state coefficients.

        Parameters
        ----------
        decimals: int, optional
            Decimals for rounding probabilities.

        Returns
        -------
        probs: (N) np.ndarray
        """
        return np.abs(self.amplitudes(decimals))**2

    def histogram(self):
        """ Computes the histogram of the state vector.

        Returns
        -------
        bins: (N) np.ndarray
            The bins of the histogram.
        hist: (N) np.ndarray
            The number of values in the corresponding bins of the histogram.
        """
        return np.arange(self.n), np.abs(self.amp)

    def project(self, idx, op):
        """ Get the projection of the state vector on a given single-qubit operator

        Parameters
        ----------
        idx: int
            Index of single qubit operator.
        op: array_like
            Single qubit operator.

        Returns
        -------
        proj: (N, N) np.ndarray
        """
        parts = [np.eye(2)] * self.n_qubits
        parts[idx] = op
        return np.dot(kron(parts), self.amp)

    def expectation(self, op, qubit=None):
        r""" Calculates the expectation value of a given operator.

        .. math::
            x = <\Psi| \hat{O} |\Psi>

        Parameters
        ----------
        op: np.ndarray
            The exectation of this operator is caluclated
        qubit: Qubit, optional
            Qubit if the operator is a single-qubit operator.

        Returns
        -------
        x: float
        """
        if qubit is not None and op.shape == (2, 2):
            parts = [np.eye(2)] * self.n_qubits
            parts[qubit.index] = op
            op = kron(parts)
        return expectation(op, self.amp)

    def apply_unitary(self, u):
        r""" Apply unitary operator to teh statevector.

        The new state after applying the unitary operator is given by
        .. math::
            |\Psi'> = \hat{U} |\Psi>

        Parameters
        ----------
        u: (N, N) array_like
            Unitary operator to apply to statevector.
        """
        self.amp = np.dot(u, self.amp)

    def apply_gate(self, gate):
        r""" Apply Gate (unitary operator) to the statevector

        See Also
        --------
        StateVector.apply_unitary

        Parameters
        ----------
        gate: np.ndarray or Gate
            Unitary operator or Gate-object to apply to statevector.
        """
        if not isinstance(gate, np.ndarray):
            gate = gate.build_matrix(self.n_qubits)
        self.apply_unitary(gate)

    def measure_qubit(self, qubit, eigvals=None, eigvecs=None, shadow=False):
        r""" Measure the state of a single qubit in a given eigenbasis.

        The probability .math:'p_i' of measuring each eigenstate of the measurement-eigenbasis
        is calculated using the projection .math:'P_i' of the corresponding eigenvector .math:'v_i'

        .. math::
            p_i = <\Psi| P_i | \Psi > \quad P_i = |v_i > < v_i|

        The calculated probabilities are used to determine the corresponding eigenvalue .math:'\lambda_i'
        which is the final measurement result. The state after the measurement is defined as:

        .. math::
            | \Psi_{\text{new}} > = \frac{P_i | \Psi >}{\norm{P_i | \Psi >}}

        Parameters
        ----------
        qubit: Qubit
            The qubit that is measured
        eigvals: ndarray, optional
            The eigenvalues of the basis in which is measured.
            The default is the computational basis with eigenvalues '0' and '1'.
        eigvecs: np.ndarray, optional
            The corresponding eigenvectors of the basis in which is measured.
            The default is the computational basis with eigenvectors '(1, 0)' and '(0, 1)'.
        shadow: bool, optional
            Flag if state should remain in the pre-measurement state.
            The default is 'False'.

        Returns
        -------
        result: float
            Eigenvalue corresponding to the measured eigenstate.
        """
        idx = qubit.index
        # get eigenbasis of measurment operator.
        # If not specified the computational basis is used
        if eigvals is None:
            v0, v1 = ZERO, ONE
            eigvals = [0, 1]
        else:
            if eigvecs is None:
                raise ValueError("No Eigenvectors of the measurement-basis are specified "
                                 "(Don't pass any eigenvalues to use comp. basis)")
            v0, v1 = eigvecs.T
        # Calculate probability of getting first eigenstate as result
        projector_0 = get_projector(v0)
        projected = self.project(idx, projector_0)
        p0 = np.dot(np.conj(self.amp).T, projected)
        if abs(p0.imag) > 1e-15:
            raise ValueError(f"Complex probability: {p0}")
        # Simulate measurement probability
        index = int(np.random.random() > p0.real)
        if index == 1:
            # Project state to other eigenstate of the measurement basis
            projector_1 = get_projector(v1)
            projected = self.project(idx, projector_1)
        # Project measurement result on the state
        if not shadow:
            self.amp = projected / la.norm(projected)
        # return corresponding eigenvalue of the measured eigenstate
        return eigvals[index].real

    def measure(self, qubits, eigvals=None, eigvecs=None, shadow=False, snapshot=True):
        r""" Measure the state of multiple qubits in a given eigenbasis.

        The probability .math:'p_i' of measuring each eigenstate of the measurement-eigenbasis
        is calculated using the projection .math:'P_i' of the corresponding eigenvector .math:'v_i'

        .. math::
            p_i = <\Psi| P_i | \Psi > \quad P_i = |v_i > < v_i|

        The calculated probabilities are used to determine the corresponding eigenvalue .math:'\lambda_i'
        which is the final measurement result. The state after the measurement is defined as:

        .. math::
            | \Psi_{\text{new}} > = \frac{P_i | \Psi >}{\norm{P_i | \Psi >}}

        Parameters
        ----------
        qubits: array_like of Qubit or Qubit
            The qubits that are measured.
        eigvals: ndarray, optional
            The eigenvalues of the basis in which is measured.
            The default is the computational basis with eigenvalues '0' and '1'.
        eigvecs: np.ndarray, optional
            The corresponding eigenvectors of the basis in which is measured.
            The default is the computational basis with eigenvectors '(1, 0)' and '(0, 1)'.
        shadow: bool, optional
            Flag if state should remain in the pre-measurement state.
            The default is 'False'.
        snapshot: bool, optional
            Flag if snapshot of statevector should be saved before measurment.
            The default is 'True'.

        Returns
        -------
        result: np.ndarray
            Eigenvalue corresponding to the measured eigenstate.
        """
        if not hasattr(qubits, "__len__"):
            qubits = [qubits]

        # get eigenbasis of measurment operator.
        # If not specified the computational basis is used
        if eigvals is None:
            eigvecs = np.asarray([ZERO, ONE])
            eigvals = [0, 1]
        else:
            if eigvecs is None:
                raise ValueError("No Eigenvectors of the measurement-basis are specified "
                                 "(Don't pass any eigenvalues to use comp. basis)")
            eigvecs = eigvecs.T

        # Calculate probabilities of all posiible results
        results = list(product([0, 1], repeat=len(qubits)))  # Result indices
        num_res = len(results)
        probs = np.zeros(num_res)
        projections = np.zeros((num_res, self.n), dtype="complex")
        eye = np.eye(2)
        for i, res in enumerate(results):
            # Build projector
            parts = [eye] * self.n_qubits
            for r, q in zip(res, qubits):
                parts[q.index] = get_projector(eigvecs[r])
            projector = kron(parts)

            # Get projected state and calculate probability
            projected = np.dot(projector, self.amp)
            p = np.dot(np.conj(self.amp).T, projected)
            projections[i] = projected
            if abs(p.imag) > 1e-15:
                raise ValueError(f"Complex probability: {p}")
            probs[i] = p.real

        # Simulate measurement probability and get corresponding eigenvalues
        index = np.random.choice(range(len(results)), p=probs)
        result = [eigvals[i] for i in results[index]]

        # Project measurement result on the state
        if not shadow:
            # Save snapshot of state before projecting to post-measurement state
            if snapshot:
                self.save_snapshot()
            projected = projections[index]
            self.amp = projected / la.norm(projected)
        return result

    def measure_x(self, qubits, shadow=False, snapshot=True):
        """ Performs a measurement of a single qubit in the x-basis.

        When a qubit is in the .math:'|+\rangle' (.math:'|-\rangle') state a measurement
        in the .math:'x'-basis will result in .math:'1' (.math:'-1').

        Parameters
        ----------
        qubits: array_like of Qubit or Qubit
            The qubits that are measured.
        shadow: bool, optional
            Flag if state should remain in the pre-measurement state.
            The default is 'False'.
        snapshot: bool, optional
            Flag if snapshot of statevector should be saved before measurment.
            The default is 'True'.

        Returns
        -------
        result: np.ndarray
            Eigenvalue corresponding to the measured eigenstate.
        """
        return self.measure(qubits, EIGVALS, EV_X, shadow, snapshot)

    def measure_y(self, qubits, shadow=False, snapshot=True):
        """ Performs a measurement of a single qubit in the y-basis.

        When a qubit is in the .math:'|i\rangle' (.math:'|-i\rangle') state a measurement
        in the .math:'y'-basis will result in .math:'1' (.math:'-1').

        Parameters
        ----------
        qubits: array_like of Qubit or Qubit
            The qubits that are measured.
        shadow: bool, optional
            Flag if state should remain in the pre-measurement state.
            The default is 'False'.
        snapshot: bool, optional
            Flag if snapshot of statevector should be saved before measurment.
            The default is 'True'.

        Returns
        -------
        result: np.ndarray
            Eigenvalue corresponding to the measured eigenstate.
        """
        return self.measure(qubits, EIGVALS, EV_Y, shadow, snapshot)

    def measure_z(self, qubits, shadow=False, snapshot=True):
        """ Performs a measurement of a single qubit in the z-basis.

        When a qubit is in the .math:'|0\rangle' (.math:'|1\rangle') state a measurement
        in the .math:'z'-basis will result in .math:'1' (.math:'-1').

        Parameters
        ----------
        qubits: array_like of Qubit or Qubit
            The qubits that are measured.
        shadow: bool, optional
            Flag if state should remain in the pre-measurement state.
            The default is 'False'.
        snapshot: bool, optional
            Flag if snapshot of statevector should be saved before measurment.
            The default is 'True'.

        Returns
        -------
        result: np.ndarray
            Eigenvalue corresponding to the measured eigenstate.
        """
        return self.measure(qubits, EIGVALS, EV_Z, shadow, snapshot)
