# -*- coding: utf-8 -*-

# Copyright 2017, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

# pylint: disable=invalid-name

"""
controlled-NOT gate.
"""
from qiskit.circuit import CompositeGate
from qiskit.circuit import Gate
from qiskit.circuit import QuantumCircuit
from qiskit.circuit import QuantumRegister
from qiskit.circuit.decorators import _op_expand
from qiskit.dagcircuit import DAGCircuit
from qiskit.extensions.standard.cxbase import CXBase


class CnotGate(Gate):
    """controlled-NOT gate."""

    def __init__(self, ctl, tgt, circ=None):
        """Create new CNOT gate."""
        super().__init__("cx", [], [ctl, tgt], circ)

    def _define_decompositions(self):
        """
        gate cx c,t { CX c,t; }
        """
        decomposition = DAGCircuit()
        q = QuantumRegister(2, "q")
        decomposition.add_qreg(q)
        rule = [
            CXBase(q[0], q[1])
        ]
        for inst in rule:
            decomposition.apply_operation_back(inst)
        self._decompositions = [decomposition]

    def inverse(self):
        """Invert this gate."""
        return self  # self-inverse

    def reapply(self, circ):
        """Reapply this gate to corresponding qubits in circ."""
        self._modifiers(circ.cx(self.qargs[0], self.qargs[1]))


@_op_expand(2)
def cx(self, ctl, tgt):
    """Apply CX from ctl to tgt."""
    return self._attach(CnotGate(ctl, tgt, self))


QuantumCircuit.cx = cx
CompositeGate.cx = cx
