from __future__ import annotations

import datetime


def get_time() -> dict[str, str]:
    now = datetime.datetime.now()
    return {"time": now.strftime("%I:%M %p").lstrip("0")}

