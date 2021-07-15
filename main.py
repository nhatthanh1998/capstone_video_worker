import sys
import os
from dotenv import load_dotenv
from src.workers.generator import GeneratorWorker
import argparse
import requests
import json


load_dotenv()
QUEUE_HOST = os.environ.get("QUEUE_HOST")
MAIN_SERVER_ENDPOINT = os.environ.get("MAIN_SERVER_ENDPOINT")
parser = argparse.ArgumentParser()

parser.add_argument("--styleID", type=str, help="styleID that the model belong to", default='', required=True)
params = parser.parse_args()
styleID = params.styleID


if len(styleID) == 0:
    raise ValueError("StyleID must be filled!!!")
else:
    if __name__ == '__main__':
        try:
            response = requests.get(f"{MAIN_SERVER_ENDPOINT}/styles/{styleID}/active-model")
            data = json.loads(response.content.decode('utf-8'))
            routing_key = data.get("routingKey")
            modelType = data.get("modelType")
            snapshot_path = data.get("snapshotPath")
            generator_worker = GeneratorWorker(
                queue_host=QUEUE_HOST,
                snapshot_path=snapshot_path,
                main_server_endpoint=MAIN_SERVER_ENDPOINT
            )
            generator_worker.start_task()
        except KeyboardInterrupt:
            print('Interrupted')
            try:
                sys.exit(0)
            except SystemExit:
                sys.exit(0)
