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

#set up packages
ln -s /dev/null /tmp/null.mp4
pip install flask --ignore-installed
pip install ./mmj_utils/
pip install ./nanoowl/

if ! test -f nanoowl/data/owl_image_encoder_patch32.engine; then
    echo "Building owl encoder engine"
    mkdir nanoowl/data
    python3 -m "nanoowl.build_image_encoder_engine" "nanoowl/data/owl_image_encoder_patch32.engine"
fi
echo "Done"