import os
from typing import Optional

try:
    from langfuse import Langfuse
except ImportError:
    Langfuse = None

class LangfuseSingleton:
    _instance: Optional['LangfuseSingleton'] = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_client()
        return cls._instance

    def _init_client(self):
        if Langfuse is None:
            self._client = None
            return
        # .env 파일에서 직접 읽기
        import os
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".security", ".env")
        env_map = {}
        if os.path.exists(env_path):
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    raw = line.strip()
                    if not raw or raw.startswith("#") or "=" not in raw:
                        continue
                    key, value = raw.split("=", 1)
                    env_map[key.strip()] = value.strip().strip('"').strip("'")
        public_key = env_map.get("LANGFUSE_PUBLIC_KEY", "")
        secret_key = env_map.get("LANGFUSE_SECRET_KEY", "")
        base_url = env_map.get("LANGFUSE_BASE_URL", "")
        if public_key and secret_key and base_url:
            self._client = Langfuse(public_key=public_key, secret_key=secret_key, host=base_url)
        else:
            self._client = None

    @property
    def client(self):
        return self._client

    def record_duration(self, trace_name: str, elapsed: float, metadata: Optional[dict] = None):
        if self._client is None:
            print(f"Langfuse client not initialized. Cannot record trace '{trace_name}'.")
            return
        if metadata is None:
            metadata = {}
        # Langfuse v4: context manager 기반 span 생성
        with self._client.start_as_current_observation(as_type="span", name=trace_name, metadata=metadata) as span:
            span.update(output=f"duration: {elapsed}")
        print(f"Recorded trace '{trace_name}' with duration {elapsed} seconds.")

def get_langfuse_singleton() -> LangfuseSingleton:
    return LangfuseSingleton()
