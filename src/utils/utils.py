import uuid

import torch
from torchvision.transforms import transforms
from dotenv import load_dotenv
import os
import json
import boto3
import io
from torchvision.utils import make_grid
from PIL import Image
import cv2
import math
from torchvision.utils import save_image
import urllib
import shutil

load_dotenv()
ENV = os.environ.get("ENV", "dev")
S3_BUCKET_TEMPORARY = os.environ.get("S3_BUCKET_TEMPORARY")


def mkdir(path):
    print("mkdir.......")
    os.makedirs(path, exist_ok=True)


def init_s3_bucket(env, bucket):
    if env == "production":
        s3_client = boto3.client('s3')
    else:
        AWS_PUBLIC_KEY = os.environ.get("AWS_PUBLIC_KEY")
        AWS_PRIVATE_KEY = os.environ.get("AWS_PRIVATE_KEY")
        session = boto3.Session(
            aws_access_key_id=AWS_PUBLIC_KEY,
            aws_secret_access_key=AWS_PRIVATE_KEY
        )
        s3_client = session.client('s3')

    region = s3_client.get_bucket_location(Bucket=bucket)['LocationConstraint']

    return s3_client, region


s3, S3_REGION = init_s3_bucket(bucket=S3_BUCKET_TEMPORARY, env=ENV)


def load_model(path, generator, device):
    generator.load_state_dict(torch.hub.load_state_dict_from_url(path, map_location=torch.device(device)))
    return generator


def transform():
    """ Transforms for training images """
    transform_ = transforms.Compose(
        [
            transforms.ToTensor()
        ]
    )
    return transform_


def transform_tensor_to_bytes(tensor):
    grid = make_grid(tensor)
    ndarr = grid.mul(255).add_(0.5).clamp_(0, 255).permute(1, 2, 0).to('cpu', torch.uint8).numpy()
    img = Image.fromarray(ndarr)
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    return img_byte_arr.getvalue()


def transform_byte_to_object(byte_data):
    response = byte_data.decode('utf8')
    response = json.loads(response)
    return response


def get_s3_location(key):
    return f'https://s3-{S3_REGION}.amazonaws.com/{S3_BUCKET_TEMPORARY}/{key}'


def save_folder_to_s3(upload_dir, folder_name):
    files = os.listdir(upload_dir)
    for file_name in files:
        s3.upload_file(f"{upload_dir}/{file_name}", S3_BUCKET_TEMPORARY, f"{folder_name}/{file_name}")


def add_audio_to_transfer_video(original_video_path, transfer_video_path, output_path):
    rs = os.popen(
        f'bash src/scripts/combine_video_audio.sh {transfer_video_path} {original_video_path} {output_path}').close()


def convert_to_hls_stream(video_path, output_dir):
    rs = os.popen(f'bash src/scripts/convert_to_hls_stream.sh {video_path} {output_dir}').close()


def convert_video_to_frames(video_path, frame_dir):
    mkdir(frame_dir)
    capture_video = cv2.VideoCapture(video_path)
    fps = math.ceil(capture_video.get(cv2.CAP_PROP_FPS))
    success, frame = capture_video.read()
    total_frame = 1
    while success:
        capture_video.set(cv2.CAP_PROP_POS_MSEC, (total_frame * 1000 / fps))
        cv2.imwrite(frame_dir + "/frame_%d.jpg" % total_frame, frame)
        success, frame = capture_video.read()
        total_frame += 1
    return total_frame, fps


def convert_frame_to_video(frame_dir, output_path, total_frames, fps):
    img = cv2.imread(frame_dir + '/frame_1.jpg')
    height, width, layers = img.shape
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    for i in range(1, total_frames):
        print(frame_dir + '/frame_' + str(i) + '.jpg')
        video.write(cv2.imread(frame_dir + '/frame_' + str(i) + '.jpg'))
    cv2.destroyAllWindows()
    print("convert done:", output_path)
    video.release()


def apply_style_to_frame(device, generator, transform_func, frame_dir, frame_name, output_dir):
    if frame_name.endswith('.jpg'):
        frame_path = f"{frame_dir}/{frame_name}"
        tensor = transform_func(Image.open(frame_path)).unsqueeze(0).to(device)
        tensor = generator(tensor)
        save_image(tensor, f"{output_dir}/{frame_name}")

def download_video_file(video_url, save_path):
    urllib.request.urlretrieve(video_url, save_path)


def apply_style_to_video(video_path, generator, device, transform_func, save_location):
    frame_dir = f"src/process/{uuid.uuid4()}"
    transfer_dir = f"src/process/{uuid.uuid4()}"
    output_dir = f"src/process/{uuid.uuid4()}"
    mkdir("src/process")
    mkdir(frame_dir)
    mkdir(transfer_dir)
    mkdir(output_dir)    
    
    print("Download video....")
    download_video_file(video_path, "src/process/original.mp4")

    print("Convert original video to frame....")
    total_frames, fps = convert_video_to_frames("src/process/original.mp4", frame_dir)

    print("Apply style to frame ....")
    files = os.listdir(frame_dir)
    for file_name in files:
        apply_style_to_frame(device, generator, transform_func, frame_dir, file_name, transfer_dir)

    print("Convert frame to video ....")
    convert_frame_to_video(transfer_dir, "src/process/transfer.mp4", total_frames=total_frames, fps=fps)

    print("Add audio to video ....")
    add_audio_to_transfer_video(video_path, "src/process/transfer.mp4", f"{output_dir}/output.mp4")

    print("Convert video to HLS stream format....")
    # convert_to_hls_stream(f"{output_dir}/output.mp4", output_dir)

    print("Save to s3")
    # save_folder_to_s3(output_dir, save_location)

    print("Delete material")
    # shutil.rmtree("src/process")

    print("Done")


    

