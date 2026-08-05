"""Pipeline test for the Computer Graphics & Image Processing lab."""

import cv2
import numpy as np


def main() -> None:
    """Run the pipeline test and display the resulting image."""
    # Create a black image of size 300x300 with 3 color channels (BGR).
    image = np.zeros((300, 300, 3), dtype=np.uint8)

    # Define the text lines to draw on the image.
    lines = [
        "CG & IP Pipeline OK",
        "Project: Smart Document Scanner with OCR",
        "Taksh Shah - 24000986",
        "Husain Khanrahim- 24001166",
        "Aarya Parikh - 24001046",
        
    ]

    # Choose font, scale, color, and thickness for the text.
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    color = (255, 255, 255)  # White text in BGR format.
    thickness = 1

    # Draw each line of text onto the image with a vertical offset.
    y_start = 30
    y_step = 30
    for index, line in enumerate(lines):
        position = (10, y_start + index * y_step)
        cv2.putText(image, line, position, font, font_scale, color, thickness, cv2.LINE_AA)

    # Convert the color image to grayscale for edge detection.
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply Canny edge detection to the grayscale image.
    edges = cv2.Canny(gray_image, 50, 150)

    # Display the result in a window titled 'Pipeline Test'.
    cv2.imshow("Pipeline Test", edges)

    # Wait until any key is pressed.
    cv2.waitKey(0)

    # Close all OpenCV windows.
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
