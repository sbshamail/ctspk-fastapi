# src/api/core/avatar_helper.py
import base64
from typing import Dict, Any, Optional
import hashlib


def get_initials(name: str) -> str:
    """
    Extract first and last letter from name for avatar

    Args:
        name: User's full name

    Returns:
        str: Two-letter initials (first and last letter)
    """
    if not name or len(name.strip()) == 0:
        return "?"

    # Remove extra spaces and split
    name_parts = name.strip().split()

    if len(name_parts) == 1:
        # Single word - use first and last letter
        word = name_parts[0]
        if len(word) == 1:
            return word.upper()
        return (word[0] + word[-1]).upper()
    else:
        # Multiple words - use first letter of first and last word
        return (name_parts[0][0] + name_parts[-1][0]).upper()


def get_color_from_name(name: str) -> str:
    """
    Generate a consistent color based on the name using hash

    Args:
        name: User's name

    Returns:
        str: Hex color code
    """
    # Use MD5 hash to generate consistent color
    hash_obj = hashlib.md5(name.encode())
    hash_hex = hash_obj.hexdigest()

    # Use first 6 characters as color
    color = f"#{hash_hex[:6]}"
    return color


def generate_svg_avatar(name: str, size: int = 200) -> str:
    """
    Generate SVG avatar with initials

    Args:
        name: User's name
        size: Size of the avatar in pixels (default: 200)

    Returns:
        str: SVG string
    """
    initials = get_initials(name)
    bg_color = get_color_from_name(name)

    # Calculate font size based on avatar size
    font_size = int(size * 0.4)

    svg = f'''<svg width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">
    <rect width="{size}" height="{size}" fill="{bg_color}"/>
    <text x="50%" y="50%"
          font-family="Arial, sans-serif"
          font-size="{font_size}"
          font-weight="600"
          fill="white"
          text-anchor="middle"
          dominant-baseline="central">
        {initials}
    </text>
</svg>'''

    return svg


def generate_avatar_data_url(name: str, size: int = 200) -> str:
    """
    Generate data URL for SVG avatar

    Args:
        name: User's name
        size: Size of the avatar in pixels

    Returns:
        str: Data URL string
    """
    svg = generate_svg_avatar(name, size)
    # Encode SVG as base64
    svg_base64 = base64.b64encode(svg.encode('utf-8')).decode('utf-8')
    return f"data:image/svg+xml;base64,{svg_base64}"


def get_user_avatar(user_image: Optional[Dict[str, Any]], user_name: str) -> Dict[str, str]:
    """
    Get user avatar - returns uploaded image or generates SVG avatar

    Args:
        user_image: User's image JSON data (can be None)
        user_name: User's name for generating avatar

    Returns:
        Dict containing 'original' and 'thumbnail' URLs
    """
    if user_image and isinstance(user_image, dict):
        # User has uploaded image
        return {
            "original": user_image.get("original", ""),
            "thumbnail": user_image.get("thumbnail", user_image.get("original", "")),
            "id": user_image.get("id", None)
        }
    else:
        # Generate SVG avatar
        avatar_url = generate_avatar_data_url(user_name, 200)
        thumbnail_url = generate_avatar_data_url(user_name, 100)

        return {
            "original": avatar_url,
            "thumbnail": thumbnail_url,
            "id": None
        }
