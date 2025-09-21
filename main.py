import subprocess
import shutil
import os
import uuid
import shlex

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.concurrency import run_in_threadpool
from starlette.background import BackgroundTask

ALLOWED_EXTENSIONS = {
    "audio": [".mp3", ".wav", ".aac", ".m4a"],
    "video": [".mp4", ".mov", ".mkv", ".avi"],
    "image": [".jpg", ".jpeg", ".png"],
}

MAX_SIZE = 50_000_000  # 50 MB limit
UPLOAD_DIR = "tmp/ffstudio"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def validate_file(filename: str, category: str):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS.get(category, []):
        raise ValueError(f"Invalid {category} file type: {ext}")


app = FastAPI()

# Allow frontend JS to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def run_ffmpeg(cmd):
    try:
        await run_in_threadpool(subprocess.run, cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(e)
        print(e.stderr.decode())
        return JSONResponse({"error": e.stderr.decode()}, status_code=500)
    return None


def cleanup(files):
    for file in files:
        try:
            os.remove(file)
        except FileNotFoundError:
            pass


@app.post("/api/cut-mp3")
async def cut_mp3(
    file: UploadFile = File(..., max_size=MAX_SIZE),
    start: str = Form(...),  # format: "00:00:10"
    duration: str = Form(...),  # format: "00:00:20"
):
    try:
        validate_file(file.filename, "audio")
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    input_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
    with open(input_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    output_path = input_path.replace(".mp3", "_cut.mp3")

    cmd = [
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

    error = await run_ffmpeg(cmd)
    if error:
        return JSONResponse({"error": "Processing failed"}, status_code=500)

    files = [input_path, output_path]
    return FileResponse(
        output_path,
        media_type="audio/mpeg",
        filename="trimmed.mp3",
        background=BackgroundTask(lambda: cleanup(files)),
    )


@app.post("/api/crop-video")
async def crop_video(
    file: UploadFile = File(..., max_size=MAX_SIZE),
    x: int = Form(...),
    y: int = Form(...),
    w: int = Form(...),
    h: int = Form(...),
):
    try:
        validate_file(file.filename, "video")
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    video_ext = os.path.splitext(file.filename)[1] or ".mp4"
    video_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{video_ext}")
    with open(video_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    output_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_cropped.mp4")

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-filter:v",
        f"crop={w}:{h}:{x}:{y}",
        "-c:a",
        "copy",
        output_path,
    ]
    error = await run_ffmpeg(cmd)
    if error:
        return JSONResponse({"error": "Processing failed"}, status_code=500)

    files = [video_path, output_path]
    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename="output.mp4",
        background=BackgroundTask(lambda: cleanup(files)),
    )


@app.post("/api/trim")
async def trim_video(
    file: UploadFile = File(..., max_size=MAX_SIZE),
    start: str = Form(...),  # e.g. "00:00:10"
    end: str = Form(...),  # e.g. "00:00:20"
):
    try:
        validate_file(file.filename, "video")
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    input_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
    with open(input_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    output_path = input_path.replace(".mp4", "_trimmed.mp4")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-ss",
        str(start),
        "-to",
        str(end),
        "-c",
        "copy",
        output_path,
    ]

    error = await run_ffmpeg(cmd)

    if error:
        return JSONResponse({"error": "Processing failed"}, status_code=500)

    files = [input_path, output_path]
    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename="output.mp4",
        background=BackgroundTask(lambda: cleanup(files)),
    )


@app.post("/api/replace-audio")
async def replace_audio(
    video: UploadFile = File(..., max_size=MAX_SIZE),
    audio: UploadFile = File(..., max_size=MAX_SIZE),
):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    try:
        validate_file(video.filename, "video")
        validate_file(audio.filename, "audio")
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    # Save video & audio
    video_ext = os.path.splitext(video.filename)[1] or ".mp4"
    video_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{video_ext}")
    with open(video_path, "wb") as f:
        shutil.copyfileobj(video.file, f)

    audio_ext = os.path.splitext(audio.filename)[1] or ".mp3"
    audio_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{audio_ext}")
    with open(audio_path, "wb") as f:
        shutil.copyfileobj(audio.file, f)

    output_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_replaced.mp4")

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-i",
        audio_path,
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-c:v",
        "copy",
        "-shortest",
        output_path,
    ]

    error = await run_ffmpeg(cmd)
    if error:
        return JSONResponse({"error": "Processing failed"}, status_code=500)

    files = [video_path, audio_path, output_path]
    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename="output.mp4",
        background=BackgroundTask(lambda: cleanup(files)),
    )


@app.post("/api/image-audio")
async def image_audio(
    image: UploadFile = File(..., max_size=MAX_SIZE),
    audio: UploadFile = File(..., max_size=MAX_SIZE),
):
    try:
        validate_file(image.filename, "image")
        validate_file(audio.filename, "audio")
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    image_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{image.filename}")
    audio_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{audio.filename}")

    with open(image_path, "wb") as f:
        shutil.copyfileobj(image.file, f)

    with open(audio_path, "wb") as f:
        shutil.copyfileobj(audio.file, f)

    scaled_image_path = os.path.join(
        UPLOAD_DIR, f"{uuid.uuid4()}_scaled_{image.filename}"
    )
    image_resize_cmd = [
        "ffmpeg",
        "-i",
        image_path,
        "-vf",
        "scale=1080:-2",
        scaled_image_path,
    ]
    error = await run_ffmpeg(image_resize_cmd)
    if error:
        return JSONResponse({"error": "Processing failed"}, status_code=500)

    output_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_slideshow.mp4")
    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        scaled_image_path,
        "-i",
        audio_path,
        "-c:v",
        "libx264",
        "-tune",
        "stillimage",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-preset",
        "ultrafast",
        "-shortest",
        output_path,
    ]

    error = await run_ffmpeg(cmd)
    if error:
        return JSONResponse({"error": "Processing failed"}, status_code=500)

    files = [image_path, scaled_image_path, audio_path, output_path]
    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename="output.mp4",
        background=BackgroundTask(lambda: cleanup(files)),
    )


app.mount("/", StaticFiles(directory="public", html=True), name="frontend")
