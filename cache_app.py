import os
import pickle
from datetime import datetime, timedelta
from typing import Any, Optional

CACHE_FILENAME = 'historical_data.pkl'
CACHE_DURATION = timedelta(days=1)

def load_cache() -> Optional[Any]:
    if os.path.exists(CACHE_FILENAME):
        try:
            with open(CACHE_FILENAME, 'rb') as file:
                cached_content = pickle.load(file)
                last_update_time = cached_content['last_updated']
                if datetime.now() - last_update_time < CACHE_DURATION:
                    return cached_content['data']
        except (pickle.UnpicklingError, KeyError, EOFError) as error:
            print(f"Error loading cache: {error}")
    return None

def save_cache(data: Any) -> None:
    cache_data = {
        'last_updated': datetime.now(),
        'data': data
    }
    try:
        with open(CACHE_FILENAME, 'wb') as file:
            pickle.dump(cache_data, file)
    except pickle.PicklingError as error:
        print(f"Error saving cache: {error}")