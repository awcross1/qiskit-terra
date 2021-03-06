# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""Helper function for converting a dag to a circuit"""
import collections

from qiskit.circuit import QuantumCircuit
from qiskit.circuit import ClassicalRegister
from qiskit.circuit import QuantumRegister


def dag_to_circuit(dag):
    """Build a ``QuantumCircuit`` object from a ``DAGCircuit``.

    Args:
        dag (DAGCircuit): the input dag.

    Return:
        QuantumCircuit: the circuit representing the input dag.
    """
    qregs = collections.OrderedDict()
    for qreg in dag.qregs.values():
        qreg_tmp = QuantumRegister(qreg.size, name=qreg.name)
        qregs[qreg.name] = qreg_tmp
    cregs = collections.OrderedDict()
    for creg in dag.cregs.values():
        creg_tmp = ClassicalRegister(creg.size, name=creg.name)
        cregs[creg.name] = creg_tmp

    name = dag.name or None
    circuit = QuantumCircuit(*qregs.values(), *cregs.values(), name=name)

    for node in dag.node_nums_in_topological_order():
        n = dag.node(node)
        if n['type'] == 'op':
            qubits = []
            for qubit in n['qargs']:
                qubits.append(qregs[qubit[0].name][qubit[1]])

            clbits = []
            for clbit in n['cargs']:
                clbits.append(cregs[clbit[0].name][clbit[1]])

            # Get arguments for classical control (if any)
            if n['condition'] is None:
                control = None
            else:
                control = (n['condition'][0], n['condition'][1])

            def duplicate_instruction(inst):
                """Create a fresh instruction from an input instruction."""
                if inst.name == 'barrier':
                    params = [inst.qargs]
                elif inst.name == 'snapshot':
                    params = inst.params + [inst.qargs]
                else:
                    params = inst.params + inst.qargs + inst.cargs
                new_inst = inst.__class__(*params)
                return new_inst

            inst = duplicate_instruction(n['op'])
            inst.control = control
            circuit._attach(inst)

    return circuit
