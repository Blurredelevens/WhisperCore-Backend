import base64
import json
import logging
import os

from flask import Response, current_app, jsonify, send_file, stream_with_context
from werkzeug.utils import secure_filename

from services.s3_service import s3_service

logger = logging.getLogger(__name__)


def upload_image(file, folder, filename=None, user_id=None, memory_id=None):
    """
    Uploads an image to S3 or local storage and returns (image_base64, image_path).
    """
    if not file or not file.filename:
        return None, None

    try:
        logger.info(f"Starting image upload for folder: {folder}, user_id: {user_id}, memory_id: {memory_id}")

        image_bytes = file.read()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        logger.info(f"Image encoded to base64, size: {len(image_base64)} characters")

        if s3_service.is_enabled():
            logger.info("Using S3 for image storage")
            if folder == "users":
                s3_url = s3_service.upload_user_image(file, user_id)
            else:
                s3_url = s3_service.upload_memory_image(file, memory_id, user_id)
            if s3_url:
                image_path = s3_url
                logger.info(f"Image uploaded to S3: {s3_url}")
            else:
                # S3 upload failed, fallback to local
                logger.warning("S3 upload failed, falling back to local storage")
                filename = filename or secure_filename(file.filename)
                upload_folder = os.path.join(current_app.root_path, "uploads", folder)
                os.makedirs(upload_folder, exist_ok=True)
                file_path = os.path.join(upload_folder, filename)
                with open(file_path, "wb") as f:
                    f.write(image_bytes)
                image_path = file_path
                logger.info(f"Image saved locally: {file_path}")
        else:
            logger.info("Using local storage for image")
            filename = filename or secure_filename(file.filename)
            upload_folder = os.path.join(current_app.root_path, "uploads", folder)
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, filename)
            with open(file_path, "wb") as f:
                f.write(image_bytes)
            image_path = file_path
            logger.info(f"Image saved locally: {file_path}")

        logger.info("Image upload completed successfully")
        return image_base64, image_path

    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        return None, None


def upload_image_with_progress(file, folder, filename=None, user_id=None, memory_id=None):
    """
    Uploads an image with progress streaming for real-time feedback.

    Returns:
        Generator that yields progress updates
    """
    if not file or not file.filename:
        yield {"status": "error", "message": "No file provided"}
        return

    try:
        yield {"status": "started", "message": "Starting image upload..."}

        # Read file
        image_bytes = file.read()
        yield {"status": "reading", "message": "File read successfully", "size": len(image_bytes)}

        # Encode to base64
        base64.b64encode(image_bytes).decode("utf-8")
        yield {"status": "encoded", "message": "Image encoded to base64"}

        # Upload to storage
        if s3_service.is_enabled():
            yield {"status": "uploading", "message": "Uploading to S3..."}
            if folder == "users":
                s3_url = s3_service.upload_user_image(file, user_id)
            else:
                s3_url = s3_service.upload_memory_image(file, memory_id, user_id)

            if s3_url:
                yield {"status": "completed", "message": "Uploaded to S3", "path": s3_url}
            else:
                yield {"status": "fallback", "message": "S3 failed, using local storage..."}
                # Fallback to local storage
            filename = filename or secure_filename(file.filename)
            upload_folder = os.path.join(current_app.root_path, "uploads", folder)
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, filename)
            with open(file_path, "wb") as f:
                f.write(image_bytes)
            yield {"status": "completed", "message": "Saved locally", "path": file_path}
        else:
            yield {"status": "uploading", "message": "Saving to local storage..."}
            filename = filename or secure_filename(file.filename)
            upload_folder = os.path.join(current_app.root_path, "uploads", folder)
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, filename)
            with open(file_path, "wb") as f:
                f.write(image_bytes)
            yield {"status": "completed", "message": "Saved locally", "path": file_path}

    except Exception as e:
        logger.error(f"Error in streaming image upload: {e}")
        yield {"status": "error", "message": f"Upload failed: {str(e)}"}


def get_image_response(image_path):
    """
    Returns a Flask response for downloading an image.
    """
    if not image_path:
        return jsonify({"error": "No image found"}), 404
    if image_path.startswith("https://"):
        return jsonify({"image_url": image_path}), 200
    return send_file(image_path, mimetype="image/jpeg")


def stream_image_upload(file, folder, filename=None, user_id=None, memory_id=None):
    """
    Stream image upload progress for real-time feedback.

    Returns:
        Flask Response with Server-Sent Events
    """

    def generate_progress():
        for progress in upload_image_with_progress(file, folder, filename, user_id, memory_id):
            yield f"data: {json.dumps(progress)}\n\n"

    return Response(
        stream_with_context(generate_progress()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
        },
    )
