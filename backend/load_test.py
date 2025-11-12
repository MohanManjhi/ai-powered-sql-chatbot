import requests
import threading
import time

# --- Configuration ---
BASE_URL = "http://localhost:5001"  # The base URL of your Flask application
NUM_USERS = 10  # The number of concurrent users to simulate
TEST_DURATION = 30  # The duration of the test in seconds

# --- API Endpoints to Test ---
ENDPOINTS = [
    {
        "path": "/api/nl-to-sql",
        "method": "POST",
        "json": {"question": "Show me all books", "db_type": "sql"}
    },
    {
        "path": "/api/nl-to-sql",
        "method": "POST",
        "json": {"question": "Show me all photos", "db_type": "mongo"}
    },
    {
        "path": "/api/schema",
        "method": "GET",
        "json": None
    },
    {
        "path": "/api/health",
        "method": "GET",
        "json": None
    }
]

# --- Global Statistics ---
total_requests = 0
total_response_time = 0
lock = threading.Lock()

def worker(worker_id):
    """
    This function represents a single user.
    It will repeatedly send requests to the API endpoints for the specified duration.
    """
    global total_requests
    global total_response_time

    print(f"Worker {worker_id}: Starting...")
    start_time = time.time()

    while time.time() - start_time < TEST_DURATION:
        for endpoint in ENDPOINTS:
            try:
                url = BASE_URL + endpoint["path"]
                method = endpoint["method"]
                json_data = endpoint["json"]

                response_start_time = time.time()

                if method == "POST":
                    response = requests.post(url, json=json_data)
                else:
                    response = requests.get(url)

                response_time = time.time() - response_start_time

                with lock:
                    total_requests += 1
                    total_response_time += response_time

                # Optional: Add a small delay between requests
                time.sleep(1)

            except requests.exceptions.RequestException as e:
                print(f"Worker {worker_id}: Request failed: {e}")

    print(f"Worker {worker_id}: Finished.")


def main():
    """
    This function creates and starts the threads, and then waits for them to complete.
    It also prints out some basic statistics at the end.
    """
    print("--- Starting Load Test ---")
    print(f"Number of users: {NUM_USERS}")
    print(f"Test duration: {TEST_DURATION} seconds")
    print("--------------------------")

    threads = []
    for i in range(NUM_USERS):
        thread = threading.Thread(target=worker, args=(i,)) 
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    print("\n--- Load Test Finished ---")
    print(f"Total requests: {total_requests}")
    if total_requests > 0:
        average_response_time = total_response_time / total_requests
        print(f"Average response time: {average_response_time:.4f} seconds")
    print("--------------------------")
    print("\nTo run this script, make sure your Flask application is running.")
    print("You can then execute this script from your terminal:")
    print("python backend/load_test.py")


if __name__ == "__main__":
    main()
