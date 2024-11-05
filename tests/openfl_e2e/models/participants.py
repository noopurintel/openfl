# Copyright 2020-2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import os
import subprocess
from datetime import datetime

import utils.constants as constants
from utils.logger import logger as log
import utils.subprocess_helper as sh


# Define the Aggregator class
class Aggregator():
    def __init__(self, agg_domain_name, workspace_path=None):
        self.name = agg_domain_name
        self.agg_domain_name = agg_domain_name
        self.workspace_path = workspace_path

    def generate_sign_request(self):
        log.info(f"Generated a sign request for {self.agg_domain_name}")
        try:
            sh.run_command(f"fx aggregator generate-cert-request --fqdn {self.agg_domain_name}", work_dir=self.workspace_path)
        except Exception as e:
            log.error(f"Failed to generate the sign request: {e}")
            raise e
        return True
    
    def certify_request(self):
        log.info(f"CA should sign the aggregator {self.agg_domain_name} request")
        try:
            sh.run_command(f"fx aggregator certify --silent --fqdn {self.agg_domain_name}", work_dir=self.workspace_path)
            log.info(f"CA signed the request from {self.agg_domain_name}")
        except Exception as e:
            log.error(f"Failed to certify the aggregator request : {e}")
            raise e
        return True

    def sign_collaborator_csr(self, collaborator_name):
        try:
            zip_name = f"col_{collaborator_name}_to_agg_cert_request.zip"
            col_zip = os.path.join(os.getcwd(), self.workspace_path, zip_name)
            _, output, error = sh.run_command(f"fx collaborator certify --request-pkg {col_zip} -s", work_dir=self.workspace_path)
            if "OK" in output:
                log.info(f"Successfully signed the CSR for the collaborator {collaborator_name} with zip path {col_zip}")
            else:
                log.error(f"Failed to sign the CSR for collaborator {collaborator_name}: {error}")

        except Exception as e:
            log.error(f"Failed to sign the CSR: {e}")
            raise e
        return True

    def start(self):
        try:
            log.info(f"Starting the aggregator {self.agg_domain_name}")
            curr_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.agg_domain_name}_{curr_time}.log"
            res_file = os.path.join(os.getcwd(), self.workspace_path, filename)
            log.info(f"Results file: {res_file}")
            bg_file = open(res_file, "w", buffering=1)

            sh.run_command_background("fx aggregator start", work_dir=self.workspace_path, redirect_to_file=bg_file, check_sleep=60)
            log.info(f"Started the aggregator {self.agg_domain_name}")
        except Exception as e:
            log.error(f"Failed to start the aggregator: {e}")
            res_file.close()
            raise e
        return res_file


# Define the Collaborator class
class Collaborator():
    def __init__(self, collaborator_name=None, data_directory_path=None, workspace_path=None):
        self.name = collaborator_name
        self.collaborator_name = collaborator_name
        self.data_directory_path = data_directory_path
        self.workspace_path = workspace_path

    def generate_sign_request(self):
        try:
            sh.run_command(f"fx collaborator generate-cert-request -n {self.collaborator_name}", work_dir=self.workspace_path)
            log.info(f"Generated a sign request for {self.collaborator_name}")
        except Exception as e:
            log.error(f"Failed to generate the sign request: {e}")
            raise e
        return True
    
    def create_collaborator(self):
        try:
            sh.run_command(f"fx collaborator create -n {self.collaborator_name} -d {self.data_directory_path}", work_dir=self.workspace_path)
            log.info(f"Created {self.collaborator_name} with the data directory {self.data_directory_path}")
        except Exception as e:
            log.error(f"Failed to create the collaborator: {e}")
            raise e
        return True
    
    def import_certify_csr(self):
        try:
            zip_name = f"agg_to_col_{self.collaborator_name}_signed_cert.zip"
            col_zip = os.path.join(os.getcwd(), self.workspace_path, zip_name)
            _, output, error = sh.run_command(f"fx collaborator certify --import {col_zip}", work_dir=self.workspace_path)
            log.info(f"Imported and certified the CSR for {self.collaborator_name} with zip path {col_zip}")
            if "OK" in output:
                log.info(f"Successfully imported and certified the CSR for {self.collaborator_name}")
            else:
                log.error(f"Failed to import and certify the CSR for {self.collaborator_name}: {error}")

        except Exception as e:
            log.error(f"Failed to import and certify the CSR: {e}")
            raise e
        return True

    def start(self):
        try:
            log.info(f"Starting the collaborator {self.collaborator_name}")
            curr_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.collaborator_name}_{curr_time}.log"
            res_file = os.path.join(os.getcwd(), self.workspace_path, filename)
            log.info(f"Results file: {res_file} and type: {type(res_file)}")
            bg_file = open(res_file, "w", buffering=1)

            sh.run_command_background(f"fx collaborator start -n {self.collaborator_name}", work_dir=self.workspace_path, redirect_to_file=bg_file, check_sleep=60)
            log.info(f"Started {self.collaborator_name}")
        except Exception as e:
            log.error(f"Failed to start the collaborator: {e}")
            res_file.close()
            raise e
        return res_file


# Define the ModelOwner class
class ModelOwner():
    def __init__(self, workspace_name, model_name):
        self.workspace_name = workspace_name
        self.model_name = model_name
        self.aggregator = None
        self.collaborators = []
        self.workspace_path = None
        self.plan_path = None
        self.no_of_collaborators = constants.NO_OF_COLLABORATORS
        self.rounds_to_train = constants.NO_OF_ROUNDS

    def create_workspace(self, results_dir=None):
        try:
            results_dir = results_dir if results_dir else os.getcwd()
            sh.run_command(f"fx workspace create --prefix {self.workspace_name} --template {self.model_name}", work_dir=results_dir)
            log.info(f"Created the workspace {self.workspace_name} for the {self.model_name} model")
            self.workspace_path = os.path.join(results_dir, self.workspace_name)
            log.info(f"Workspace path: {self.workspace_path}")
        except Exception as e:
            log.error(f"Failed to create the workspace: {e}")
            raise e
        return self.workspace_path

    def modify_plan(self, new_rounds=None, no_of_collaborators=None):
        self.plan_path = os.join(self.workspace_path, "plan", "plan.yaml")
        log.info(f"Modifying the plan at {self.plan_path}")
        # Open the file and modify the entries
        self.rounds_to_train = new_rounds if new_rounds else self.rounds_to_train
        self.no_of_collaborators = no_of_collaborators if no_of_collaborators else self.no_of_collaborators

        log.info(f"Modified the plan to train the model for {self.rounds} rounds")
        return True

    def initialize_plan(self, agg_domain_name):
        try:
            sh.run_command(f"fx plan initialize -a {agg_domain_name}", work_dir=self.workspace_path)
            log.info(f"Initialized the plan for the workspace {self.workspace_name} on {agg_domain_name}")
        except Exception as e:
            log.error(f"Failed to initialize the plan: {e}")
            raise e
        return True

    def certify_workspace(self):
        try:
            sh.run_command("fx workspace certify", work_dir=self.workspace_path)
            log.info(f"Certified the workspace {self.workspace_name}")
        except Exception as e:
            log.error(f"Failed to certify the workspace: {e}")
            raise e
        return True

    def export_workspace(self):
        try:
            sh.run_command("fx workspace export", work_dir=self.workspace_path)
            log.info(f"Exported the workspace")
        except Exception as e:
            log.error(f"Failed to export the workspace: {e}")
            raise e
        return True

    def import_workspace(self, workspace_zip):
        try:
            sh.run_command(f"fx workspace import --archive {workspace_zip}", work_dir=self.workspace_path)
            log.info(f"Imported the workspace")
        except Exception as e:
            log.error(f"Failed to import the workspace: {e}")
            raise e
        return True
