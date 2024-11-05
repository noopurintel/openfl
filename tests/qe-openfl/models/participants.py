# Copyright 2020-2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import os
import utils.constants as constants
from utils.logger import logger as log
import utils.subprocess_helper as sh

# Define the Aggregator class
class Aggregator():
    def __init__(self, agg_domain_name, workspace_path=None):
        self.agg_domain_name = agg_domain_name
        self.workspace_path = workspace_path

    def generate_sign_request(self, agg_domain_name):
        log.info(f"Generated a sign request for the aggregator {agg_domain_name}")
        try:
            sh.run_command(f"fx aggregator generate-cert-request --fqdn {agg_domain_name}", work_dir=self.workspace_path)
        except Exception as e:
            log.error(f"Failed to generate the sign request: {e}")
            raise e
    
    def sign_collaborator_csr(self, collaborator_name):
        try:
            zip_name = f"col_{self.collaborator_name}_to_agg_cert_request.zip"
            col_zip = os.path.join(self.workspace_path, zip_name)
            sh.run_command(f"fx collaborator certify --request-pkg {col_zip} -s", work_dir=self.workspace_path)
            log.info(f"Signed the CSR for the collaborator {collaborator_name} with zip name {zip_name}")
        except Exception as e:
            log.error(f"Failed to sign the CSR: {e}")
            raise e
    
    def start(self):
        try:
            sh.run_command("fx aggregator start", work_dir=self.workspace_path)
            log.info(f"Started the aggregator {self.agg_domain_name}")
        except Exception as e:
            log.error(f"Failed to start the aggregator: {e}")
            raise e


# Define the Collaborator class
class Collaborator():
    def __init__(self, collaborator_name=None, data_directory_path=None, workspace_path=None):
        self.collaborator_name = collaborator_name
        self.data_directory_path = data_directory_path
        self.workspace_path = workspace_path

    def generate_sign_request(self, collaborator_name):
        try:
            sh.run_command(f"fx collaborator generate-cert-request -n {collaborator_name}", work_dir=self.workspace_path)
            log.info(f"Generated a sign request for the collaborator {collaborator_name}")
        except Exception as e:
            log.error(f"Failed to generate the sign request: {e}")
            raise e
    
    def create_collaborator(self):
        try:
            sh.run_command(f"fx collaborator create -n {self.collaborator_name} -d {self.data_directory_path}", work_dir=self.workspace_path)
            log.info(f"Created the collaborator {self.collaborator_name} with the data directory {self.data_directory_path}")
        except Exception as e:
            log.error(f"Failed to create the collaborator: {e}")
            raise e
    
    def import_certify_csr(self):
        try:
            zip_name = f"agg_to_col_{self.collaborator_name}_signed_cert.zip"
            col_zip = os.path.join(self.workspace_path, zip_name)
            sh.run_command(f"fx collaborator certify --import {col_zip}", work_dir=self.workspace_path)
            log.info(f"Imported and certified the CSR for the collaborator {self.collaborator_name} with zip name {zip_name}")
        except Exception as e:
            log.error(f"Failed to import and certify the CSR: {e}")
            raise e

    def start(self):
        try:
            sh.run_command(f"fx collaborator start -n {self.collaborator_name}", work_dir=self.workspace_path)
            log.info(f"Started the collaborator {self.collaborator_name}")
        except Exception as e:
            log.error(f"Failed to start the collaborator: {e}")
            raise e

# Define the Facilitator class
class Facilitator():
    def __init__(self, workspace_name, model_name):
        self.workspace_name = workspace_name
        self.model_name = model_name
        self.aggregator = None
        self.collaborators = []
        self.workspace_path = None
        self.plan_path = None
        self.no_of_collaborators = constants.NO_OF_COLLABORATORS
        self.rounds_to_train = constants.NO_OF_ROUNDS

    def create_workspace(self):
        try:
            sh.run_command(f"fx workspace create --prefix {self.workspace_name} --template {self.model_name}", work_dir=self.workspace_path)
            log.info(f"Created the workspace {self.workspace_name} for the {self.model_name} model")
            self.workspace_path = os.path.join(os.getcwd(), self.workspace_name)
            log.info(f"Workspace path: {self.workspace_path}")
            return self.workspace_path
        except Exception as e:
            log.error(f"Failed to create the workspace: {e}")
            raise e

    def modify_plan(self, new_rounds=None, no_of_collaborators=None):
        self.plan_path = os.join(self.workspace_path, "plan", "plan.yaml")
        log.info(f"Modifying the plan at {self.plan_path}")
        # Open the file and modify the entries
        self.rounds_to_train = new_rounds if new_rounds else self.rounds_to_train
        self.no_of_collaborators = no_of_collaborators if no_of_collaborators else self.no_of_collaborators

        log.info(f"Modified the plan to train the model for {self.rounds} rounds")

    def initialize_plan(self, agg_domain_name):
        try:
            sh.run_command(f"fx plan initialize -a {agg_domain_name}", work_dir=self.workspace_path)
            log.info(f"Initialized the plan for the workspace {self.workspace_name} on the aggregator {agg_domain_name}")
        except Exception as e:
            log.error(f"Failed to initialize the plan: {e}")
            raise e

    def certify_workspace(self):
        try:
            sh.run_command("fx workspace certify", work_dir=self.workspace_path)
            log.info(f"Certified the workspace {self.workspace_name}")
        except Exception as e:
            log.error(f"Failed to certify the workspace: {e}")
            raise e

    def export_workspace(self):
        try:
            sh.run_command("fx workspace export", work_dir=self.workspace_path)
            log.info(f"Exported the workspace")
        except Exception as e:
            log.error(f"Failed to export the workspace: {e}")
            raise e

    def import_workspace(self, workspace_zip):
        try:
            sh.run_command(f"fx workspace import --archive {workspace_zip}", work_dir=self.workspace_path)
            log.info(f"Imported the workspace")
        except Exception as e:
            log.error(f"Failed to import the workspace: {e}")
            raise e
