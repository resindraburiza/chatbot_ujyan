#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os

class DefaultConfig:
    """ Bot Configuration """

    PORT = 3978
    APP_ID = os.environ.get("MicrosoftAppId", "")
    APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "")

    APP_ID_DEPLOY = '0cbc76f7-7128-4ec7-bb2a-fd9427398088'
    APP_PASSWORD_DEPLOY = 'aac364bd-32ca-4484-ab4f-7ecc92a22f7b'
