# -*- coding: utf-8 -*-
"""
Created on 22 Sep 2019
author: Dylan Jones

project: Qsim
version: 1.0
"""
import numpy as np
from qsim import State, kron

X_GATE = np.array([[0, 1], [1, 0]])
Y_GATE = np.array([[0, -1j], [1j, 0]])
Z_GATE = np.array([[1, 0], [0, -1]])
HADAMARD_GATE = np.array([[1, 1], [1, -1]]) / np.sqrt(2)
PHASE_GATE = np.array([[1, 0], [0, 1j]])
T_GATE = np.array([[1, 0], [0, np.exp(1j*np.pi/4)]])


class CircuitObject:

    def __init__(self, register, qubit, name, out=None):
        self.reg = register
        self.qubit = qubit
        self.name = name
        self.out = out

    def __str__(self):
        return f"{self.name} (qubit: {self.qubit})"

    def apply(self, *args, **kwargs):
        pass


class Gate(CircuitObject):

    def __init__(self, register, qubit, array, name, con=None):
        super().__init__(register, qubit, name)
        self.con_quibits = con
        self.array = np.asarray(array)

    def __mul__(self, other):
        pass

    @classmethod
    def single(cls, register, qubit, array, name=""):
        eye = np.eye(2)
        arrs = [eye] * register.n
        arrs[qubit] = array
        return cls(register, qubit, kron(arrs), name)

    @classmethod
    def single_control(cls, register, con, qubit, array, name=""):
        eye = np.eye(2)
        arrs1 = [eye] * register.n
        arrs1[con] = State.p0
        arrs2 = [eye] * register.n
        arrs2[con] = State.p1
        arrs2[qubit] = array
        arr = kron(arrs1) + kron(arrs2)
        return cls(register, qubit, arr, name, con=con)

    def apply(self, verbose=True, *args, **kwargs):
        self.reg.apply_gate(self.array)
