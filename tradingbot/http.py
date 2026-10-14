import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def make_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=6,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_maxsize=16)
    s.mount("https://", adapter)
    s.headers["User-Agent"] = "tradingbot-research/0.1 (backtest)"
    return s
