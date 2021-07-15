FROM python:3

WORKDIR /usr/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src ./src
COPY main.py ./
COPY .env ./
CMD [ "python", "main.py", "--styleID", "d3e15e7d-bd7e-464f-a88b-3f1573113923"]