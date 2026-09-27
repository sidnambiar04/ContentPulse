import time
import requests


HEADERS = {
    "User-Agent": "ContentPulse/1.0",
    "Accept": "text/html,application/xhtml+xml"
}

MAX_RETRIES = 3
REQUEST_TIMEOUT = 15
RETRY_BACKOFF_SECONDS = 1

RETRYABLE_STATUS_CODES = {
    408,
    425,
    429,
    500,
    502,
    503,
    504
}


def request_with_retry(
    url,
    method="GET",
    timeout=REQUEST_TIMEOUT
):

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            print(
                f"HTTP request "
                f"(attempt {attempt}/{MAX_RETRIES}): "
                f"{url}"
            )

            response = requests.request(
                method=method,
                url=url,
                headers=HEADERS,
                timeout=timeout
            )

            if response.ok:
                return response

            if response.status_code not in RETRYABLE_STATUS_CODES:

                print(
                    f"HTTP {response.status_code} "
                    f"for {url} - not retrying"
                )

                response.raise_for_status()

            print(
                f"HTTP {response.status_code} "
                f"for {url}"
            )

            if attempt < MAX_RETRIES:

                wait_time = (
                    RETRY_BACKOFF_SECONDS
                    * (2 ** (attempt - 1))
                )

                print(
                    f"Retrying in "
                    f"{wait_time} seconds..."
                )

                time.sleep(wait_time)

            else:
                response.raise_for_status()

        except requests.exceptions.Timeout as e:

            print(f"Timeout for {url}")

            if attempt < MAX_RETRIES:

                wait_time = (
                    RETRY_BACKOFF_SECONDS
                    * (2 ** (attempt - 1))
                )

                print(
                    f"Retrying in "
                    f"{wait_time} seconds..."
                )

                time.sleep(wait_time)

            else:
                raise e

        except requests.exceptions.ConnectionError as e:

            print(
                f"Connection error for {url}"
            )

            if attempt < MAX_RETRIES:

                wait_time = (
                    RETRY_BACKOFF_SECONDS
                    * (2 ** (attempt - 1))
                )

                print(
                    f"Retrying in "
                    f"{wait_time} seconds..."
                )

                time.sleep(wait_time)

            else:
                raise e

        except requests.exceptions.RequestException:
            raise

    return None