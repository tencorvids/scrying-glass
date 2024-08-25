import cv2 as cv

def image_resize(image, width=800, height=None, interp=cv.INTER_AREA):
    """
    Resize the input image.

    Args:
        image (np.ndarray): Input image
        width (int): Desired width of the output image
        height (int): Desired height of the output image
        interp: Interpolation method

    Returns:
        np.ndarray: Resized image
    """
    dim = None
    (h, w) = image.shape[:2]

    if width is None or height is None:
        return image

    if width is None:
        r = height / float(h)
        dim = (int(w * r), height)

    else:
        r = width / float(w)
        dim = (width, int(h * r))

    resized = cv.resize(image, dim, interpolation=interp)
    return resized

def histogram_equalization(image):
    """
    Perform histogram equalization on the input image.

    Args:
        image (np.ndarray): Input image

    Returns:
        np.ndarray: Equalized image
    """
    clahe = cv.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))

    lab_image = cv.cvtColor(image, cv.COLOR_BGR2LAB)

    l, r, y = cv.split(lab_image)
    l_adjusted = clahe.apply(l)

    adjusted_lab_image = cv.merge((l_adjusted, r, y))
    adjusted_image = cv.cvtColor(adjusted_lab_image, cv.COLOR_LAB2BGR)

    return adjusted_image
