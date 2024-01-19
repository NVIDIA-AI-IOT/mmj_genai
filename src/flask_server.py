# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#Setup endpoint that can be used to update the prompt 
from threading import Thread 
from flask import Flask, request
import json 
class FlaskServer:

    def __init__(self,out_q, port=5000):
        self.out_q = out_q
        self.app = Flask(__name__)
        self.app.add_url_rule('/prompt', 'update_prompt', self.update_prompt)
        self.port=port

    def update_prompt(self):
        self.out_q.put(request.args)
        return f"{json.dumps(request.args, indent=4)}"

    def _start_flask(self):
        self.app.run(use_reloader=False, host='0.0.0.0', port=self.port)

    def start_flask(self):
        self.flask_thread = Thread(target=self._start_flask, daemon=True)
        self.flask_thread.start()

