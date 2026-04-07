# 공통 유틸리티 클래스 및 함수 정의 파일
from __future__ import annotations
import json
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# 섹션, 키, 값 쌍을 담는 데이터 클래스
@dataclass
class SectionKeyVal:
    mSection: str
    mKey: str
    mVal: str

# 이벤트 상태를 담는 데이터 클래스
@dataclass
class MyFlag:
    mEventName: str
    mDo: bool

# 메모리 기반 간단한 키-밸브 저장소 및 큐 관리
class MemData:
    _data_queue: list[SectionKeyVal] = [] # 데이터 처리 큐
    _temp_flags: list[MyFlag] = []        # 임시 이벤트 플래그 큐
    _kv_store: dict[tuple[str, str], str] = {} # 키-밸브 저장소

    # 데이터 저장 및 큐에 추가
    @classmethod
    def PutData(cls, section: str, key: str, val: str) -> None:
        cls._kv_store[(section, key)] = val
        cls._data_queue.append(SectionKeyVal(section, key, val))

    # 데이터 큐에서 하나 추출
    @classmethod
    def GetDataSecKeyVal(cls) -> SectionKeyVal | None:
        if not cls._data_queue: return None
        return cls._data_queue.pop(0)

    # 임시 플래그 추가
    @classmethod
    def AddTempFlag(cls, event_name: str, do_event: bool) -> None:
        cls._temp_flags.append(MyFlag(event_name, do_event))

    # 임시 플래그 추출
    @classmethod
    def GetTempFlag(cls) -> MyFlag | None:
        if not cls._temp_flags: return None
        return cls._temp_flags.pop(0)

# INI 설정 파일 조작 (메모리 시뮬레이션용)
class IniFile:
    _ini_data: dict[str, dict[str, str]] = {}

    # 캐시된 설정 데이터 초기화
    def ResetIni(self) -> None:
        self._ini_data.clear()

    # 특정 섹션의 모든 키-값 반환
    def ReadAllKey(self, section: str) -> dict[str, str]:
        return dict(self._ini_data.get(section, {}))

# 암호화/복호화 유틸리티 (현재는 껍데기만 존재)
class EncryptionUtils:
    @staticmethod
    def decrypt(value: str) -> str:
        # 암호화된 SQL 대응용이나 현재는 원본 반환
        return value or ""

# 문자열 변환 및 데이터 처리 정적 메서드 모음
class QS:
    # 문자열 또는 딕셔너리를 딕셔너리로 변환 (JSON 파싱 포함)
    @staticmethod
    def Str2Map(req_param: str | dict[str, Any]) -> dict[str, Any]:
        if isinstance(req_param, dict): return req_param
        if not req_param: return {}
        return json.loads(req_param)

    # 객체를 문자열로 변환
    @staticmethod
    def Obj2Str(val: Any) -> str:
        return "" if val is None else str(val)

    # 객체를 정수로 변환 (실수형 문자열 처리 포함)
    @staticmethod
    def Obj2Int(val: Any) -> int:
        if val is None: return 0
        try:
            text = str(val).strip()
            return int(float(text)) if text else 0
        except Exception: return 0

    # 객체를 문자열 리스트로 변환
    @staticmethod
    def Obj2ListString(val: Any) -> list[str]:
        if val is None: return []
        return [str(x) for x in val] if isinstance(val, list) else [str(val)]

    # 단순 문자열 정수 변환
    @staticmethod
    def Str2Int(val: str) -> int:
        try: return int(val)
        except Exception: return 0

    # 문자열 롱 정수 변환 (Str2Int와 동일 처리)
    @staticmethod
    def Str2Long(val: str) -> int:
        return QS.Str2Int(val)

    # 문자열 등을 불리언 값으로 변환
    @staticmethod
    def ChangeBool(val: str | bool) -> bool:
        if isinstance(val, bool): return val
        return str(val).strip().lower() in {"1", "true", "y", "yes"}

    # 파일 이동 (대상 경로 폴더 자동 생성)
    @staticmethod
    def MoveFile(old_file: str, new_file: str) -> bool:
        src, dst = Path(old_file), Path(new_file)
        if not src.exists(): return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        return True

    # 파일 강제 이동 (기존 파일 있을 시 삭제 후 이동)
    @staticmethod
    def MoveFileForce(old_file: str, new_file: str) -> str:
        src, dst = Path(old_file), Path(new_file)
        if not src.exists(): return ""
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists(): dst.unlink()
        src.rename(dst)
        return str(dst)

    # 파일이 존재할 경우 삭제
    @staticmethod
    def DeleteFileIfExist(file_path: str) -> bool:
        path = Path(file_path)
        if path.exists(): path.unlink()
        return True

    # 디렉토리 내 파일 목록 조회
    @staticmethod
    def GetFileList(parent_dir: str) -> list[str]:
        base = Path(parent_dir)
        return [str(x) for x in base.iterdir()] if base.exists() else []

    # 조건에 맞는 파일 검색 (확장자 등)
    @staticmethod
    def GetResultFiles(map_obj: dict[str, Any]) -> list[str]:
        base = Path(QS.Obj2Str(map_obj.get("baseDir", ".")))
        ext = QS.Obj2Str(map_obj.get("ext", ""))
        if not base.exists(): return []
        return [str(p) for p in (base.rglob(f"*{ext}") if ext else base.rglob("*")) if p.is_file()]

    # 재귀적 파일 검색 확장형
    @staticmethod
    def GetResultFilesEx(map_obj: dict[str, Any]) -> list[str]:
        return QS.GetResultFiles(map_obj)

    # 지정된 디렉토리 내에서 조건에 맞는 파일들 탐색
    @staticmethod
    def FindLargerFiles(base_dir: str, target_dir: str, target_file: str, extension: str, _minus_hour: int) -> list[str]:
        base = Path(base_dir)
        if not base.exists(): return []
        pattern = f"*{extension}" if extension else "*"
        out: list[str] = []
        for file_path in base.rglob(pattern):
            if not file_path.is_file(): continue
            if target_dir and target_dir not in str(file_path.parent): continue
            if target_file and target_file not in file_path.name: continue
            out.append(str(file_path))
        return out

    # 파일 이름 순 정렬 후 조건에 맞는 파일 조회
    @staticmethod
    def FindLargerFilesEx(base_dir: str, last_dir: str, last_file: str, reg_exp: str, count: int) -> list[str]:
        base = Path(base_dir)
        if not base.exists(): return []
        files = sorted([p for p in base.rglob("*") if p.is_file()])
        out = []
        for file_path in files:
            if last_dir and last_dir not in str(file_path.parent): continue
            if last_file and file_path.name <= last_file: continue
            if reg_exp and reg_exp not in file_path.name: continue
            out.append(str(file_path))
            if len(out) >= count: break
        return out

    # 디렉토리 순회하며 조건 부합 파일들을 리스트에 수집
    @staticmethod
    def SearchFilesFromDir(search_dir: str, last_file: str, regexp: str, count: int, out_list: list[str]) -> None:
        base = Path(search_dir)
        if not base.exists(): return
        for file_path in sorted([p for p in base.rglob("*") if p.is_file()]):
            if last_file and file_path.name <= last_file: continue
            if regexp and regexp not in file_path.name: continue
            out_list.append(str(file_path))
            if len(out_list) >= count: break

# 파일 쓰기 및 다운로드 등 파일 시스템 조작 클라이언트
class FileClient:
    def __init__(self) -> None:
        self._read_size = 0

    # 파일 내용 쓰기
    def WriteFile(self, req_param_or_path: str, data: str | None = None) -> dict[str, Any] | bool:
        if data is not None:
            path = Path(req_param_or_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(data, encoding="utf-8")
            return True

        req_map = QS.Str2Map(req_param_or_path)
        new_file = QS.Obj2Str(req_map.get("newfile"))
        content = QS.Obj2Str(req_map.get("data"))
        if not new_file: return {"statusCode": "100", "statusMsg": "newfile is empty"}
        path = Path(new_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"statusCode": "200", "statusMsg": "OK"}

    # 파일 본문 데이터 반환 (다운로드 대용)
    def DownloadFile(self, req_param: str) -> dict[str, Any]:
        req_map = QS.Str2Map(req_param)
        target = Path(QS.Obj2Str(req_map.get("readfile", req_map.get("fullpath", ""))))
        if not target.exists() or not target.is_file():
            return {"statusCode": "100", "statusMsg": "File not found"}
        return {
            "statusCode": "200", "statusMsg": "OK", "filename": target.name,
            "content": target.read_text(encoding="utf-8", errors="ignore"),
        }

    # 디렉토리 내 파일 목록 반환 (다운로드용 목록)
    def DownloadList(self, req_param: str) -> dict[str, Any]:
        req_map = QS.Str2Map(req_param)
        base_dir = Path(QS.Obj2Str(req_map.get("baseDir", ".")))
        if not base_dir.exists(): return {"statusCode": "100", "statusMsg": "Base directory not found"}
        return {
            "statusCode": "200", "statusMsg": "OK",
            "list": [str(p) for p in base_dir.rglob("*") if p.is_file()],
        }

    # 파일 오프셋 읽기
    def ReadFile(self, full_path: str, offset: int) -> str:
        file_path = Path(full_path)
        if not file_path.exists():
            self._read_size = 0
            return ""
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        sliced = content[offset:]
        self._read_size = len(sliced)
        return sliced

    # 마지막 읽기 크기 반환
    def GetReadSize(self) -> int:
        return self._read_size

# ZIP 압축 관리 클래스
class ZipOperation:
    # 단일 파일을 임시 ZIP 파일로 압축
    def File2TempZip(self, org_file: str) -> str:
        src = Path(org_file)
        if not src.exists() or not src.is_file(): return ""
        temp_dir = Path(tempfile.gettempdir())
        zip_path = temp_dir / f"{src.stem}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.write(src, arcname=src.name)
        return str(zip_path)

# 성공 응답 생성 (FastAPI용)
def ok_response(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    out = {"statusCode": 200, "statusMsg": "OK", "datalist": [], "data": None}
    if extra: out.update(extra)
    return out

# 실패 응답 생성 (FastAPI용)
def error_response(message: str) -> dict[str, Any]:
    return {"statusCode": 100, "statusMsg": message, "datalist": [], "data": None}

# 문자열 파라미터를 딕셔너리로 변환
def to_map(req_param: str | dict[str, Any]) -> dict[str, Any]:
    return QS.Str2Map(req_param)
