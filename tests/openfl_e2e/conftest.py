# Copyright 2020-2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import pytest
import collections
import os
import json
import shutil
import xml.etree.ElementTree as ET
import logging
from utils.logger import configure_logging
from utils.logger import logger as log
from utils.conftest_helper import parse_arguments
import utils.constants as constants
import models.participants as participants

federation_fixture = collections.namedtuple("federation_fixture", "model_owner, aggregator, collaborators, model_name, workspace_path, results_dir")


def pytest_addoption(parser):
    parser.addini("results_dir", "Directory to store test results", default="results")
    parser.addini("log_level", "Logging level", default="DEBUG")
    parser.addoption(
        "--results_dir", action="store", type=str, default="results", help="Results directory"
    )
    parser.addoption(
        "--num_collaborators", action="store", type=int, default=constants.NO_OF_COLLABORATORS, help="Number of collaborators"
    )
    parser.addoption(
        "--num_rounds", action="store", type=int, default=constants.NO_OF_ROUNDS, help="Number of rounds to train"
    )
    parser.addoption(
        "--model_name", action="store", type=str, default=constants.DEFAULT_MODEL_NAME, help="Model name"
    )


@pytest.fixture(scope="session", autouse=True)
def setup_logging(pytestconfig):
    results_dir = pytestconfig.getini("results_dir")
    log_level = pytestconfig.getini("log_level")

    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

    # Setup a global logger to ensure logging works before any test-specific logs are set
    configure_logging(os.path.join(results_dir, "deployment.log"), log_level)
    return logging.getLogger()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook to capture the result of setup, call, and teardown phases.
    This avoids duplicate entries for Pass/Fail in the XML report.
    """
    outcome = yield
    report = outcome.get_result()

    # Retrieve the custom test_id marker if it exists
    test_id_marker = item.get_closest_marker("test_id")
    outcome_mapping = {"passed": "Pass", "failed": "Fail"}
    report_when_mapping = {"setup": "Setup", "call": "Test", "teardown": "Teardown"}
    final_outcome = outcome_mapping.get(report.outcome, report.outcome)
    report_phase = report_when_mapping.get(report.when, report.when)

    # Modify nodeid if test_id is provided and append outcome and phase
    if test_id_marker:
        test_id = test_id_marker.args[0]
        report.nodeid = (
            f"{report.nodeid} [{test_id}] [outcome: {final_outcome}] [phase: {report_phase}]"
        )

    # Initialize XML structure if not already initialized
    if not hasattr(item.config, "_xml_report"):
        item.config._xml_report = ET.Element(
            "testsuite",
            {
                "name": "pytest",
                "errors": "0",
                "failures": "0",
                "skipped": "0",
                "tests": "0",
                "time": "0",
                "timestamp": "",
                "hostname": "",
            },
        )

    # Store the result of each phase (setup/call/teardown)
    if not hasattr(item, "_results"):
        item._results = {}

    # Save the outcome and other details per phase
    item._results[report.when] = {
        "outcome": final_outcome,
        "longrepr": report.longrepr,
        "duration": report.duration,
    }
    # Log failures
    if report.when == "call" and report.failed:
        logger = logging.getLogger()
        logger.error(f"Test {report.nodeid} failed: {call.excinfo.value}")

    # Only create the XML element after the teardown phase
    if report.when == "teardown" and not hasattr(item, "_xml_created"):
        item._xml_created = True  # Ensure XML creation happens only once

        # Determine final outcome based on the worst phase result
        if "call" in item._results:
            final_outcome = item._results["call"]["outcome"]
        elif "setup" in item._results:
            final_outcome = item._results["setup"]["outcome"]
        else:
            final_outcome = "skipped"

        # Create the <testcase> XML element
        testcase = ET.SubElement(
            item.config._xml_report,
            "testcase",
            {
                "classname": item.module.__name__,
                "name": item.name,
                "time": str(sum(result["duration"] for result in item._results.values())),
            },
        )

        # Add <failure> or <skipped> tags based on the final outcome
        if final_outcome == "Fail":
            failure_message = item._results.get("call", {}).get(
                "longrepr", item._results.get("setup", {}).get("longrepr", "Unknown Error")
            )
            failure = ET.SubElement(
                testcase,
                "error",
                {
                    "message": str(failure_message),
                },
            )
            failure.text = str(failure_message)
        elif final_outcome == "skipped":
            skipped_message = item._results.get("setup", {}).get("longrepr", "Skipped")
            skipped = ET.SubElement(
                testcase,
                "skipped",
                {
                    "message": str(skipped_message),
                },
            )
            skipped.text = str(skipped_message)

        # Update the testsuite summary statistics
        tests = int(item.config._xml_report.attrib["tests"]) + 1
        item.config._xml_report.attrib["tests"] = str(tests)
        if final_outcome == "Fail":
            failures = int(item.config._xml_report.attrib["failures"]) + 1
            item.config._xml_report.attrib["failures"] = str(failures)
        elif final_outcome == "skipped":
            skipped = int(item.config._xml_report.attrib["skipped"]) + 1
            item.config._xml_report.attrib["skipped"] = str(skipped)


def pytest_sessionfinish(session, exitstatus):
    # Clear the .pytest_cache directory after the test session is finished
    cache_dir = os.path.join(session.config.rootdir, ".pytest_cache")
    log.debug(f"\nClearing .pytest_cache directory at {cache_dir}")
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir, ignore_errors=False)
        log.debug(f"Cleared .pytest_cache directory at {cache_dir}")


# @pytest.fixture(scope="session")
# def global_config(pytestconfig):
#     args = parse_arguments()
#     config = {
#         "deploy_repo_path": pytestconfig.getoption("--deploy-repo-path") or args.deploy_repo_path,
#         "results_dir": pytestconfig.getoption("--results-dir") or args.results_dir or pytestconfig.getini(
#             "results_dir"),
#         "repo_dir": pytestconfig.getoption("--repo-dir") or args.repo_dir or get_default_repo_dir(),
#         "log_level": pytestconfig.getini("log_level"),
#         "num_collaborators": pytestconfig.getoption("--num-collaborators") or args.num_collaborators,
#         "test_mode": pytestconfig.getoption("--test-mode") or args.test_mode,
#         "browser_type": pytestconfig.getoption("--browser-type") or args.browser_type,
#         "keep_deployment": pytestconfig.getoption("--keep-deployment")
#     }
#     return config


# @pytest.fixture(autouse=True)
# def manage_logs(request, global_config):
#     """Set log file name same as test name and results_dir to include module name"""
#     results_dir = global_config['results_dir']
#     log_level = global_config['log_level']
#     suite_name = request.node.fspath.purebasename
#     test_name = request.node.name
#     module_results_dir = os.path.join(results_dir, suite_name)
#     os.makedirs(module_results_dir, exist_ok=True)
#     log_file = os.path.join(module_results_dir, f"{test_name}.log")

#     # Clear existing handlers, if any
#     logger = logging.getLogger()
#     while logger.handlers:
#         logger.handlers.pop()

#     # Configure logging for the specific test
#     configure_logging(log_file, log_level)
#     global_config['test_results_dir'] = module_results_dir
#     global_config['test_name'] = test_name


@pytest.fixture(scope="module")
def fx_federation(request, pytestconfig):
    """
    Fixture for federation. This fixture is used to create the model owner, aggregator, and collaborators.
    It also creates workspace.
    Args:
        request: pytest request object. Model name is passed as a parameter to the fixture from test cases.
        pytestconfig: pytest config object
    """
    log.info("Fixture for federation")
    # TODO - /etc/hosts file entry for the aggregator
    log.info(f"Params are: {request.param}")
    model_name = request.param
    args = parse_arguments()
    results_dir = args.results_dir or pytestconfig.getini("results_dir")
    num_collaborators = args.num_collaborators
    num_rounds = args.num_rounds
    collaborators = []
    log.info(f"num_collaborators: {num_collaborators}, num_rounds: {num_rounds}, model_name: {model_name}")
    workspace_name = f"workspace_{model_name}"
    model_owner = participants.ModelOwner(workspace_name, model_name)
    workspace_path = model_owner.create_workspace(results_dir=results_dir)
    log.info(f"Created the workspace at {workspace_path}")

    aggregator = participants.Aggregator(agg_domain_name="aggregator", workspace_path=workspace_path)

    for i in range(num_collaborators):
        collaborator = participants.Collaborator(collaborator_name=f"collaborator{i+1}", data_directory_path=i+1, workspace_path=workspace_path)
        collaborators.append(collaborator)

    return federation_fixture(
        model_owner=model_owner,
        aggregator=aggregator,
        collaborators=collaborators,
        model_name=model_name,
        workspace_path=workspace_path,
        results_dir=results_dir,
    )


# @pytest.fixture(scope="module", autouse=True)
# def teardown_module(request, federation, global_config):
#     def finalizer():
#         if global_config['keep_deployment']:
#             log.info("Keeping the deployment as per the request")
#         else:
#             delete_federation(federation)
#             log.info("Federation deleted")

#     request.addfinalizer(finalizer)


