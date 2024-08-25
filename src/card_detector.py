import cv2 as cv
import numpy as np
from PIL import Image
import imagehash
from typing import Tuple, Optional

from src.utils.image_processing import image_resize, histogram_equalization

def preprocess(image: np.ndarray, mode: str = 'otsu') -> np.ndarray:
    """
    Preprocess the input image for card detection.

    Args:
        image (np.ndarray): Input image
        mode (str): Thresholding mode ('otsu', 'binary', 'adaptive', or 'binary_otsu')

    Returns:
        np.ndarray: Preprocessed image
    """
    resized = image_resize(image)
    equalized = histogram_equalization(resized)
    
    gray = cv.cvtColor(equalized, cv.COLOR_BGR2GRAY)
    blur = cv.GaussianBlur(gray, (3,3), 0)
    
    if mode == 'binary':
        return cv.threshold(blur, 70, 255, cv.THRESH_BINARY)[1]
    elif mode == 'adaptive':
        return cv.adaptiveThreshold(blur, 255, cv.ADAPTIVE_THRESH_GAUSSIAN_C, cv.THRESH_BINARY, 11, 10)
    elif mode == 'binary_otsu':
        return cv.threshold(blur, 70, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)[1]
    else:  # default to 'otsu'
        return cv.threshold(blur, 70, 255, cv.THRESH_OTSU)[1]

def warp(image: np.ndarray, points: np.ndarray) -> np.ndarray:
    """
    Perform perspective transform on the image based on the given points.

    Args:
        image (np.ndarray): Input image
        points (np.ndarray): Corner points for perspective transform, shape (4, 1, 2)

    Returns:
        np.ndarray: Warped image
    """
    temp_rect = np.zeros((4, 2), dtype='float32')
    s = np.sum(points, axis=1)

    temp_rect[0] = points[np.argmin(s)][0]  # Top-left point
    temp_rect[2] = points[np.argmax(s)][0]  # Bottom-right point

    diff = np.diff(points, axis=1)
    temp_rect[1] = points[np.argmin(diff)][0]  # Top-right point
    temp_rect[3] = points[np.argmax(diff)][0]  # Bottom-left point

    max_width = 476
    max_height = 664

    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1]], dtype="float32")

    M = cv.getPerspectiveTransform(temp_rect, dst)
    warped = cv.warpPerspective(image, M, (max_width, max_height))

    return warped

def segmentation(image: np.ndarray, original: np.ndarray) -> np.ndarray:
    """
    Segment the card from the image.

    Args:
        image (np.ndarray): Preprocessed image
        original (np.ndarray): Original image

    Returns:
        np.ndarray: Segmented and warped image of the card
    """
    contours, _ = cv.findContours(image, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
    contours_sorted = sorted(contours, key=cv.contourArea, reverse=True)
    card_contour = contours_sorted[1]

    perimeter = cv.arcLength(card_contour, True)
    approximate_points = cv.approxPolyDP(card_contour, 0.01 * perimeter, True)
    
    points = np.float32(approximate_points).reshape(4, 1, 2)

    warped_image = warp(original, points)
    return warped_image

def detect(image: np.ndarray) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int], Optional[int]]:
    """
    Detect and hash the card in the image using various preprocessing methods.

    Args:
        image (np.ndarray): Input image

    Returns:
        Tuple[Optional[int], Optional[int], Optional[int], Optional[int], Optional[int]]:
            Hash values for original, otsu, binary_otsu, binary, and adaptive preprocessing methods
    """
    try:
        original_hash = imagehash.phash(Image.fromarray(image), 16)
        processed_hash_otsu = imagehash.phash(Image.fromarray(preprocess(image, mode='otsu')), 16)
        processed_hash_binary_otsu = imagehash.phash(Image.fromarray(preprocess(image, mode='binary_otsu')), 16)
        processed_hash_binary = imagehash.phash(Image.fromarray(preprocess(image, mode='binary')), 16)
        processed_hash_adaptive = imagehash.phash(Image.fromarray(preprocess(image, mode='adaptive')), 16)

        return (
            int(str(original_hash), 16),
            int(str(processed_hash_otsu), 16),
            int(str(processed_hash_binary_otsu), 16),
            int(str(processed_hash_binary), 16),
            int(str(processed_hash_adaptive), 16)
        )
    except Exception as e:
        print(f"Error during image detection: {str(e)}")
        return None, None, None, None, None
