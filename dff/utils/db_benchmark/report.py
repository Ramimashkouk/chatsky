"""
Report
--------
This method contains a function to print benchmark results to console.
"""
from pathlib import Path
from typing import Union, Set, Literal, Tuple
import json

from humanize import naturalsize

from dff.utils.db_benchmark.benchmark import BenchmarkConfig


def report(
    file: Union[str, Path],
    display: Set[Literal["name", "desc", "config", "sizes", "metrics"]] = set({"name", "metrics"}),
):
    """
    Print average results from a result file to stdout.

    Printed stats contain benchmark configs, object sizes, average benchmark values for successful cases and
    exception message for unsuccessful cases.

    :param file:
        File with benchmark results generated by
        :py:func:`~dff.utils.db_benchmark.benchmark.save_results_to_file`.
    :param display:
        A set of objects to display in results.
        Values allowed inside the set:

            - "name" -- displays the name of the benchmark case.
            - "desc" -- displays the description of the benchmark case.
            - "config" -- displays the config of the benchmark case.
            - "sizes" -- displays size stats for the config.
            - "metrics" -- displays average write, read, update read+update times.
    """
    with open(file, "r", encoding="utf-8") as fd:
        file_contents = json.load(fd)

    def get_benchmark_config_report(benchmark_config, sizes) -> Tuple[str, str]:
        benchmark_config = BenchmarkConfig(**benchmark_config)
        starting_context_size = sizes["starting_context_size"]
        final_context_size = sizes["final_context_size"]
        misc_size = sizes["misc_size"]
        message_size = sizes["message_size"]

        return (
            f"Number of contexts: {benchmark_config.context_num}\n"
            f"From dialog len: {benchmark_config.from_dialog_len}\n"
            f"To dialog len: {benchmark_config.to_dialog_len}\n"
            f"Step dialog len: {benchmark_config.step_dialog_len}\n"
            f"Message misc dimensions: {benchmark_config.message_dimensions}\n"
            f"Misc dimensions: {benchmark_config.misc_dimensions}",
            
            f"Size of misc field: {misc_size} ({naturalsize(misc_size, gnu=True)})\n"
            f"Size of one message: {message_size} ({naturalsize(message_size, gnu=True)})\n"
            f"Starting context size: {starting_context_size} ({naturalsize(starting_context_size, gnu=True)})\n"
            f"Final context size: {final_context_size} ({naturalsize(final_context_size, gnu=True)})",
        )

    sep = "-" * 80

    report_result = "\n".join([sep, file_contents["name"], sep, file_contents["description"], sep, ""])

    for benchmark in file_contents["benchmarks"]:
        config, sizes = get_benchmark_config_report(benchmark["benchmark_config"], benchmark["sizes"])

        reported_values = {
            "name": benchmark["name"],
            "desc": benchmark["description"],
            "config": config,
            "sizes": sizes,
            "metrics": "".join(
                [
                    f"{metric.title() + ': ' + str(benchmark['average_results']['pretty_' + metric]):20}"
                    if benchmark["success"]
                    else benchmark["result"]
                    for metric in ("write", "read", "update", "read+update")
                ]
            ),
        }

        result = []
        for value_name, value in reported_values.items():
            if value_name in display:
                result.append(value)
        result.append("")

        report_result += f"\n{sep}\n".join(result)

    print(report_result, end="")
