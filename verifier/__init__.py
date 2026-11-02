"""The deterministic verifier: each tool's checks live in its own module, on contract instances."""

from contract import Task, Tool

from . import pin, top_cited

TOOLS = {
    Tool.TOP_CITED_PUBMED: top_cited,
    Tool.PIN_TOP_CITED: pin,
}
TASKS = {Task.TOP_CITED_PAPER: top_cited.verify_task}


def verify_input(tool, value):
    return TOOLS[Tool(tool)].verify_input(value)


def verify_output(tool, input_value, output_value, workspace):
    return TOOLS[Tool(tool)].verify_output(input_value, output_value, workspace)


def verify_task(task, arguments, output, reference, workspace):
    return TASKS[Task(task)](arguments, output, reference, workspace)
