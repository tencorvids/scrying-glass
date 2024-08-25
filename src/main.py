import cv2 as cv
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException
import psycopg2
import os
from dotenv import find_dotenv, load_dotenv
from src.card_detector import detect
import logging

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

DB_NAME = os.getenv("DATABASE")
DB_USER = os.getenv("USER")
DB_PASSWORD = os.getenv("PASSWORD")
DB_HOST = os.getenv("HOST")
DB_PORT = os.getenv("PORT")

# Global variable for database connection
db_connection = None
db_cursor = None

def get_db_connection():
    global db_connection, db_cursor
    try:
        if db_connection is None or db_connection.closed:
            db_connection = psycopg2.connect(
                database=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
            )
            db_cursor = db_connection.cursor()
            logger.info("Database connection established")
    except psycopg2.Error as e:
        logger.error(f"Unable to connect to the database: {e}")
        raise HTTPException(status_code=500, detail="Database connection error")

@app.on_event("startup")
async def startup_event():
    get_db_connection()

@app.on_event("shutdown")
async def shutdown_event():
    global db_connection, db_cursor
    if db_cursor:
        db_cursor.close()
    if db_connection:
        db_connection.close()
    logger.info("Database connection closed")

def execute_query(query, params):
    global db_cursor
    if db_cursor is None:
        return
    try:
        db_cursor.execute(query, params)
        return db_cursor.fetchone()
    except psycopg2.Error as e:
        logger.error(f"Database query error: {e}")
        raise HTTPException(status_code=500, detail="Database query error")

@app.post("/scry")
async def UploadImage(file: UploadFile = File(...)):
    content = await file.read()
    im_file = np.asarray(bytearray(content), dtype=np.uint8)
    img = cv.imdecode((im_file), cv.IMREAD_UNCHANGED)

    original_hash_int, processed_hash_otsu_int, processed_hash_binary_otsu_int, processed_hash_binary_int, processed_hash_adaptive_int = detect(img)

    if None in (original_hash_int, processed_hash_otsu_int, processed_hash_binary_otsu_int, processed_hash_binary_int, processed_hash_adaptive_int):
        raise HTTPException(status_code=400, detail="Image processing failed")

    get_db_connection() 

    query = "SELECT scryfall_uri, perceptual_hash_int FROM cards ORDER BY ABS(perceptual_hash_int - %s) ASC LIMIT 1"

    original_result = execute_query(query, (original_hash_int,))
    otsu_result = execute_query(query, (processed_hash_otsu_int,))
    binary_otsu_result = execute_query(query, (processed_hash_binary_otsu_int,))
    binary_result = execute_query(query, (processed_hash_binary_int,))
    adaptive_result = execute_query(query, (processed_hash_adaptive_int,))

    if not all([original_result, otsu_result, binary_otsu_result, binary_result, adaptive_result]):
        raise HTTPException(status_code=404, detail="No matching cards found")

    original_scryfall_uri, original_p_hash_int = original_result
    processed_otsu_scryfall_uri, processed_otsu_p_hash_int = otsu_result
    processed_binary_otsu_scryfall_uri, processed_binary_otsu_p_hash_int = binary_otsu_result
    processed_binary_scryfall_uri, processed_binary_p_hash_int = binary_result
    processed_adaptive_scryfall_uri, processed_adaptive_p_hash_int = adaptive_result

    original_hamming_distance = abs(original_hash_int - original_p_hash_int)
    processed_otsu_hamming_distance = abs(processed_hash_otsu_int - processed_otsu_p_hash_int)
    processed_binary_otsu_hamming_distance = abs(processed_hash_binary_otsu_int - processed_binary_otsu_p_hash_int)
    processed_binary_hamming_distance = abs(processed_hash_binary_int - processed_binary_p_hash_int)
    processed_adaptive_hamming_distance = abs(processed_hash_adaptive_int - processed_adaptive_p_hash_int)

    data = {
        'original': {
            'scryfall_uri': original_scryfall_uri,
            'hamming_distance': original_hamming_distance
        },
        'otsu': {
            'scryfall_uri': processed_otsu_scryfall_uri,
            'hamming_distance': processed_otsu_hamming_distance
        },
        'binary_otsu': {
            'scryfall_uri': processed_binary_otsu_scryfall_uri,
            'hamming_distance': processed_binary_otsu_hamming_distance
        },
        'binary': {
            'scryfall_uri': processed_binary_scryfall_uri,
            'hamming_distance': processed_binary_hamming_distance
        },
        'adaptive': {
            'scryfall_uri': processed_adaptive_scryfall_uri,
            'hamming_distance': processed_adaptive_hamming_distance
        }
    }

    min_distance = min(data, key=lambda x: data[x]['hamming_distance'])
    return {'uri': data[min_distance]['scryfall_uri']}
