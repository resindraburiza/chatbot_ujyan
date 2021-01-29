#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os

class DefaultConfig:
    """ Bot Configuration """

    PORT = 3978
    APP_ID = os.environ.get("MicrosoftAppId", "")
    APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "")

    APP_ID_DEPLOY = 'bbf340f5-a48e-4a57-ba70-a0825e59202d'
    APP_PASSWORD_DEPLOY = 'aac364bd-32ca-4484-ab4f-7ecc92a22f7b'
