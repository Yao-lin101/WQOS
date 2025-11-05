import os

ROOT_PATH = os.path.dirname(os.path.dirname(__file__))  # 项目根目录
DATA_PATH = os.path.join(ROOT_PATH, 'data')
RECORDS_PATH = os.path.join(ROOT_PATH, 'records')
DATASETS_PATH = os.path.join(DATA_PATH, 'datasets')
FIELDS_PATH = os.path.join(DATA_PATH, 'fields')

REGION_LIST = ['USA', 'GLB', 'EUR', 'ASI', 'CHN', 'KOR', 'TWN', 'JPN', 'HKG', 'AMR', 'IND']

os.makedirs(DATA_PATH, exist_ok=True)
os.makedirs(RECORDS_PATH, exist_ok=True)
os.makedirs(DATASETS_PATH, exist_ok=True)
os.makedirs(FIELDS_PATH, exist_ok=True)
