# -*- coding: utf-8 -*-
"""
Created on 10 Oct 2019
author: Dylan Jones

project: qDmft
version: 1.0
"""
import re
import numpy as np
from scitools import Plot
from .register import Qubit, Clbit
from .utils import Basis, get_info, to_list, histogram
from .visuals import CircuitString
from .instruction import Gate, Measurement, Instruction, ParameterMap
from .backends import StateVector


class CircuitResult:

    def __init__(self, data, basis_labels):
        self.labels = basis_labels
        self.data = None
        self.hist = None

        self.load(data)

    def load(self, data, normalize=True):
        self.data = data
        self.hist = histogram(data, normalize)

    @property
    def shape(self):
        return self.data.shape

    @property
    def n(self):
        return self.shape[0]

    def mean(self):
        return self.sorted()[0]

    def sorted(self):
        bins, probs = self.hist
        indices = np.argsort(probs)[::-1]
        return [(bins[i], probs[i]) for i in indices]

    def highest(self, thresh=0.7):
        res_sorted = self.sorted()
        pmax = res_sorted[0][1]
        return [(self.labels[i], p) for i, p in res_sorted if p >= thresh * pmax]

    def show_histogram(self, show=True):
        bins, hist = self.hist
        plot = Plot(xlim=(-0.5, len(bins) - 0.5), ylim=(0, 1))
        plot.set_title(f"N={self.n}")
        plot.grid(axis="y")
        plot.set_ticks(bins, np.arange(0, 1.1, 0.2))
        plot.set_ticklabels(self.labels)
        plot.ax.bar(bins, hist, width=0.9)
        if show:
            plot.show()

    def __str__(self):
        entries = [f"   {label} {p:.3f}" for label, p in self.highest()]
        string = f"Result ({self.n} shots):\n"
        string += "\n".join(entries)
        return string


def init_bits(arg, bit_type):
    qubits = None
    if isinstance(arg, int):
        qubits = [bit_type(i) for i in range(arg)]
    elif isinstance(arg, bit_type):
        qubits = [arg]
    elif isinstance(arg, list):
        qubits = arg
    return qubits


class Circuit:

    def __init__(self, qubits, clbits=None, backend=StateVector.name):
        self.qubits = init_bits(qubits, Qubit)
        if clbits is None:
            clbits = len(self.qubits)
        self.clbits = init_bits(clbits, Clbit)
        self.basis = Basis(self.n_qubits)
        self.instructions = list()
        self.pmap = ParameterMap.instance()
        self.res = None

        if backend == StateVector.name:
            self.backend = StateVector(self.qubits, self.basis)
        else:
            raise ValueError("Invalid backend: " + backend)

    @classmethod
    def like(cls, other):
        return cls(other.qubits, other.clbits, other.backend.name)

    @property
    def n_qubits(self):
        return len(self.qubits)

    @property
    def n_clbits(self):
        return len(self.clbits)

    @property
    def n_params(self):
        return len(self.pmap.params)

    @property
    def params(self):
        return self.pmap.params

    @property
    def args(self):
        return self.pmap.args

    def init(self):
        self.backend.init()

    def init_params(self, *args):
        self.pmap.init(*args)

    def set_params(self, args):
        self.pmap.set_params(args)

    # =========================================================================

    def __repr__(self):
        return f"Circuit(qubits: {self.qubits}, clbits: {self.clbits})"

    def __str__(self):
        string = self.__repr__()
        for inst in self.instructions:
            string += "\n   " + str(inst)
        return string

    def print(self, padding=1, maxwidth=None):
        s = CircuitString(len(self.qubits), padding)
        for instructions in self.instructions:
            s.add(instructions)
        print(s.build(wmax=maxwidth))

    def show(self):
        pass

    def to_string(self, delim="; "):
        info = [f"qubits={self.n_qubits}", f"clbits={self.n_clbits}"]
        string = "".join([x + delim for x in info])
        lines = [string]
        for inst in self.instructions:
            string = inst.to_string()
            lines.append(string)
        return "\n".join(lines)

    # =========================================================================

    def add_instruction(self, inst):
        self.instructions.append(inst)
        return inst

    def _get_qubits(self, bits):
        if bits is None:
            return None
        bitlist = list()
        for q in to_list(bits):
            if not isinstance(q, Qubit):
                q = self.qubits[q]
            bitlist.append(q)
        return bitlist

    def _get_clbits(self, bits):
        if bits is None:
            return None
        bitlist = list()
        for c in to_list(bits):
            if not isinstance(c, Clbit):
                c = self.clbits[c]
            bitlist.append(c)
        return bitlist

    def add_gate(self, name, qubits, con=None, arg=None, argidx=None):
        qubits = self._get_qubits(qubits)
        con = self._get_qubits(con)
        gates = Gate(name, qubits, con=con, arg=arg, argidx=argidx)
        return self.add_instruction(gates)

    def add_measurement(self, qubits, clbits):
        qubits = self._get_qubits(qubits)
        clbits = self._get_clbits(clbits)
        m = Measurement("m", qubits, clbits)
        return self.add_instruction(m)

    def i(self, qubit):
        return self.add_gate("I", qubit)

    def x(self, qubit):
        return self.add_gate("X", qubit)

    def y(self, qubit):
        return self.add_gate("Y", qubit)

    def z(self, qubit):
        return self.add_gate("Z", qubit)

    def h(self, qubit):
        return self.add_gate("H", qubit)

    def s(self, qubit):
        return self.add_gate("S", qubit)

    def t(self, qubit):
        return self.add_gate("T", qubit)

    def rx(self, qubit, arg=0, argidx=None):
        return self.add_gate("Rx", qubit, arg=arg, argidx=argidx)

    def ry(self, qubit, arg=0, argidx=None):
        return self.add_gate("Ry", qubit, arg=arg, argidx=argidx)

    def rz(self, qubit, arg=0, argidx=None):
        return self.add_gate("Rz", qubit, arg=arg, argidx=argidx)

    def cx(self, con, qubit):
        return self.add_gate("X", qubit, con)

    def cy(self, con, qubit):
        return self.add_gate("Y", qubit, con)

    def cz(self, con, qubit):
        return self.add_gate("Z", qubit, con)

    def ch(self, con, qubit):
        return self.add_gate("H", qubit, con)

    def cs(self, con, qubit):
        return self.add_gate("S", qubit, con)

    def ct(self, con, qubit):
        return self.add_gate("T", qubit, con)

    def crx(self, con, qubit, arg=0, argidx=None):
        return self.add_gate("Rx", qubit, con, arg, argidx)

    def cry(self, con, qubit, arg=0, argidx=None):
        return self.add_gate("Ry", qubit, con, arg, argidx)

    def crz(self, con, qubit, arg=0, argidx=None):
        return self.add_gate("Rz", qubit, con, arg, argidx)

    def m(self, qubits=None, clbits=None):
        if qubits is None:
            qubits = range(self.n_qubits)
        if clbits is None:
            clbits = range(self.n_qubits)
        self.add_measurement(qubits, clbits)

    def measure(self, qubits):
        qubits = self._get_qubits(qubits)
        return self.backend.measure(qubits)

    def state(self):
        return self.backend.state()

    def run_shot(self, *args, **kwargs):
        self.init()
        data = np.zeros(self.n_clbits)
        for inst in self.instructions:
            if isinstance(inst, Gate):
                self.backend.apply_gate(inst, *args, **kwargs)
            elif isinstance(inst, Measurement):
                data = np.zeros(self.n_clbits)
                values = self.backend.measure(inst.qubits)
                for idx, x in zip(inst.cl_indices, values):
                    data[idx] = x
        return data

    def run(self, shots=1, *args, **kwargs):
        data = np.zeros((shots, self.n_clbits))
        for i in range(shots):
            data[i] = self.run_shot(*args, **kwargs)
        self.res = CircuitResult(data, self.basis.labels)
        return self.res

    def histogram(self):
        return self.res.hist

    def show_histogram(self, show=True):
        return self.res.show_histogram(show)
