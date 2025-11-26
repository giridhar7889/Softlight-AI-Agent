"""Image processing utilities for UI change detection and screenshot management."""

import io
import base64
from pathlib import Path
from typing import Tuple, Optional
import numpy as np
from PIL import Image
import imagehash
import cv2


class ImageProcessor:
    """Handles image processing operations."""
    
    @staticmethod
    def load_image(image_path: Path) -> Image.Image:
        """Load an image from file."""
        return Image.open(image_path)
    
    @staticmethod
    def save_image(image: Image.Image, output_path: Path, quality: int = 95):
        """Save an image to file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path, quality=quality, optimize=True)
    
    @staticmethod
    def encode_image_base64(image_path: Path) -> str:
        """Encode an image to base64 string."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    @staticmethod
    def image_to_base64(image: Image.Image, format: str = "PNG") -> str:
        """Convert PIL Image to base64 string."""
        buffered = io.BytesIO()
        image.save(buffered, format=format)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    @staticmethod
    def compute_hash(image: Image.Image, hash_size: int = 16) -> str:
        """Compute perceptual hash of an image."""
        return str(imagehash.phash(image, hash_size=hash_size))
    
    @staticmethod
    def compute_similarity(image1: Image.Image, image2: Image.Image) -> float:
        """
        Compute similarity between two images using perceptual hashing.
        Returns a value between 0 (completely different) and 1 (identical).
        """
        hash1 = imagehash.phash(image1)
        hash2 = imagehash.phash(image2)
        
        # Calculate Hamming distance
        hash_diff = hash1 - hash2
        
        # Convert to similarity (0-1 scale)
        # Maximum possible difference for phash is 64 (8x8 hash)
        max_diff = 64
        similarity = 1 - (hash_diff / max_diff)
        
        return similarity
    
    @staticmethod
    def compute_structural_similarity(image1: Image.Image, image2: Image.Image) -> float:
        """
        Compute structural similarity (SSIM) between two images.
        More accurate but slower than hash-based comparison.
        """
        # Convert to numpy arrays
        img1_array = np.array(image1.convert('L'))
        img2_array = np.array(image2.convert('L'))
        
        # Resize if dimensions don't match
        if img1_array.shape != img2_array.shape:
            img2_array = cv2.resize(img2_array, (img1_array.shape[1], img1_array.shape[0]))
        
        # Compute SSIM
        from skimage.metrics import structural_similarity
        ssim_score = structural_similarity(img1_array, img2_array)
        
        return ssim_score
    
    @staticmethod
    def detect_change(
        image1: Image.Image,
        image2: Image.Image,
        threshold: float = 0.15,
        method: str = "hash"
    ) -> Tuple[bool, float]:
        """
        Detect if there's a significant change between two images.
        
        Args:
            image1: First image
            image2: Second image
            threshold: Change threshold (0-1, higher means more change needed)
            method: Comparison method ("hash" or "structural")
        
        Returns:
            Tuple of (changed: bool, difference: float)
        """
        if method == "hash":
            similarity = ImageProcessor.compute_similarity(image1, image2)
        else:
            similarity = ImageProcessor.compute_structural_similarity(image1, image2)
        
        difference = 1 - similarity
        changed = difference >= threshold
        
        return changed, difference
    
    @staticmethod
    def create_diff_image(
        image1: Image.Image,
        image2: Image.Image,
        output_path: Optional[Path] = None
    ) -> Image.Image:
        """
        Create a visual diff image highlighting changes between two images.
        """
        # Convert to numpy arrays
        img1_array = np.array(image1.convert('RGB'))
        img2_array = np.array(image2.convert('RGB'))
        
        # Resize if needed
        if img1_array.shape != img2_array.shape:
            img2_array = cv2.resize(
                img2_array,
                (img1_array.shape[1], img1_array.shape[0])
            )
        
        # Compute absolute difference
        diff = cv2.absdiff(img1_array, img2_array)
        
        # Convert to grayscale and threshold
        gray_diff = cv2.cvtColor(diff, cv2.COLOR_RGB2GRAY)
        _, thresh = cv2.threshold(gray_diff, 30, 255, cv2.THRESH_BINARY)
        
        # Create colored diff overlay
        diff_colored = np.zeros_like(img1_array)
        diff_colored[:, :, 0] = thresh  # Red channel for differences
        
        # Blend with original
        alpha = 0.5
        blended = cv2.addWeighted(img2_array, alpha, diff_colored, 1 - alpha, 0)
        
        # Convert back to PIL
        diff_image = Image.fromarray(blended)
        
        if output_path:
            diff_image.save(output_path)
        
        return diff_image
    
    @staticmethod
    def resize_image(
        image: Image.Image,
        max_width: int = 1920,
        max_height: int = 1080,
        maintain_aspect: bool = True
    ) -> Image.Image:
        """Resize image while maintaining aspect ratio."""
        if not maintain_aspect:
            return image.resize((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Calculate scaling factor
        width_ratio = max_width / image.width
        height_ratio = max_height / image.height
        scale_factor = min(width_ratio, height_ratio, 1.0)  # Don't upscale
        
        if scale_factor < 1.0:
            new_width = int(image.width * scale_factor)
            new_height = int(image.height * scale_factor)
            return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return image
    
    @staticmethod
    def crop_region(
        image: Image.Image,
        x: int,
        y: int,
        width: int,
        height: int
    ) -> Image.Image:
        """Crop a specific region from an image."""
        return image.crop((x, y, x + width, y + height))
    
    @staticmethod
    def annotate_element(
        image: Image.Image,
        x: int,
        y: int,
        width: int,
        height: int,
        color: Tuple[int, int, int] = (255, 0, 0),
        thickness: int = 3
    ) -> Image.Image:
        """Draw a bounding box around an element on the image."""
        img_array = np.array(image)
        cv2.rectangle(
            img_array,
            (x, y),
            (x + width, y + height),
            color,
            thickness
        )
        return Image.fromarray(img_array)

