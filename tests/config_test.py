import os, json

from appdirs import AppDirs

dirs = AppDirs("Kodexa", "Kodexa")

path = os.path.join(dirs.user_config_dir, ".kodexa.json")
if os.path.exists(path):
    with open(path, "r") as outfile:
        kodexa_config = json.load(outfile)
        print(kodexa_config)
