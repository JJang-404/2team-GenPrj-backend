
# 프로젝트 전역 상수 및 설정 경로 정의 파일
import os

# 디렉토리 경로 설정
APP_DIR = os.path.dirname(os.path.abspath(__file__))
# current file is backend/common/defines.py, so go up twice for project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DBFILE_DIR = os.path.join(DATA_DIR, "db")
if not os.path.exists(DBFILE_DIR):
    os.makedirs(DBFILE_DIR)
BACKEND_INI_PATH = os.path.join(APP_DIR, "backend.ini")

# SQLite DB 파일 경로 및 SQLAlchemy URL
DB_FILE_PATH = os.path.join(DBFILE_DIR, "genprj.db")
DEFAULT_DATABASE_URL = f"sqlite:///{DB_FILE_PATH.replace(os.sep, '/')}"

# 애플리케이션 메타데이터
APP_NAME = "genprj-backend"
APP_TITLE = "genprj Backend"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "genprj FastAPI backend project"


# OpenAI 프롬프트 분리 설정
_DEFAULT_BASE_PROMPT_MSG = "You prepare Stable Diffusion 3.5 prompts. Return strict JSON only with keys positive_prompt and negative_prompt. Respect user-supplied positive_prompt and negative_prompt first, translate Korean or mixed-language inputs into concise natural English, fill missing fields from prompt context, and if negative_prompt is missing use a safe image-quality negative prompt. Do not include markdown or explanations."


def get_server_port() -> int:
	"""backend.ini의 [server] port를 읽어서 반환합니다."""
	import configparser
	config = configparser.ConfigParser()
	config.read(BACKEND_INI_PATH, encoding="utf-8")
	return config.getint("server", "port", fallback=8119)

def get_base_prompt_msg() -> str:
	"""backend.ini의 [engine] base_prompt_msg를 읽어서 반환합니다."""
	import configparser
	config = configparser.ConfigParser()
	config.read(BACKEND_INI_PATH, encoding="utf-8")
	msg = config.get("engine", "base_prompt_msg", fallback=_DEFAULT_BASE_PROMPT_MSG).strip()
	return msg or _DEFAULT_BASE_PROMPT_MSG

SERVER_PORT = get_server_port()
BASE_PROMPT_MSG = get_base_prompt_msg()
