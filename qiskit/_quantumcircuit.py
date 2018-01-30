# -*- coding: utf-8 -*-

# Copyright 2017 IBM RESEARCH. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================

"""
Quantum circuit object.
"""
import itertools
from collections import OrderedDict
from ._qiskiterror import QISKitError
from ._register import Register
from ._quantumregister import QuantumRegister
from ._classicalregister import ClassicalRegister
from ._measure import Measure
from ._reset import Reset
from ._instructionset import InstructionSet
from .dagcircuit import DAGCircuit


class QuantumCircuit(object):
    """Quantum circuit."""

    # Class variable OPENQASM header
    header = "OPENQASM 2.0;"

    # Class variable with gate definitions
    # This is a dict whose values are dicts with the
    # following keys:
    #   "opaque" = True or False
    #   "n_args" = number of real parameters
    #   "n_bits" = number of qubits
    #   "args"   = list of parameter names
    #   "bits"   = list of qubit names
    #   "body"   = GateBody AST node
    definitions = {}

    def __init__(self, *regs):
        """Create a new circuit."""
        # Data contains a list of instructions in the order they were applied.
        self.data = []
        # This is a map of registers bound to this circuit, by name.
        self.regs = OrderedDict()
        self.add(*regs)

    def has_register(self, register):
        """
        Test if this circuit has the register r.

        Return True or False.
        """
        if register.name in self.regs:
            registers = self.regs[register.name]
            if registers.size == register.size:
                if ((isinstance(register, QuantumRegister) and
                     isinstance(registers, QuantumRegister)) or
                        (isinstance(register, ClassicalRegister) and
                         isinstance(registers, ClassicalRegister))):
                    return True
        return False

    def get_qregs(self):
        """Get the qregs from the registers."""
        qregs = {}
        for name, register in self.regs.items():
            if isinstance(register, QuantumRegister):
                qregs[name] = register
        return qregs

    def get_cregs(self):
        """Get the cregs from the registers."""
        cregs = {}
        for name, register in self.regs.items():
            if isinstance(register, ClassicalRegister):
                cregs[name] = register
        return cregs

    def combine(self, rhs):
        """
        Append rhs to self if self contains rhs's registers.

        Return self + rhs as a new object.
        """
        for register in rhs.regs.values():
            if not self.has_register(register):
                raise QISKitError("circuits are not compatible")
        circuit = QuantumCircuit(
            *[register for register in self.regs.values()])
        for gate in itertools.chain(self.data, rhs.data):
            gate.reapply(circuit)
        return circuit

    def extend(self, rhs):
        """
        Append rhs to self if self contains rhs's registers.

        Modify and return self.
        """
        for register in rhs.regs.values():
            if not self.has_register(register):
                raise QISKitError("circuits are not compatible")
        for gate in rhs.data:
            gate.reapply(self)
        return self

    def __add__(self, rhs):
        """Overload + to implement self.concatenate."""
        return self.combine(rhs)

    def __iadd__(self, rhs):
        """Overload += to implement self.extend."""
        return self.extend(rhs)

    def __len__(self):
        """Return number of operations in circuit."""
        return len(self.data)

    def __getitem__(self, item):
        """Return indexed operation."""
        return self.data[item]

    def _attach(self, gate):
        """Attach a gate."""
        self.data.append(gate)
        return gate

    def add(self, *regs):
        """Add registers."""
        for register in regs:
            if not isinstance(register, Register):
                raise QISKitError("expected a register")
            if register.name not in self.regs:
                self.regs[register.name] = register
            else:
                raise QISKitError("register name \"%s\" already exists"
                                  % register.name)

    def _check_qreg(self, register):
        """Raise exception if r is not in this circuit or not qreg."""
        if not isinstance(register, QuantumRegister):
            raise QISKitError("expected quantum register")
        if not self.has_register(register):
            raise QISKitError(
                "register '%s' not in this circuit" %
                register.name)

    def _check_qubit(self, qubit):
        """Raise exception if qubit is not in this circuit or bad format."""
        self._check_qreg(qubit[0])
        qubit[0].check_range(qubit[1])

    def _check_creg(self, register):
        """Raise exception if r is not in this circuit or not creg."""
        if not isinstance(register, ClassicalRegister):
            raise QISKitError("expected classical register")
        if not self.has_register(register):
            raise QISKitError(
                "register '%s' not in this circuit" %
                register.name)

    def _check_dups(self, qubits):
        """Raise exception if list of qubits contains duplicates."""
        squbits = set(qubits)
        if len(squbits) != len(qubits):
            raise QISKitError("duplicate qubit arguments")

    def qasm(self):
        """Return OPENQASM string."""
        string = self.header + "\n"
        for register in self.regs.values():
            string += register.qasm() + "\n"
        for instruction in self.data:
            string += instruction.qasm() + "\n"
        return string

    def dag(self):
        """Return corresponding DAGCircuit object.

        None of the gates are expanded, i.e. the gates that are defined in the
        circuit are included in the gate basis.
        """
        dagcircuit = DAGCircuit()
        # Add registers
        for register in self.regs.values():
            if isinstance(register, QuantumRegister):
                dagcircuit.add_qreg(register.name, len(register))
            else:
                dagcircuit.add_creg(register.name, len(register))
        # Add user gate definitions
        for name, data in self.definitions.items():
            dagcircuit.add_basis_element(name, data["n_bits"], 0,
                                         data["n_args"])
            dagcircuit.add_gate_data(name, data)
        # Add instructions
        builtins = {
            "U": ["U", 1, 0, 3],
            "CX": ["CX", 2, 0, 0],
            "measure": ["measure", 1, 1, 0],
            "reset": ["reset", 1, 0, 0],
            "barrier": ["barrier", -1, 0, 0]
        }
        for instruction in self.data:
            # Add OpenQASM built-in gates on demand
            if instruction.name in builtins:
                dagcircuit.add_basis_element(*builtins[instruction.name])
            # Separate classical arguments to measurements
            if instruction.name == "measure":
                qargs = [(instruction.arg[0][0].name, instruction.arg[0][1])]
                cargs = [(instruction.arg[1][0].name, instruction.arg[1][1])]
            else:
                qargs = list(map(lambda x: (x[0].name, x[1]), instruction.arg))
                cargs = []
            # Get arguments for classical control (if any)
            if instruction.control is None:
                control = None
            else:
                control = (instruction.control[0].name, instruction.control[1])
            dagcircuit.apply_operation_back(instruction.name, qargs, cargs,
                                            instruction.param,
                                            control)
        return dagcircuit

    def measure(self, qubit, cbit):
        """Measure quantum bit into classical bit (tuples).

        Returns:
            Gate: the attached measure gate.

        Raises:
            QISKitError: if qubit is not in this circuit or bad format;
                if cbit is not in this circuit or not creg.
        """
        if isinstance(qubit, QuantumRegister) and \
           isinstance(cbit, ClassicalRegister) and len(qubit) == len(cbit):
            instructions = InstructionSet()
            for i in range(qubit.size):
                instructions.add(self.measure((qubit, i), (cbit, i)))
            return instructions

        self._check_qubit(qubit)
        self._check_creg(cbit[0])
        cbit[0].check_range(cbit[1])
        return self._attach(Measure(qubit, cbit, self))

    def reset(self, quantum_register):
        """Reset q."""
        if isinstance(quantum_register, QuantumRegister):
            instructions = InstructionSet()
            for sizes in range(quantum_register.size):
                instructions.add(self.reset((quantum_register, sizes)))
            return instructions
        self._check_qubit(quantum_register)
        return self._attach(Reset(quantum_register, self))
