from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import JSONResponse
import requests
import time
import re

app = FastAPI()

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type"
}

@app.options("/{path:path}")
async def options_handler(path: str):
    return JSONResponse(content=None, headers=CORS_HEADERS)

@app.post("/pdf")
async def handle_pdf(request: Request, pdf: UploadFile = File(None)):
    try:
        if request.method != "POST":
            return json_response(
                {"success": False, "message": "Only POST requests are allowed"},
                405
            )

        if not pdf:
            return json_response(
                {"success": False, "message": "PDF file required"},
                400
            )

        timestamp = int(time.time() * 1000)
        filename = f"pdf_{timestamp}.pdf"

        uploaded_url = upload_to_tmpfiles(pdf, filename)

        text = extract_text_from_pdf(uploaded_url)

        return json_response(
            {"success": True, "text": text},
            200
        )

    except Exception as e:
        return json_response(
            {"success": False, "message": str(e) or "Error processing PDF"},
            400
        )

def upload_to_tmpfiles(pdf: UploadFile, filename: str) -> str:
    files = {
        "file": (filename, pdf.file, "application/pdf")
    }

    response = requests.post(
        "https://tmpfiles.org/api/v1/upload",
        files=files,
        timeout=60
    )

    if response.status_code != 200:
        raise Exception("Failed to upload PDF")

    data = response.json()

    if "data" not in data or "url" not in data["data"]:
        raise Exception("No upload URL received")

    normal_url = data["data"]["url"]

    match = re.search(r"/(\d+)/", normal_url)
    if not match:
        raise Exception("Invalid upload URL format")

    file_id = match.group(1)

    return f"https://tmpfiles.org/dl/{file_id}/{filename}"

def extract_text_from_pdf(pdf_url: str) -> str:
    response = requests.post(
        "https://api.kome.ai/api/tools/pdf-to-text",
        json={"url": pdf_url},
        headers={"Content-Type": "application/json"},
        timeout=60
    )

    if response.status_code != 200:
        raise Exception("Failed to extract text from PDF")

    data = response.json()

    if "text" not in data:
        raise Exception("No text extracted from PDF")

    return data["text"]

def json_response(data: dict, status: int = 200, extra_headers: dict = None):
    headers = {
        "Content-Type": "application/json",
        **CORS_HEADERS
    }
    if extra_headers:
        headers.update(extra_headers)

    return JSONResponse(
        content=data,
        status_code=status,
        headers=headers
    )