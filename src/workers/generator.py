import torch
from PIL import Image
from src.models.generator import Generator
import requests
from src.utils.utils import load_model, transform, transform_byte_to_object, \
    transform_tensor_to_bytes, apply_style_to_video
import uuid
import pika
import datetime;

class GeneratorWorker:
    def __init__(self, 
                 queue_host,
                 snapshot_path,
                 main_server_endpoint):
        self.frame_dir = None
        self.fps = 0
        self.total_frames = 0

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.queue_host = queue_host
        self.main_server_endpoint = main_server_endpoint
        self.snapshot_path = snapshot_path

        self.generator = Generator().to(self.device)
        self.transform_ = transform()
        self.generator = load_model(path=self.snapshot_path, generator=self.generator, device=self.device)
        self.connection = pika.BlockingConnection(pika.URLParameters(self.queue_host))
        self.channel = self.connection.channel()

    def upload_model(self, snapshot_location):
        self.generator = load_model(path=snapshot_location, generator=self.generator, device=self.device)

    def preprocess(self, video_location):
        print("Preprocess")

    def inference(self, model_input):
        return self.generator(model_input)[0]

    def post_process(self, user_id, save_location, save_album_id, style_id):
        endpoint_url = f"{self.main_server_endpoint}/medias/transfer-video/completed"
        payload = {
            'saveLocation': save_location,
            'userId': user_id,
            'saveAlbumId': save_album_id,
            'styleId': style_id,
        }
        requests.post(endpoint_url, data=payload)
        torch.cuda.empty_cache()

    def handler(self, ch, method, video_location, style_id, user_id, save_album_id):
        # 1. Preprocess
        # model_input = self.preprocess(photo_access_url=photo_access_url)

        # # 2. Transform
        # model_output = self.inference(model_input=model_input)

        # # 3. Post process
        # self.post_process(model_output=model_output, image_name=image_name, socketId=socketId, style_id=style_id)

        # # 4. Ack the processed message.
        # ch.basic_ack(delivery_tag=method.delivery_tag)
        print("Receive")
        print(video_location)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        timestamp = str(int(datetime.datetime.now().timestamp()))
        save_location = f'{user_id}/{timestamp}'
        apply_style_to_video(video_location, self.generator, self.device, self.transform_, save_location)
        self.post_process(user_id=user_id, save_location=save_location, save_album_id=save_album_id, style_id=style_id)


    def process_transfer_photo_task(self, ch, method, properties, body):
        print("Transfer photo task on process...")
        data = transform_byte_to_object(body)
        style_id = data['styleId']
        video_location = data['videoLocation']
        user_id = data['userId']
        save_album_id = data['saveAlbumId']
        # Put data to model process pipeline
        self.handler(ch=ch, method=method, video_location=video_location, style_id=style_id, user_id=user_id, save_album_id=save_album_id)

    def process_update_model_task(self, ch, method, properties, body):
        print("Start update model....")
        body = transform_byte_to_object(body)
        data = body['data']
        snapshot_location = data['snapshotLocation']
        self.upload_model(snapshot_location)

    def declare_transfer_photo_workflow(self):
        self.channel.queue_declare("TRANSFER_VIDEO_QUEUE", durable=True)
        self.channel.exchange_declare(exchange="EXCHANGE_TRANSFER_VIDEO", exchange_type='direct')
        self.channel.queue_bind(exchange="EXCHANGE_TRANSFER_VIDEO", queue="TRANSFER_VIDEO_QUEUE", routing_key="")
        self.channel.basic_consume(queue="TRANSFER_VIDEO_QUEUE", on_message_callback=self.process_transfer_photo_task)
        print(f' [*] Hello isss')

    def declare_update_model_workflow(self):
        rs = self.channel.queue_declare(queue='', exclusive=True)
        queue_name = rs.method.queue
        self.channel.exchange_declare(exchange=self.exchange_update_model_name, exchange_type='fanout')
        self.channel.queue_bind(exchange=self.exchange_update_model_name, queue=queue_name, routing_key=self.routing_key)
        self.channel.basic_consume(queue=queue_name, on_message_callback=self.process_update_model_task)

    def start_task(self):
        self.declare_transfer_photo_workflow()
        # self.declare_update_model_workflow()
        self.channel.start_consuming()
