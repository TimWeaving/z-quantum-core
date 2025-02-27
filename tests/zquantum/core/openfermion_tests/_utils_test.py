import random
import unittest

import numpy as np
import pkg_resources
from openfermion import (
    FermionOperator,
    IsingOperator,
    QubitOperator,
    get_fermion_operator,
    get_interaction_operator,
    get_sparse_operator,
    jordan_wigner,
    qubit_operator_sparse,
)
from openfermion.hamiltonians import fermi_hubbard
from openfermion.linalg import jw_get_ground_state_at_particle_number
from zquantum.core.circuits import Circuit, X, Y, Z
from zquantum.core.measurement import ExpectationValues
from zquantum.core.openfermion._io import load_interaction_operator
from zquantum.core.openfermion._utils import (
    change_operator_type,
    create_circuits_from_qubit_operator,
    evaluate_qubit_operator,
    evaluate_qubit_operator_list,
    generate_random_qubitop,
    get_diagonal_component,
    get_expectation_value,
    get_fermion_number_operator,
    get_ground_state_rdm_from_qubit_op,
    get_polynomial_tensor,
    get_qubitop_from_coeffs_and_labels,
    get_qubitop_from_matrix,
    remove_inactive_orbitals,
    reverse_qubit_order,
)
from zquantum.core.utils import RNDSEED, hf_rdm
from zquantum.core.wavefunction import Wavefunction


class TestQubitOperator(unittest.TestCase):
    def test_build_qubitoperator_from_coeffs_and_labels(self):
        # Given
        test_op = QubitOperator(((0, "Y"), (1, "X"), (2, "Z"), (4, "X")), 3.0j)
        coeffs = [3.0j]
        labels = [[2, 1, 3, 0, 1]]

        # When
        build_op = get_qubitop_from_coeffs_and_labels(coeffs, labels)

        # Then
        self.assertEqual(test_op, build_op)

    def test_qubitop_matrix_converion(self):
        # Given
        m = 4
        n = 2 ** m
        TOL = 10 ** -15
        random.seed(RNDSEED)
        A = np.array([[random.uniform(-1, 1) for x in range(n)] for y in range(n)])

        # When
        A_qubitop = get_qubitop_from_matrix(A)
        A_qubitop_matrix = np.array(qubit_operator_sparse(A_qubitop).todense())
        test_matrix = A_qubitop_matrix - A

        # Then
        for row in test_matrix:
            for elem in row:
                self.assertEqual(abs(elem) < TOL, True)

    def test_generate_random_qubitop(self):
        # Given
        nqubits = 4
        nterms = 5
        nlocality = 2
        max_coeff = 1.5
        fixed_coeff = False

        # When
        qubit_op = generate_random_qubitop(
            nqubits, nterms, nlocality, max_coeff, fixed_coeff
        )
        # Then
        self.assertEqual(len(qubit_op.terms), nterms)
        for term, coefficient in qubit_op.terms.items():
            for i in range(nlocality):
                self.assertLess(term[i][0], nqubits)
            self.assertEqual(len(term), nlocality)
            self.assertLessEqual(np.abs(coefficient), max_coeff)

        # Given
        fixed_coeff = True
        # When
        qubit_op = generate_random_qubitop(
            nqubits, nterms, nlocality, max_coeff, fixed_coeff
        )
        # Then
        self.assertEqual(len(qubit_op.terms), nterms)
        for term, coefficient in qubit_op.terms.items():
            self.assertEqual(np.abs(coefficient), max_coeff)

    def test_evaluate_qubit_operator(self):
        # Given
        qubit_op = QubitOperator("0.5 [] + 0.5 [Z1]")
        expectation_values = ExpectationValues([0.5, 0.5])
        # When
        value_estimate = evaluate_qubit_operator(qubit_op, expectation_values)
        # Then
        self.assertAlmostEqual(value_estimate.value, 0.5)

    def test_evaluate_qubit_operator_list(self):
        # Given
        qubit_op_list = [
            QubitOperator("0.5 [] + 0.5 [Z1]"),
            QubitOperator("0.3 [X1] + 0.2[Y2]"),
        ]
        expectation_values = ExpectationValues([0.5, 0.5, 0.4, 0.6])
        # When
        value_estimate = evaluate_qubit_operator_list(qubit_op_list, expectation_values)
        # Then
        self.assertAlmostEqual(value_estimate.value, 0.74)

    def test_reverse_qubit_order(self):
        # Given
        op1 = QubitOperator("[Z0 Z1]")
        op2 = QubitOperator("[Z1 Z0]")

        # When/Then
        self.assertEqual(op1, reverse_qubit_order(op2))

        # Given
        op1 = QubitOperator("Z0")
        op2 = QubitOperator("Z1")

        # When/Then
        self.assertEqual(op1, reverse_qubit_order(op2, n_qubits=2))
        self.assertEqual(op2, reverse_qubit_order(op1, n_qubits=2))

    def test_get_expectation_value(self):
        """Check <Z0> and <Z1> for the state |100>"""
        # Given
        wf = Wavefunction([0, 1, 0, 0, 0, 0, 0, 0])
        op1 = QubitOperator("Z0")
        op2 = QubitOperator("Z1")
        # When
        exp_op1 = get_expectation_value(op1, wf)
        exp_op2 = get_expectation_value(op2, wf)

        # Then
        self.assertAlmostEqual(-1, exp_op1)
        self.assertAlmostEqual(1, exp_op2)

    def test_change_operator_type(self):
        # Given
        operator1 = QubitOperator("Z0 Z1", 4.5)
        operator2 = IsingOperator("Z0 Z1", 4.5)
        operator3 = IsingOperator()
        operator4 = IsingOperator("Z0", 0.5) + IsingOperator("Z1", 2.5)
        # When
        new_operator1 = change_operator_type(operator1, IsingOperator)
        new_operator2 = change_operator_type(operator2, QubitOperator)
        new_operator3 = change_operator_type(operator3, QubitOperator)
        new_operator4 = change_operator_type(operator4, QubitOperator)

        # Then
        self.assertEqual(IsingOperator("Z0 Z1", 4.5), new_operator1)
        self.assertEqual(QubitOperator("Z0 Z1", 4.5), new_operator2)
        self.assertEqual(QubitOperator(), new_operator3)
        self.assertEqual(
            QubitOperator("Z0", 0.5) + QubitOperator("Z1", 2.5), new_operator4
        )

    def test_get_fermion_number_operator(self):
        # Given
        n_qubits = 4
        n_particles = None
        correct_operator = get_interaction_operator(
            FermionOperator(
                """
        0.0 [] +
        1.0 [0^ 0] +
        1.0 [1^ 1] +
        1.0 [2^ 2] +
        1.0 [3^ 3]
        """
            )
        )

        # When
        number_operator = get_fermion_number_operator(n_qubits)

        # Then
        self.assertEqual(number_operator, correct_operator)

        # Given
        n_qubits = 4
        n_particles = 2
        correct_operator = get_interaction_operator(
            FermionOperator(
                """
        -2.0 [] +
        1.0 [0^ 0] +
        1.0 [1^ 1] +
        1.0 [2^ 2] +
        1.0 [3^ 3]
        """
            )
        )

        # When
        number_operator = get_fermion_number_operator(n_qubits, n_particles)

        # Then
        self.assertEqual(number_operator, correct_operator)

    def test_create_circuits_from_qubit_operator(self):
        # Initialize target
        circuit1 = Circuit([Z(0), X(1)])
        circuit2 = Circuit([Y(0), Z(1)])

        # Given
        qubit_op = QubitOperator("Z0 X1") + QubitOperator("Y0 Z1")

        # When
        pauli_circuits = create_circuits_from_qubit_operator(qubit_op)

        # Then
        self.assertEqual(pauli_circuits[0], circuit1)
        self.assertEqual(pauli_circuits[1], circuit2)


class TestOtherUtils(unittest.TestCase):
    def test_get_diagonal_component_polynomial_tensor(self):
        fermion_op = FermionOperator("0^ 1^ 2^ 0 1 2", 1.0)
        fermion_op += FermionOperator("0^ 1^ 2^ 0 1 3", 2.0)
        fermion_op += FermionOperator((), 3.0)
        polynomial_tensor = get_polynomial_tensor(fermion_op)
        diagonal_op, remainder_op = get_diagonal_component(polynomial_tensor)
        self.assertTrue((diagonal_op + remainder_op) == polynomial_tensor)
        diagonal_qubit_op = jordan_wigner(get_fermion_operator(diagonal_op))
        remainder_qubit_op = jordan_wigner(get_fermion_operator(remainder_op))
        for term in diagonal_qubit_op.terms:
            for pauli in term:
                self.assertTrue(pauli[1] == "Z")
        for term in remainder_qubit_op.terms:
            is_diagonal = True
            for pauli in term:
                if pauli[1] != "Z":
                    is_diagonal = False
                    break
            self.assertFalse(is_diagonal)

    def test_get_diagonal_component_interaction_op(self):
        fermion_op = FermionOperator("1^ 1", 0.5)
        fermion_op += FermionOperator("2^ 2", 0.5)
        fermion_op += FermionOperator("1^ 2^ 0 3", 0.5)
        diagonal_op, remainder_op = get_diagonal_component(
            get_interaction_operator(fermion_op)
        )
        self.assertTrue(
            (diagonal_op + remainder_op) == get_interaction_operator(fermion_op)
        )
        diagonal_qubit_op = jordan_wigner(diagonal_op)
        remainder_qubit_op = jordan_wigner(remainder_op)
        for term in diagonal_qubit_op.terms:
            for pauli in term:
                self.assertTrue(pauli[1] == "Z")
        is_diagonal = True
        for term in remainder_qubit_op.terms:
            for pauli in term:
                if pauli[1] != "Z":
                    is_diagonal = False
                    break
        self.assertFalse(is_diagonal)

    def test_get_ground_state_rdm_from_qubit_op(self):
        # Given
        n_sites = 2
        U = 5.0
        fhm = fermi_hubbard(
            x_dimension=n_sites,
            y_dimension=1,
            tunneling=1.0,
            coulomb=U,
            chemical_potential=U / 2,
            magnetic_field=0,
            periodic=False,
            spinless=False,
            particle_hole_symmetry=False,
        )
        fhm_qubit = jordan_wigner(fhm)
        fhm_int = get_interaction_operator(fhm)
        e, wf = jw_get_ground_state_at_particle_number(
            get_sparse_operator(fhm), n_sites
        )

        # When
        rdm = get_ground_state_rdm_from_qubit_op(
            qubit_operator=fhm_qubit, n_particles=n_sites
        )

        # Then
        self.assertAlmostEqual(e, rdm.expectation(fhm_int))

    def test_remove_inactive_orbitals(self):
        fermion_ham = load_interaction_operator(
            pkg_resources.resource_filename(
                "zquantum.core.testing", "hamiltonian_HeH_plus_STO-3G.json"
            )
        )
        frozen_ham = remove_inactive_orbitals(fermion_ham, 1, 1)
        self.assertEqual(frozen_ham.one_body_tensor.shape[0], 2)

        hf_energy = hf_rdm(1, 1, 2).expectation(fermion_ham)
        self.assertAlmostEqual(frozen_ham.constant, hf_energy)
