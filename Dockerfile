FROM python:3.12

WORKDIR /code

COPY ./requirements.txt requirements.txt

RUN apt update && apt install ffmpeg -y
RUN apt install --reinstall libexpat1 -y
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["fastapi", "run", "main.py", "--port", "8080", "--workers", "4"]