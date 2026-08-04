def load_config(filename):
    # Simulate a low-level failure (e.g. file doesn't exist)
    raise FileNotFoundError(f"could not find {filename}")


def start_app_without_from():
    try:
        load_config("settings.json")
    except FileNotFoundError as exc:
        raise RuntimeError("app failed to start")          # no 'from' at all


def start_app_with_from():
    try:
        load_config("settings.json")
    except FileNotFoundError as exc:
        raise RuntimeError("app failed to start") from exc  # explicit chain


def start_app_suppressed():
    try:
        load_config("settings.json")
    except FileNotFoundError as exc:
        raise RuntimeError("app failed to start") from None # chain hidden

#load_config("a")
start_app_without_from()
#start_app_with_from()
#start_app_suppressed()
