# 공통 유틸리티 함수 정의 파일
from __future__ import annotations
import configparser
import os
from datetime import datetime
from typing import TYPE_CHECKING, Any, TypeVar
from fastapi import Request
from pydantic import BaseModel
# 올바른 경로로 수정
from app.common.defines import M18_BEND_INI_PATH

SchemaType = TypeVar("SchemaType", bound=BaseModel)

# 디렉토리가 없으면 생성
def Ensure_Directory(dirPath: str) -> None:
    os.makedirs(dirPath, exist_ok=True)

# INI 설정 파일 객체 로드
def Get_Ini_Config() -> configparser.ConfigParser:
    configData = configparser.ConfigParser()
    configData.read(M18_BEND_INI_PATH, encoding="utf-8")
    return configData

# INI 문자열 값 조회
def Get_Ini_Value(sectionName: str, keyName: str, fallback: str = "") -> str:
    configData = Get_Ini_Config()
    return configData.get(sectionName, keyName, fallback=fallback)

# INI 정수 값 조회
def Get_Ini_Int_Value(sectionName: str, keyName: str, fallbackValue: int) -> int:
    configData = Get_Ini_Config()
    return configData.getint(sectionName, keyName, fallback=fallbackValue)

# INI 값 설정 및 파일 저장
def Set_Ini_Value(sectionName: str, keyName: str, valueData: str | int | float | bool) -> None:
    configData = Get_Ini_Config()
    if not configData.has_section(sectionName):
        configData.add_section(sectionName)
    configData.set(sectionName, keyName, str(valueData))
    with open(M18_BEND_INI_PATH, "w", encoding="utf-8") as fileData:
        configData.write(fileData)

# 현재 일시 반환
def Get_Now() -> datetime:
    return datetime.now()

# 데이터 객체를 Pydantic 스키마 모델로 변환
def To_Schema(sourceData: Any, schemaType: type[SchemaType]) -> SchemaType:
    return schemaType.model_validate(sourceData, from_attributes=True)

