import time
from typing import Optional

import requests


def wait_for_backend(
    timeout: int = 60, url: str = "http://localhost:8080/health"
) -> None:
    try:
        print("Waiting for backend to start...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                requests.get(url)
                print("Backend is ready!")
                exit(0)
            except requests.exceptions.ConnectionError:
                time.sleep(1)
                print("Still waiting...")
        print("Timeout waiting for backend")
        exit(1)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    wait_for_backend()
