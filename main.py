import subprocess
import shutil
import os
import uuid

from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


app = FastAPI()

# Allow frontend JS to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "tmp/ffstudio"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount static files (css, js, images, etc.)
app.mount("/static", StaticFiles(directory="public"), name="static")


# Serve index.html at root
@app.get("/")
async def read_index():
    return FileResponse(os.path.join("public", "index.html"))


def run_ffmpeg(cmd):
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        return JSONResponse({"error": e.stderr.decode()}, status_code=500)
    return None


@app.post("/cut-mp3")
async def cut_mp3(
    file: UploadFile,
    start: str = Form(...),  # format: "00:00:10"
    duration: str = Form(...),  # format: "00:00:20"
):
    # Save input file temporarily
    input_path = f"temp_{uuid.uuid4().hex}.mp3"
    output_path = f"cut_{uuid.uuid4().hex}.mp3"

    with open(input_path, "wb") as f:
        f.write(await file.read())

    # Run ffmpeg command to trim audio
    command = [
        "ffmpeg",
        "-i",
        input_path,
        "-ss",
        start,
        "-t",
        duration,
        "-acodec",
        "copy",
        output_path,
    ]

    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Cleanup input file
    os.remove(input_path)

    # Return trimmed file
    return FileResponse(output_path, media_type="audio/mpeg", filename="trimmed.mp3")


@app.post("/crop")
async def crop_video(
    file: UploadFile,
    x: int = Form(...),
    y: int = Form(...),
    w: int = Form(...),
    h: int = Form(...),
):
    input_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
    with open(input_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    output_path = input_path.replace(".mp4", "_cropped.mp4")

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-filter:v",
        f"crop={w}:{h}:{x}:{y}",
        "-c:a",
        "copy",
        output_path,
    ]
    error = run_ffmpeg(cmd)
    if error:
        return error

    return FileResponse(output_path, media_type="video/mp4", filename="output.mp4")


@app.post("/trim")
async def trim_video(
    file: UploadFile,
    start: str = Form(...),  # e.g. "00:00:10"
    end: str = Form(...),  # e.g. "00:00:20"
):
    input_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
    with open(input_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    output_path = input_path.replace(".mp4", "_trimmed.mp4")
    cmd = f"ffmpeg -y -i {input_path} -ss {start} -to {end} -c copy {output_path}"

    error = run_ffmpeg(cmd.split())
    if error:
        return error

    return FileResponse(output_path, media_type="video/mp4", filename="output.mp4")


@app.post("/replace-audio")
async def replace_audio(video: UploadFile, audio: UploadFile):
    video_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{video.filename}")
    audio_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{audio.filename}")

    with open(video_path, "wb") as f:
        shutil.copyfileobj(video.file, f)
    with open(audio_path, "wb") as f:
        shutil.copyfileobj(audio.file, f)

    output_path = video_path.replace(".mp4", "_newaudio.mp4")
    cmd = f"ffmpeg -y -i {video_path} -i {audio_path} -map 0:v -map 1:a -c:v copy -shortest {output_path}"

    error = run_ffmpeg(cmd.split())
    if error:
        return error

    return FileResponse(output_path, media_type="video/mp4", filename="output.mp4")


@app.post("/image-audio")
async def image_audio(image: UploadFile, audio: UploadFile):
    image_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{image.filename}")
    audio_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{audio.filename}")

    with open(image_path, "wb") as f:
        shutil.copyfileobj(image.file, f)
    with open(audio_path, "wb") as f:
        shutil.copyfileobj(audio.file, f)

    output_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_slideshow.mp4")
    cmd = f"ffmpeg -y -loop 1 -i {image_path} -i {audio_path} -c:v libx264 -tune stillimage -c:a aac -b:a 192k -pix_fmt yuv420p -shortest {output_path}"

    error = run_ffmpeg(cmd.split())
    if error:
        return error

    return FileResponse(output_path, media_type="video/mp4", filename="output.mp4")
