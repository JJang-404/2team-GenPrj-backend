
# 프로젝트 전역 상수 및 설정 경로 정의 파일
import os

# 디렉토리 경로 설정
APP_DIR = os.path.dirname(os.path.abspath(__file__))
# current file is backend/common/defines.py, so go up twice for project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DBFILE_DIR = os.path.join(DATA_DIR, "db")
NABIDREAM_BEND_INI_PATH = os.path.join(APP_DIR, "nabidream_bend.ini")
BACKEND_INI_PATH = os.path.join(APP_DIR, "backend.ini")

# SQLite DB 파일 경로 및 SQLAlchemy URL
DB_FILE_PATH = os.path.join(DBFILE_DIR, "nabidream.db")
DEFAULT_DATABASE_URL = f"sqlite:///{DB_FILE_PATH.replace(os.sep, '/')}"

# 애플리케이션 메타데이터
APP_NAME = "nabidream-backend"
APP_TITLE = "nabidream Backend"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "nabidream FastAPI backend starter project"

# 감성 분석 점수 및 별점 임계값
SENTIMENT_NEUTRAL_SCORE = 0.5
SENTIMENT_POSITIVE_SCORE = 1.0
SENTIMENT_NEGATIVE_SCORE = 0.0
SENTIMENT_MIN_RATING = 1
SENTIMENT_NEUTRAL_RATING = 3
SENTIMENT_MAX_RATING = 5

# 키워드 기반 감성 분석용 사전
SENTIMENT_POSITIVE_KEYWORDS = ["좋", "재밌", "훌륭", "추천", "감동", "최고"]
SENTIMENT_NEGATIVE_KEYWORDS = ["별로", "지루", "최악", "실망", "나쁘", "후회"]

# INI 설정 섹션 이름
INI_SECTION_SENTIMENT = "sentiment"
INI_SECTION_HUGGINGFACE = "huggingface"
INI_SECTION_OLLAMA = "ollama"
INI_SECTION_SERVER = "server"
INI_SECTION_ENGINE = "engine"

# INI 설정 키 이름
INI_KEY_USEMODEL = "usemodel"
INI_KEY_PROVIDER = "provider"
INI_KEY_HUGGINGFACE_MODEL = "huggingface_model"
INI_KEY_OLLAMA_MODEL = "ollama_model"
INI_KEY_OLLAMA_BASE_URL = "ollama_base_url"
INI_KEY_OLLAMA_TIMEOUT_SEC = "ollama_timeout_sec"
INI_KEY_SERVER_PORT = "port"
INI_KEY_BASE_PROMPT_MSG = "base_prompt_msg"

# 감성 분석 제공자 상수
SENTIMENT_PROVIDER_HUGGINGFACE = "huggingface"
SENTIMENT_PROVIDER_OLLAMA = "ollama"
SENTIMENT_PROVIDER_HUGGINFLACE = "hugginflace" # 오타 방어용 유지

# 모델 및 API 기본값
DEFAULT_SENTIMENT_PROVIDER = SENTIMENT_PROVIDER_HUGGINGFACE
DEFAULT_HUGGINGFACE_MODEL = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
DEFAULT_OLLAMA_MODEL = "llama3.1:8b"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_TIMEOUT_SEC = 30
DEFAULT_SERVER_PORT = 8119

# OpenAI 번역 설정
_DEFAULT_BASE_PROMPT_MSG = "Translate Korean text to English image generation prompts. Output must be concise and vivid."


def get_server_port() -> int:
	"""backend.ini의 [server] port를 읽어서 반환합니다."""
	import configparser
	config = configparser.ConfigParser()
	config.read(BACKEND_INI_PATH, encoding="utf-8")
	return config.getint(INI_SECTION_SERVER, INI_KEY_SERVER_PORT, fallback=DEFAULT_SERVER_PORT)

def get_base_prompt_msg() -> str:
	"""backend.ini의 [engine] base_prompt_msg를 읽어서 반환합니다."""
	import configparser
	config = configparser.ConfigParser()
	config.read(BACKEND_INI_PATH, encoding="utf-8")
	msg = config.get(INI_SECTION_ENGINE, INI_KEY_BASE_PROMPT_MSG, fallback=_DEFAULT_BASE_PROMPT_MSG).strip()
	return msg or _DEFAULT_BASE_PROMPT_MSG

SERVER_PORT = get_server_port()
BASE_PROMPT_MSG = get_base_prompt_msg()
