# Copyright 2020-2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import pytest
import time
import concurrent.futures

from utils.logger import logger as log


# Create fx_federation fixture with model name as parameter
@pytest.mark.parametrize('fx_federation', ['torch_cnn_mnist'], indirect=True)
def test_torch_cnn_mnist(fx_federation):
    """
    Test for torch_cnn_mnist model.
    """
    log.info(f"Test for torch_cnn_mnist with fx_federation: {fx_federation}")

    # Check if the workspace is already created and call the respective functions accordingly
    if not fx_federation.use_existing_workspace:
        # Model owner operations
        assert fx_federation.model_owner.initialize_plan(agg_domain_name="aggregator"), "Failed to initialize plan for aggregator"
        assert fx_federation.model_owner.certify_workspace(), "Failed to certify workspace"

        # Aggregator operations
        assert fx_federation.aggregator.generate_sign_request(), "Failed to generate sign request for aggregator"
        assert fx_federation.aggregator.certify_request(), "Failed to certify request for aggregator"

        # Collaborator operations
        for collaborator in fx_federation.collaborators:
            log.info(f"Performing operations for: {collaborator.collaborator_name}")
            assert collaborator.create_collaborator(), f"Failed to create collaborator {collaborator.collaborator_name}"
            assert collaborator.generate_sign_request(), f"Failed to generate sign request for collaborator {collaborator.collaborator_name}"
            # Below step will add collaborator entries in cols.yaml file.
            assert fx_federation.aggregator.sign_collaborator_csr(collaborator.collaborator_name), f"Failed to sign CSR for collaborator {collaborator.collaborator_name}"
            assert collaborator.import_certify_csr(), f"Failed to import and certify CSR for collaborator {collaborator.collaborator_name}"
    else:
        # If the workspace is already created, then we need to import the existing workspace
        # assert fx_federation.model_owner.import_workspace(), "Failed to import workspace"
        log.info("Using existing workspace")

    # Start the collaborators and aggregator
    executor = concurrent.futures.ThreadPoolExecutor()
    # As the collaborators will wait for aggregator to start, we need to start them in parallel.
    futures = [
        executor.submit(
            participant.start
        )
        for participant in fx_federation.collaborators + [fx_federation.aggregator]
    ]

    # Result will contain a list of tuple of replica and operator objects.
    results = [f.result() for f in futures]
    log.info(f"Results: {results}")

    assert verify_federation_run_completion(fx_federation, results), "Federation completion failed"
    log.info("Test case passed")


def verify_federation_run_completion(fx_federation, results):
    """
    Verify the completion of the process for all the participants
    """
    # Start the collaborators and aggregator
    executor = concurrent.futures.ThreadPoolExecutor()
    # As the collaborators will wait for aggregator to start, we need to start them in parallel.
    futures = [
        executor.submit(
            _verify_completion_for_participant,
            participant,
            results[i]
        )
        for i, participant in enumerate(fx_federation.collaborators + [fx_federation.aggregator])
    ]

    # Result will contain a list of tuple of replica and operator objects.
    results = [f.result() for f in futures]
    log.info(f"Results: {results}")

    # If any of the participant failed, return False, else return True
    return all(results)


def _verify_completion_for_participant(participant, result_file):
    """
    Verify the completion of the process for the participant
    Args:
        participant (object): Participant object
        result_file (str): Result file
    """
    # Wait for the successful output message to appear in the log till timeout
    timeout = 900 # in seconds

    with open(result_file, 'r') as file:
        content = file.read()
    start_time = time.time()
    while (
        "OK" not in content and time.time() - start_time < timeout
    ):
        with open(result_file, 'r') as file:
            content = file.read()
        log.info(f"Process is yet to complete for {participant.name}")
        time.sleep(45)
    
    if "OK" not in content:
        log.error(f"Process failed/incomplete for {participant.name} after timeout of {timeout} seconds")
        return False
    else:
        log.info(f"Process completed for {participant.name} in {time.time() - start_time} seconds")
        return True


# @pytest.mark.parametrize('fx_federation', ['torch_cnn_histology'], indirect=True)
# def test_torch_cnn_histology(fx_federation):
#     log.info("Test for torch_cnn_histology")


# def test_keras_cnn_mnist():
#     log.info("Test for keras_cnn_mnist")


# def test_tf_2dunet():
#     log.info("Test for tf_2dunet")


# def test_tf_cnn_histology():
#     log.info("Test for tf_cnn_histology")
