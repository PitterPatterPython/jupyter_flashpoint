import base64

def create_b64_image_string(raw_image):
    """Convert a raw bytes image to a base64 string"""
    return base64.b64encode(raw_image).decode()

def format_b64_image_for_dataframe(b64_image_string):
    """Format a b64 image string as a valid HTML object, to be
        used in a dataframe.
    """
    return f"<img src='data:image/jpeg;base64,{b64_image_string}' />"