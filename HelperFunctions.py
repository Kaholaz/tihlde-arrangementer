import logging
from requests.models import Response


def check_status_code(r: Response) -> bool:
    """
    Checks status code of a response. Returns `True` if the response
    had a status-code starting with 200, `False` if not.
    """
    if 200 <= r.status_code and r.status_code < 300:
        logging.debug(
            f"Request to {r.url} returned with status code {r.status_code} <{r.reason}>"
        )
        return True
    else:
        logging.warning(
            f"Request to {r.url} returned with status code {r.status_code} <{r.reason}>"
        )
        return False
