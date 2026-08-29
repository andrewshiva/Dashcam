import os
import sys

# Import the validation logic from main.py
from main import validate_video

def run_test(video_path: str):
    print(f"--- Testing Video: {video_path} ---")
    if not os.path.exists(video_path):
        print(f"ERROR: File not found: {video_path}")
        print("Please place a test video in this folder.")
        sys.exit(1)

    is_valid, reason = validate_video(video_path)
    
    if is_valid:
        print("✅ RESULT: VALID")
        print("This video meets all requirements (H.264/H.265 codec, >= 720p resolution, >= 5 seconds).")
        print("It would be routed to the 'Validated' bucket.")
    else:
        print("❌ RESULT: INVALID")
        print(f"Reason: {reason}")
        print("It would be routed to the 'Quarantine' bucket.")

if __name__ == "__main__":
    # Default to test_video.mp4 if no argument is provided
    target_video = sys.argv[1] if len(sys.argv) > 1 else "test_video.mp4"
    run_test(target_video)
