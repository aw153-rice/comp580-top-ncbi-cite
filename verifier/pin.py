"""Checks for pin_top_cited. The pin writes no file; the task compares it as the answer key."""

from .checks import result
from .fields import output_problem, query_problem


def verify_input(value):
    problem = query_problem(value)
    if problem:
        return result(False, problem[1])
    return result(True, "input is valid")


def verify_output(input_value, output_value, _workspace):
    problem = query_problem(input_value) or output_problem(output_value)
    if problem:
        return result(False, problem[1])
    return result(True, "pin output is well formed")
