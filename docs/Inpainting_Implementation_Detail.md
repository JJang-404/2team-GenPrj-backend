# 인페인팅 및 이미지 변형 기능 구현 상세

본 문서는 `changeimage` 엔드포인트에서 이미지 변형(img2img)과 인페인팅(Inpainting)을 구분하여 처리하는 로직에 대해 설명합니다.

## 1. DTO (Data Transfer Object) 변경 사항
- **파일**: `app/models/openai.py`
- **클래스**: `ChangeImageRequest`
- **추가 필드**: `mask_base64` (기본값: `""`)
- **설명**: 프론트엔드에서 전송한 마스크 이미지 데이터를 수신합니다. 이 필드의 값이 비어있지 않을 경우 서버는 자동으로 '인페인팅 모드'로 판단합니다.

## 2. 파이프라인 분기 로직 (modelApi.py)
백엔드 서버는 프록시 역할을 수행하며, `mask_base64` 유무에 따라 업스트림 AI 엔진에 전달할 데이터를 다르게 구성합니다.

### [함수: changeimage]
1. **이미지 선검증**: `image_base64`를 디코딩하여 유효한 이미지 데이터인지 확인합니다.
2. **프롬프트 보완**: `OpenAiJob`을 통해 한글 프롬프트를 영어로 번역하고 최적화합니다.
3. **페이로드 구성 (분기 핵심)**:
    - **img2img (일반 변형)**: `mask_base64`가 없을 경우 `image_base64`와 `strength`만 전송합니다.
    - **Inpainting (영역 재생성)**: `mask_base64`가 있을 경우, 이를 `mask_image_base64` 키에 담아 업스트림에 전달합니다. AI 엔진은 마스크가 있으면 인페인팅 파이프라인을 가동합니다.
4. **결과 프록시**: 업스트림에서 생성된 바이너리 이미지를 프론트엔드에 그대로 반환합니다.

## 3. 마스크 컨벤션 (Mask Convention)
프론트엔드와 백엔드 간의 마스크 이미지 규칙은 다음과 같습니다.
- **흰색 (255, 255, 255)**: AI가 새로운 이미지를 생성할 영역 (배경 등).
- **검은색 (0, 0, 0)**: 원본 이미지를 그대로 보존할 영역 (피사체 등).
- **참고**: Stable Diffusion 표준 인페인팅 모델의 규격과 동일하므로 별도의 이미지 반전 로직 없이 처리가 가능합니다.

## 4. 실행 및 테스트 방법
- **엔드포인트**: `POST /addhelper/model/changeimage`
- **요청 예시**:
```json
{
  "prompt": "change background to a beautiful beach",
  "image_base64": "...",
  "mask_base64": "...", 
  "strength": 0.3
}
```
*`mask_base64`를 생략하거나 빈 문자열로 보내면 전체 이미지 변형(img2img)이 수행됩니다.*

---
*최종 수정일: 2026.04.10*
*작성자: Gemini Code Assist*