import redis as r
from typing import Optional, Any
from redis_lock import Lock
import json
import time

redis = r.Redis(connection_pool=r.ConnectionPool(host='localhost', port=6379, db=12))

def rget(key: str) -> Optional[str]:
    raw_result = redis.get(key)
    return raw_result.decode('utf-8') if raw_result is not None else None


def rget_int(key: str) -> Optional[int]:
    raw_result = rget(key)
    return int(raw_result) if raw_result is not None else None


def can_be_inted(x):
    try:
        int(x)
        return True
    except Exception:
        return False


def jsonKeys2int(x):
    if isinstance(x, dict):
        return {int(k) if can_be_inted(k) else k:v for k,v in x.items()}
    return x


def rget_json(key: str):
    raw_result = rget(key)
    return json.loads(raw_result, object_hook=jsonKeys2int) if raw_result is not None else None


def rset(key: str, value: Any, ex: Optional[int] = None) -> None:
    redis.set(key, value, ex=ex)


def rset_json(key: str, value: Any, ex: Optional[int] = None) -> None:
    rset(key, json.dumps(value), ex=ex)


def rdel(key: str) -> None:
    redis.delete(key)


def rlock(key: str, expire: int = 60) -> Lock:
    return Lock(redis, key, expire=expire)


def rkeys(pattern: str) -> list[str]:
    return redis.keys(pattern)


class CodeBlockCounter:

    def __init__(self, key: str):
        self.key = key
        self.lock = rlock(f"lock:{key}")

    def __enter__(self):
        with self.lock:
            count = rget(self.key)
            if count is None:
                rset(self.key, 1)
            else:
                rset(self.key, int(count) + 1)

    def __exit__(self, exc_type, exc_val, exc_tb):
        with self.lock:
            count = rget(self.key)
            if count is not None and int(count) > 1:
                rset(self.key, int(count) - 1)
            else:
                rdel(self.key)

def await_empty_counter(key, max_time, time_increment):
    for _ in range(int(max_time / time_increment)):
        if rget(key) is None:
            return
        time.sleep(time_increment)
    print("!!! Moves processing did not finish in time !!!")
    print(f"Key: {key}")
    print(f"Max time: {max_time}")
    print(f"Time increment: {time_increment}")
    return

