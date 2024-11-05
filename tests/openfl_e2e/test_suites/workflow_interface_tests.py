# Copyright 2020-2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import pytest
from utils.logger import logger as log


# Create fx_federation fixture.

def test_torch_cnn_mnist():
    log.info("Test for torch_cnn_mnist")


def test_torch_cnn_histology():
    log.info("Test for torch_cnn_histology")


def test_keras_cnn_mnist():
    log.info("Test for keras_cnn_mnist")


def test_tf_2dunet():
    log.info("Test for tf_2dunet")


def test_tf_cnn_histology():
    log.info("Test for tf_cnn_histology")
