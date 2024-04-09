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

import argparse 
from queue import Queue
from time import sleep 

#nanoowl and jetson utils must be installed properly for these imports to work. Follow the setup.sh script. 
from nanoowl.owl_predictor import OwlPredictor
from jetson_utils import videoSource, videoOutput, cudaFromNumpy, cudaToNumpy
from mmj_utils.schema_gen import SchemaGenerator
from mmj_utils.overlay_gen import DetectionOverlayCUDA
from mmj_utils.vst import VST 

from flask_server import FlaskServer

#Helper function to process prompt inputs from flask 
def process_prompt(prompt):
    objects = prompt["objects"].split(",")
    objects = [x.strip() for x in objects]
    thresholds = prompt["thresholds"].split(",")
    thresholds = [float(x.strip()) for x in thresholds]
    return objects, thresholds 

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stream_input", type=str, default="", nargs='?', help="URI of an RTSP stream (rtsp://0.0.0.0:8554/stream) OR VST address (http://0.0.0.0:81)") #if not supplied, will get stream from VST. 
    parser.add_argument("--stream_output", type=str, default="rtsp://0.0.0.0:6000/out", nargs='?', help="URI of the output stream")
    parser.add_argument("--redis_host", type=str, default="0.0.0.0", help="Host name of the redis server")
    parser.add_argument("--redis_port", type=int, default=6379, help="Port number of the redist server")
    parser.add_argument("--redis_stream", type=str, default='owl', help="Name of redis stream to send output metadata")
    parser.add_argument("--objects", type=str, default="a person", help="example: a person, a box, a cone")
    parser.add_argument("--thresholds", type=str, default="0.1", help="example: 0.1,0.2,0.15")
    parser.add_argument("--flask_port", type=int, default=5000, help="Port for flask")
    parser.add_argument("--model", type=str, default="google/owlvit-base-patch32", help="Name of model to use")
    parser.add_argument("--image_encoder_engine", type=str, default="nanoowl/data/owl_image_encoder_patch32.engine", help="Path to trt encoder engine")
    args = parser.parse_args()

    #Launch flask server and connect queue to receive prompt updates 
    flask_queue = Queue() #hold prompts from flask input 
    flask = FlaskServer(flask_queue, port=args.flask_port)
    flask.start_flask()

    #load prompt queue with cmd line inputs 
    flask_queue.put({"objects":args.objects, "thresholds":args.thresholds})

    #Determine input stream
    stream_input = args.stream_input
    if stream_input[0:7] != "rtsp://": #If not a direct rtsp stream then grab stream from VST 
        vst_host = stream_input
        vst = VST(vst_host)
        print("Getting VST streams")
        vst_rtsp_streams = vst.get_rtsp_streams()
        print(vst_rtsp_streams)
        if len(vst_rtsp_streams) == 0:
            raise Exception("No valid input source. Provide a direct RTSP stream in the in stream_input argument or ensure VST has a valid RTSP stream.") #grab the first valid RTSP stream
        else:
            stream_input = vst_rtsp_streams[0]
    print(f"Using {stream_input} as rtsp input source")


    #Setup some mmj utilities 
    overlay_gen = DetectionOverlayCUDA(max_objects=5) #used to generate bounding box overlays 
    schema_gen = SchemaGenerator(sensor_id=stream_input.split("/")[-1], sensor_type="camera", sensor_loc=[10,20,30]) #used to generate metadata output in metropolis minimal schema format 
    schema_gen.connect_redis(args.redis_host, args.redis_port, args.redis_stream) #connect schema output to redis stream

    #Load GenAI model
    predictor = OwlPredictor(
        args.model,
        image_encoder_engine=args.image_encoder_engine
    )

    # create video input and output using jetson-utils 
    v_input = videoSource(stream_input, options={"latency":50, "codec":"h264"})
    v_output = videoOutput(args.stream_output, options={'save': '/tmp/null.mp4'})

    # add output stream to VST
    # vst.readd_rtsp_stream(args.stream_output, name="Detection Overlay") #will delete existing stream if already created and re add it. 

    #Get initial prompt from cmd line 
    objects, thresholds = process_prompt(flask_queue.get())
    objects_encoding = predictor.encode_text(objects)

    frame_counter = 0
    skip_counter = 0
    while(True):

        # capture the next image
        try:
            image = v_input.Capture()
        except Exception as e:
            skip_counter += 1
            print(e)
            print("Failed to capture input frame. Trying again")
            sleep(1/33)
            continue 


        #Get prompt updates from flask
        if not flask_queue.empty():
            objects, thresholds = process_prompt(flask_queue.get())
            objects_encoding = predictor.encode_text(objects)

        #Skip frame if none 
        if image is None:
            skip_counter+=1
            if skip_counter >= 30: #Track if stream is no longer working and quit. 
                raise Exception("Stream Capture not able to get frames.")
            continue  
        else:
            skip_counter = 0

        #Run model prediction
        output = predictor.predict(
            image=image, 
            text=objects, 
            text_encodings=objects_encoding,
            threshold=thresholds,
            pad_square=True
        )

        #Generate overlay and output
        text_labels = [objects[x] for x in output.labels]
        bboxes = output.boxes.tolist()
        image = overlay_gen(image, text_labels, bboxes) 
        v_output.Render(image)

        #Generate metadata in mmj schema and output on redis 
        if frame_counter % 60 == 0:
            schema_gen(text_labels, bboxes) 
      
        frame_counter+=1

        # exit on input/output EOS
        if not v_input.IsStreaming() or not v_output.IsStreaming():
            break
