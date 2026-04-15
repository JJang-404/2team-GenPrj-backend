# React API 호출 가이드

이 문서는 현재 백엔드의 REST API를 React에서 호출하는 방법을 정리한 문서입니다.

현재 백엔드는 두 가지 방식의 API를 제공합니다.

1. `_sync` 동기 API
2. `.../jobs` 비동기 API

권장 사항은 아래와 같습니다.

1. `generate_sync`, `changeimage_sync`, `makebgimage_sync`, `makebgimageollama_sync`, `generatecomfyui_sync`, `changeimagecomfyui_sync`, `makebgimagecomfyui_sync`는 테스트 또는 짧은 작업에만 사용합니다.
2. 실제 서비스 화면에서는 `.../jobs` 비동기 API 사용을 권장합니다.
3. 긴 작업을 동기 API로 호출하면 프론트보다 앞단의 서버나 게이트웨이에서 504가 발생할 수 있습니다.

## 1. 기본 서버 주소

개발 환경 예시:

```text
https://gen-proj.duckdns.org
```

React에서는 보통 아래처럼 API 기본 주소를 하나로 관리하는 것이 좋습니다.

```ts
export const API_BASE_URL = 'https://gen-proj.duckdns.org';
```

## 2. 제공 API 목록

### 2-1. 공통 API

```text
GET  /addhelper/model/test
```

### 2-2. 동기 API

```text
GET  /addhelper/model/generate_sync
POST /addhelper/model/changeimage_sync
POST /addhelper/model/makebgimage_sync
POST /addhelper/model/makebgimageollama_sync

GET  /addhelper/model/generatecomfyui_sync
POST /addhelper/model/changeimagecomfyui_sync
POST /addhelper/model/makebgimagecomfyui_sync
```

### 2-3. 비동기 API

```text
POST /addhelper/model/generate/jobs
GET  /addhelper/model/generate/jobs/{job_id}
GET  /addhelper/model/generate/jobs/{job_id}/result

POST /addhelper/model/changeimage/jobs
GET  /addhelper/model/changeimage/jobs/{job_id}
GET  /addhelper/model/changeimage/jobs/{job_id}/result

POST /addhelper/model/makebgimage/jobs
GET  /addhelper/model/makebgimage/jobs/{job_id}
GET  /addhelper/model/makebgimage/jobs/{job_id}/result

POST /addhelper/model/makebgimageollama/jobs
GET  /addhelper/model/makebgimageollama/jobs/{job_id}
GET  /addhelper/model/makebgimageollama/jobs/{job_id}/result

POST /addhelper/model/generatecomfyui/jobs
GET  /addhelper/model/generatecomfyui/jobs/{job_id}
GET  /addhelper/model/generatecomfyui/jobs/{job_id}/result

POST /addhelper/model/changeimagecomfyui/jobs
GET  /addhelper/model/changeimagecomfyui/jobs/{job_id}
GET  /addhelper/model/changeimagecomfyui/jobs/{job_id}/result

POST /addhelper/model/makebgimagecomfyui/jobs
GET  /addhelper/model/makebgimagecomfyui/jobs/{job_id}
GET  /addhelper/model/makebgimagecomfyui/jobs/{job_id}/result
```

## 3. 요청 규칙

공통 규칙:

1. `prompt`는 기본 입력값입니다.
2. `positive_prompt`와 `negative_prompt`는 선택 입력값입니다.
3. 비어 있으면 백엔드가 OpenAI 또는 Ollama 기반으로 보완할 수 있습니다.
4. 모델 서버에는 항상 `positive_prompt`와 `negative_prompt` 둘 다 전달됩니다.

이미지 관련 규칙:

1. `changeimage_sync`, `makebgimage_sync`, `makebgimageollama_sync`, `changeimagecomfyui_sync`, `makebgimagecomfyui_sync`와 해당 jobs API는 `image_base64`가 필요합니다.
2. `image_base64`는 `data:image/png;base64,...` 형식과 순수 base64 문자열 둘 다 허용합니다.

ComfyUI 프롬프트 규칙:

1. ComfyUI API는 최종적으로 `positive_prompt`와 `negative_prompt`만 사용합니다.
2. `prompt`는 선택값이며, 전달하면 백엔드가 OpenAI를 통해 `positive/negative`를 보완합니다.
3. `prompt`를 비우는 경우 `positive_prompt`는 필수입니다.

## 4. 응답 규칙

### 4-1. 일반 JSON 응답

일부 일반 JSON 응답은 아래 구조를 사용합니다.

```json
{
	"statusCode": 200,
	"statusMsg": "OK",
	"datalist": [],
	"data": null
}
```

논리 오류인 경우에도 아래 같은 JSON이 내려올 수 있습니다.

```json
{
	"statusCode": 100,
	"statusMsg": "오류 원인",
	"datalist": [],
	"data": null
}
```

### 4-2. 동기 이미지 응답

동기 API는 성공 시 이미지 바이너리를 반환합니다.

```text
HTTP/1.1 200 OK
Content-Type: image/png
```

실패 시에는 JSON 에러를 반환합니다.

### 4-3. 비동기 jobs 응답

작업 생성 응답:

```json
{
	"job_id": "e2a1e3fe-744a-439d-a6d3-870908e234b2",
	"status": "queued"
}
```

작업 상태 응답:

```json
{
	"job_id": "e2a1e3fe-744a-439d-a6d3-870908e234b2",
	"status": "running",
	"error": null
}
```

상태 값:

1. `queued`
2. `running`
3. `done`
4. `failed`

작업 결과 조회 응답:

1. `done`이면 이미지 바이너리 반환
2. `queued` 또는 `running`이면 `409 Conflict`
3. `failed`면 `500 Internal Server Error`
4. 존재하지 않는 `job_id`면 `404 Not Found`

## 5. 가장 단순한 fetch 호출 예시

### 5-1. test 호출

```ts
const API_BASE_URL = 'https://gen-proj.duckdns.org';

export async function testConnection() {
	const response = await fetch(`${API_BASE_URL}/addhelper/model/test`);

	if (!response.ok) {
		throw new Error(`HTTP ${response.status}`);
	}

	return await response.json();
}
```

### 5-2. 공통 JSON 에러 파서

```ts
async function parseJsonError(response: Response, fallbackMessage: string) {
	const contentType = response.headers.get('content-type') || '';
	if (contentType.includes('application/json')) {
		const errorBody = await response.json();
		throw new Error(errorBody.statusMsg || errorBody.detail || fallbackMessage);
	}
	throw new Error(fallbackMessage);
}
```

### 5-3. generate_sync 호출

```ts
export async function generateImageSync(
	prompt: string,
	positivePrompt?: string,
	negativePrompt?: string,
) {
	const query = new URLSearchParams({ prompt });
	if (positivePrompt) {
		query.set('positive_prompt', positivePrompt);
	}
	if (negativePrompt) {
		query.set('negative_prompt', negativePrompt);
	}

	const response = await fetch(
		`${API_BASE_URL}/addhelper/model/generate_sync?${query.toString()}`,
	);
	const contentType = response.headers.get('content-type') || '';

	if (!response.ok) {
		await parseJsonError(response, `HTTP ${response.status}`);
	}

	if (contentType.startsWith('image/')) {
		return await response.blob();
	}

	await parseJsonError(response, '이미지 생성 실패');
	throw new Error('이미지 생성 실패');
}
```

### 5-4. changeimage_sync 호출

```ts
type ChangeImagePayload = {
	prompt: string;
	positive_prompt?: string;
	negative_prompt?: string;
	image_base64: string;
	strength?: number;
};

export async function changeImageSync(payload: ChangeImagePayload) {
	const response = await fetch(`${API_BASE_URL}/addhelper/model/changeimage_sync`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify({
			prompt: payload.prompt,
			positive_prompt: payload.positive_prompt,
			negative_prompt: payload.negative_prompt,
			image_base64: payload.image_base64,
			strength: payload.strength ?? 0.45,
		}),
	});

	const contentType = response.headers.get('content-type') || '';

	if (!response.ok) {
		await parseJsonError(response, `HTTP ${response.status}`);
	}

	if (contentType.startsWith('image/')) {
		return await response.blob();
	}

	await parseJsonError(response, '이미지 변환 실패');
	throw new Error('이미지 변환 실패');
}
```

### 5-5. makebgimage_sync 호출

```ts
type MakeBgImagePayload = {
	prompt: string;
	image_base64: string;
	task_prompt?: string;
	positive_prompt?: string;
	negative_prompt?: string;
};

export async function makeBgImageSync(payload: MakeBgImagePayload) {
	const response = await fetch(`${API_BASE_URL}/addhelper/model/makebgimage_sync`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify({
			prompt: payload.prompt,
			image_base64: payload.image_base64,
			task_prompt: payload.task_prompt ?? '<DETAILED_CAPTION>',
			positive_prompt: payload.positive_prompt,
			negative_prompt: payload.negative_prompt,
		}),
	});

	const contentType = response.headers.get('content-type') || '';

	if (!response.ok) {
		await parseJsonError(response, `HTTP ${response.status}`);
	}

	if (contentType.startsWith('image/')) {
		return await response.blob();
	}

	await parseJsonError(response, '배경 생성 실패');
	throw new Error('배경 생성 실패');
}
```

### 5-6. makebgimageollama_sync 호출

```ts
export async function makeBgImageOllamaSync(payload: MakeBgImagePayload) {
	const response = await fetch(`${API_BASE_URL}/addhelper/model/makebgimageollama_sync`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify({
			prompt: payload.prompt,
			image_base64: payload.image_base64,
			task_prompt: payload.task_prompt ?? '<DETAILED_CAPTION>',
			positive_prompt: payload.positive_prompt,
			negative_prompt: payload.negative_prompt,
		}),
	});

	const contentType = response.headers.get('content-type') || '';

	if (!response.ok) {
		await parseJsonError(response, `HTTP ${response.status}`);
	}

	if (contentType.startsWith('image/')) {
		return await response.blob();
	}

	await parseJsonError(response, 'Ollama 배경 생성 실패');
	throw new Error('Ollama 배경 생성 실패');
}
```

### 5-7. generatecomfyui_sync 호출

```ts
export async function generateImageComfyUiSync(
	prompt?: string,
	positivePrompt?: string,
	negativePrompt?: string,
) {
	const query = new URLSearchParams();
	if (prompt) {
		query.set('prompt', prompt);
	}
	if (positivePrompt) {
		query.set('positive_prompt', positivePrompt);
	}
	if (negativePrompt) {
		query.set('negative_prompt', negativePrompt);
	}

	const response = await fetch(
		`${API_BASE_URL}/addhelper/model/generatecomfyui_sync?${query.toString()}`,
	);
	const contentType = response.headers.get('content-type') || '';

	if (!response.ok) {
		await parseJsonError(response, `HTTP ${response.status}`);
	}

	if (contentType.startsWith('image/')) {
		return await response.blob();
	}

	await parseJsonError(response, 'ComfyUI 이미지 생성 실패');
	throw new Error('ComfyUI 이미지 생성 실패');
}
```

### 5-8. changeimagecomfyui_sync 호출

```ts
type ChangeImageComfyUiPayload = {
	prompt?: string;
	positive_prompt?: string;
	negative_prompt?: string;
	image_base64: string;
	strength?: number;
};

export async function changeImageComfyUiSync(payload: ChangeImageComfyUiPayload) {
	const response = await fetch(`${API_BASE_URL}/addhelper/model/changeimagecomfyui_sync`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify({
			prompt: payload.prompt,
			positive_prompt: payload.positive_prompt,
			negative_prompt: payload.negative_prompt,
			image_base64: payload.image_base64,
			strength: payload.strength ?? 0.45,
		}),
	});

	const contentType = response.headers.get('content-type') || '';

	if (!response.ok) {
		await parseJsonError(response, `HTTP ${response.status}`);
	}

	if (contentType.startsWith('image/')) {
		return await response.blob();
	}

	await parseJsonError(response, 'ComfyUI 이미지 변환 실패');
	throw new Error('ComfyUI 이미지 변환 실패');
}
```

### 5-9. makebgimagecomfyui_sync 호출

```ts
export async function makeBgImageComfyUiSync(payload: MakeBgImagePayload) {
	const response = await fetch(`${API_BASE_URL}/addhelper/model/makebgimagecomfyui_sync`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify({
			prompt: payload.prompt,
			image_base64: payload.image_base64,
			task_prompt: payload.task_prompt ?? '<DETAILED_CAPTION>',
			positive_prompt: payload.positive_prompt,
			negative_prompt: payload.negative_prompt,
		}),
	});

	const contentType = response.headers.get('content-type') || '';

	if (!response.ok) {
		await parseJsonError(response, `HTTP ${response.status}`);
	}

	if (contentType.startsWith('image/')) {
		return await response.blob();
	}

	await parseJsonError(response, 'ComfyUI 배경 생성 실패');
	throw new Error('ComfyUI 배경 생성 실패');
}
```

## 6. 비동기 jobs API 호출 예시

비동기 API는 아래 순서로 호출합니다.

1. `POST .../jobs`로 `job_id` 받기
2. `GET .../jobs/{job_id}`를 1~2초 간격으로 폴링
3. `status === 'done'`이면 `GET .../jobs/{job_id}/result` 호출
4. `status === 'failed'`이면 `error` 메시지 노출

### 6-1. 공통 폴링 유틸

```ts
async function sleep(ms: number) {
	return await new Promise((resolve) => setTimeout(resolve, ms));
}

export async function runImageJob<TPayload>(
	jobCreatePath: string,
	payload: TPayload,
	options?: { pollIntervalMs?: number; timeoutMs?: number },
) {
	const pollIntervalMs = options?.pollIntervalMs ?? 1500;
	const timeoutMs = options?.timeoutMs ?? 10 * 60 * 1000;

	const createRes = await fetch(`${API_BASE_URL}${jobCreatePath}`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify(payload),
	});

	if (!createRes.ok) {
		await parseJsonError(createRes, `job create failed: ${createRes.status}`);
	}

	const createJson = await createRes.json();
	const jobId = createJson.job_id as string;
	if (!jobId) {
		throw new Error('job_id가 없습니다.');
	}

	const startedAt = Date.now();

	while (true) {
		if (Date.now() - startedAt > timeoutMs) {
			throw new Error('작업 대기 시간이 초과되었습니다.');
		}

		const statusRes = await fetch(`${API_BASE_URL}${jobCreatePath}/${jobId}`);
		if (!statusRes.ok) {
			await parseJsonError(statusRes, `status check failed: ${statusRes.status}`);
		}

		const statusJson = await statusRes.json();
		if (statusJson.status === 'done') {
			const resultRes = await fetch(`${API_BASE_URL}${jobCreatePath}/${jobId}/result`);
			if (!resultRes.ok) {
				await parseJsonError(resultRes, `result fetch failed: ${resultRes.status}`);
			}
			return await resultRes.blob();
		}

		if (statusJson.status === 'failed') {
			throw new Error(statusJson.error || '이미지 작업이 실패했습니다.');
		}

		await sleep(pollIntervalMs);
	}
}
```

### 6-2. generate jobs 호출

```ts
export async function generateImageAsync(
	prompt: string,
	positive_prompt?: string,
	negative_prompt?: string,
) {
	return await runImageJob('/addhelper/model/generate/jobs', {
		prompt,
		positive_prompt,
		negative_prompt,
	});
}
```

### 6-3. changeimage jobs 호출

```ts
export async function changeImageAsync(payload: ChangeImagePayload) {
	return await runImageJob('/addhelper/model/changeimage/jobs', {
		prompt: payload.prompt,
		positive_prompt: payload.positive_prompt,
		negative_prompt: payload.negative_prompt,
		image_base64: payload.image_base64,
		strength: payload.strength ?? 0.45,
	});
}
```

### 6-4. makebgimage jobs 호출

```ts
export async function makeBgImageAsync(payload: MakeBgImagePayload) {
	return await runImageJob('/addhelper/model/makebgimage/jobs', {
		prompt: payload.prompt,
		image_base64: payload.image_base64,
		task_prompt: payload.task_prompt ?? '<DETAILED_CAPTION>',
		positive_prompt: payload.positive_prompt,
		negative_prompt: payload.negative_prompt,
	});
}
```

### 6-5. makebgimageollama jobs 호출

```ts
export async function makeBgImageOllamaAsync(payload: MakeBgImagePayload) {
	return await runImageJob('/addhelper/model/makebgimageollama/jobs', {
		prompt: payload.prompt,
		image_base64: payload.image_base64,
		task_prompt: payload.task_prompt ?? '<DETAILED_CAPTION>',
		positive_prompt: payload.positive_prompt,
		negative_prompt: payload.negative_prompt,
	});
}
```

### 6-6. generatecomfyui jobs 호출

```ts
export async function generateImageComfyUiAsync(
	prompt?: string,
	positive_prompt?: string,
	negative_prompt?: string,
) {
	return await runImageJob('/addhelper/model/generatecomfyui/jobs', {
		prompt,
		positive_prompt,
		negative_prompt,
	});
}
```

### 6-7. changeimagecomfyui jobs 호출

```ts
export async function changeImageComfyUiAsync(payload: ChangeImageComfyUiPayload) {
	return await runImageJob('/addhelper/model/changeimagecomfyui/jobs', {
		prompt: payload.prompt,
		positive_prompt: payload.positive_prompt,
		negative_prompt: payload.negative_prompt,
		image_base64: payload.image_base64,
		strength: payload.strength ?? 0.45,
	});
}
```

### 6-8. makebgimagecomfyui jobs 호출

```ts
export async function makeBgImageComfyUiAsync(payload: MakeBgImagePayload) {
	return await runImageJob('/addhelper/model/makebgimagecomfyui/jobs', {
		prompt: payload.prompt,
		image_base64: payload.image_base64,
		task_prompt: payload.task_prompt ?? '<DETAILED_CAPTION>',
		positive_prompt: payload.positive_prompt,
		negative_prompt: payload.negative_prompt,
	});
}
```

## 7. React에서 파일을 base64로 변환하는 방법

```ts
export function fileToBase64(file: File): Promise<string> {
	return new Promise((resolve, reject) => {
		const reader = new FileReader();

		reader.onload = () => {
			const result = reader.result;
			if (typeof result !== 'string') {
				reject(new Error('파일을 읽지 못했습니다.'));
				return;
			}
			resolve(result);
		};

		reader.onerror = () => {
			reject(new Error('파일 읽기 실패'));
		};

		reader.readAsDataURL(file);
	});
}
```

이 함수는 아래와 같은 값을 반환합니다.

```text
data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...
```

백엔드에서는 앞부분 `data:image/png;base64,` 가 있어도 처리합니다.

## 8. Axios 사용 예시

```ts
import axios from 'axios';

const API_BASE_URL = 'https://gen-proj.duckdns.org';

export async function generateImageSyncByAxios(prompt: string) {
	const response = await axios.get(`${API_BASE_URL}/addhelper/model/generate_sync`, {
		params: { prompt },
		responseType: 'blob',
	});

	return response.data;
}
```

주의:

1. 동기 API는 실패 시 JSON이 올 수 있습니다.
2. Axios에서는 `responseType: 'blob'`과 오류 응답 처리 로직을 함께 고려해야 합니다.

## 9. 프론트엔드 구현 시 권장 사항

1. 실제 서비스에서는 동기 API보다 jobs API를 우선 사용합니다.
2. 이미지 응답은 Blob으로 받고 `URL.createObjectURL`로 표시합니다.
3. 업로드 이미지는 FileReader로 base64 문자열로 변환 후 전송합니다.
4. jobs API의 상태값은 `queued`, `running`, `done`, `failed` 네 가지만 사용합니다.
5. `failed`이면 `error`, `detail`, `statusMsg` 순서로 메시지를 해석하면 안전합니다.
6. 서버 주소는 상수 또는 `.env` 파일로 분리하는 것이 좋습니다.

## 10. 실제 호출 주소 요약

```text
GET  /addhelper/model/test

GET  /addhelper/model/generate_sync?prompt=문자열&positive_prompt=선택&negative_prompt=선택
POST /addhelper/model/changeimage_sync
POST /addhelper/model/makebgimage_sync
POST /addhelper/model/makebgimageollama_sync

GET  /addhelper/model/generatecomfyui_sync?prompt=선택&positive_prompt=선택&negative_prompt=선택
POST /addhelper/model/changeimagecomfyui_sync
POST /addhelper/model/makebgimagecomfyui_sync

POST /addhelper/model/generate/jobs
GET  /addhelper/model/generate/jobs/{job_id}
GET  /addhelper/model/generate/jobs/{job_id}/result

POST /addhelper/model/changeimage/jobs
GET  /addhelper/model/changeimage/jobs/{job_id}
GET  /addhelper/model/changeimage/jobs/{job_id}/result

POST /addhelper/model/makebgimage/jobs
GET  /addhelper/model/makebgimage/jobs/{job_id}
GET  /addhelper/model/makebgimage/jobs/{job_id}/result

POST /addhelper/model/makebgimageollama/jobs
GET  /addhelper/model/makebgimageollama/jobs/{job_id}
GET  /addhelper/model/makebgimageollama/jobs/{job_id}/result

POST /addhelper/model/generatecomfyui/jobs
GET  /addhelper/model/generatecomfyui/jobs/{job_id}
GET  /addhelper/model/generatecomfyui/jobs/{job_id}/result

POST /addhelper/model/changeimagecomfyui/jobs
GET  /addhelper/model/changeimagecomfyui/jobs/{job_id}
GET  /addhelper/model/changeimagecomfyui/jobs/{job_id}/result

POST /addhelper/model/makebgimagecomfyui/jobs
GET  /addhelper/model/makebgimagecomfyui/jobs/{job_id}
GET  /addhelper/model/makebgimagecomfyui/jobs/{job_id}/result
```

`changeimage_sync` 요청 바디 예시:

```json
{
"prompt": "카툰 스타일로 바꿔주세요",
	"positive_prompt": "cartoon style, clean outlines",
	"negative_prompt": "blurry, low quality",
	"image_base64": "data:image/png;base64,... 또는 순수 base64 문자열",
	"strength": 0.45
}
```

`makebgimage_sync` 또는 `makebgimageollama_sync` 또는 `makebgimagecomfyui_sync` 요청 바디 예시:

```json
{
	"prompt": "카페 배경으로 만들어주세요",
	"image_base64": "data:image/png;base64,... 또는 순수 base64 문자열",
	"task_prompt": "<DETAILED_CAPTION>",
	"positive_prompt": "warm indoor cafe, empty background",
	"negative_prompt": "person, people, text, watermark"
}
```
