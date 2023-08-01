import json

def load_config():
    config = json.load(open('config.json', 'r'))
    return config
