import time
from typing import Union

from openfermion import (
    SymbolicOperator,
    bravyi_kitaev,
    get_fermion_operator,
    jordan_wigner,
)
from zquantum.core.openfermion import load_interaction_operator, save_qubit_operator
from zquantum.core.utils import save_timing


def transform_interaction_operator(
    transformation: str, input_operator: Union[str, SymbolicOperator]
):
    """Transform an interaction operator through either the Bravyi-Kitaev or
    Jordan-Wigner transformations. The results are serialized into a JSON under the
    files: "transformed-operator.json" and "timing.json"

    ARGS:
        transformation: The transformation to use. Either "Jordan-Wigner" or
            "Bravyi-Kitaev"
        input_operator: The interaction operator to transform
    """
    if isinstance(input_operator, str):
        input_operator = load_interaction_operator(input_operator)

    if transformation == "Jordan-Wigner":
        transformation_function = jordan_wigner
    elif transformation == "Bravyi-Kitaev":
        input_operator = get_fermion_operator(input_operator)
        transformation_function = bravyi_kitaev
    else:
        raise RuntimeError("Unrecognized transformation ", transformation)

    start_time = time.time()
    transformed_operator = transformation_function(input_operator)
    walltime = time.time() - start_time

    save_qubit_operator(transformed_operator, "transformed-operator.json")
    save_timing(walltime, "timing.json")
