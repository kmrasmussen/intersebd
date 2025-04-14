from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
import httpx
import json
import os
from datetime import datetime
import logging
import uvicorn
from typing import Optional, Dict, Any
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db, engine, Base
from models import RequestsLog

async def log_requests_middleware(request: Request, call_next):
    """
    Middleware to log requests with a valid x-intercept-key to the database,
    and others to files as a fallback.
    """
    start_time = datetime.now()
    intercept_key_str = request.headers.get("x-intercept-key")
    intercept_key_uuid = None
    is_key_valid = False

    # Validate UUID
    if intercept_key_str:
        try:
            intercept_key_uuid = uuid.UUID(intercept_key_str)
            is_key_valid = True
            print(f"Valid intercept key found: {intercept_key_uuid}")
        except ValueError:
            print(f"Invalid intercept key format: {intercept_key_str}")
            # Optionally raise HTTPException(400, "Invalid x-intercept-key format")
            # Or just proceed without DB logging

    # Read request body early for logging
    request_body_bytes = await request.body()
    request_body_json = None
    if request_body_bytes:
        try:
            request_body_json = json.loads(request_body_bytes)
        except json.JSONDecodeError:
            request_body_json = {"raw_content": request_body_bytes.decode('utf-8', errors='replace')}


    # Process the request
    response = await call_next(request)

    # Read response body
    response_body_bytes = b""
    async for chunk in response.body_iterator:
        response_body_bytes += chunk

    response_body_json = None
    if response_body_bytes:
        try:
            response_body_json = json.loads(response_body_bytes)
        except json.JSONDecodeError:
             response_body_json = {"raw_content": response_body_bytes.decode('utf-8', errors='replace')}


    # Log to Database if key is valid
    if is_key_valid:
        try:
            # Get a new DB session for this request
            async for session in get_db(): # Use the dependency
                log_entry = RequestsLog(
                    intercept_key=intercept_key_uuid,
                    request_method=request.method,
                    request_url=str(request.url),
                    request_headers=dict(request.headers), # Store all headers for now
                    request_body=request_body_json,
                    response_status_code=response.status_code,
                    response_headers=dict(response.headers),
                    response_body=response_body_json,
                )
                print(f"Created log entry: {log_entry}")
                session.add(log_entry)
                print("Added to session")
                # Add an explicit commit here to see if it helps
                await session.commit()
                print("Committed to database")
                print(f"Logged request/response for key {intercept_key_uuid} to DB")
                break
        except Exception as e:
            print(f"Failed to log request to DB for key {intercept_key_uuid}: {e}")
            # Optionally log to file as fallback here if DB fails

    else:
        # Fallback: Log to file if key is invalid or missing (optional)
        log_id = f"{start_time.strftime('%Y%m%d_%H%M%S_%f')}"
        print(f"No valid intercept key. Logging to file: {log_id}")
        # You might want to keep or remove the file logging part
        # await log_request_to_file(request, log_id, request_body_bytes)
        # await log_response_to_file(log_id, response.status_code, dict(response.headers), response_body_bytes)


    # Return the response using the consumed body
    return Response(
        content=response_body_bytes,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type
    )