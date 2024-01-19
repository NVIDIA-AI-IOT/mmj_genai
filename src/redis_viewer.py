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

import redis 
from time import sleep 
import argparse


parser = argparse.ArgumentParser()
parser.add_argument("--redis_host", type=str, default="localhost", help="Host name of the redis server")
parser.add_argument("--redis_port", type=int, default=6379, help="Port number of the redist server")
parser.add_argument("--redis_stream", type=str, default='owl', help="Name of redis stream to send output metadata")
args = parser.parse_args()

redis_server = redis.Redis(host=args.redis_host, port=args.redis_port, decode_responses=True)

while True:
    l = redis_server.xread(count=10, block=5000, streams={args.redis_stream: '$'} )
    print(l)
