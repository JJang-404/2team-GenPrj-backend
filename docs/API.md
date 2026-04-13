# React API 호출 가이드

이 문서는 현재 백엔드의 REST API를 React에서 호출하는 방법을 정리한 문서입니다.

현재 제공되는 주요 API는 아래 3개입니다.

1. GET /addhelper/model/test
2. GET /addhelper/model/generate
3. POST /addhelper/model/changeimage

generate와 changeimage는 공통으로 아래 규칙을 따릅니다.

1. prompt는 기본 입력값입니다.
2. positive_prompt와 negative_prompt는 선택 입력값입니다.
3. positive_prompt 또는 negative_prompt가 비어 있으면 백엔드가 OpenAI를 이용해 보완합니다.
4. 모델 서버에는 항상 positive_prompt와 negative_prompt 둘 다 전달합니다.

중요한 점은 응답 형태가 두 종류라는 것입니다.

1. test는 JSON을 반환합니다.
2. generate와 changeimage는 성공 시 이미지 바이너리 Blob을 반환합니다.
3. generate와 changeimage는 실패 시 JSON 에러를 반환합니다.

## 1. 기본 서버 주소

개발 환경 예시:

```text
https://gen-proj.duckdns.org
```

React에서는 보통 아래처럼 API 기본 주소를 하나로 관리하는 것이 좋습니다.

```ts
export const API_BASE_URL = 'https://gen-proj.duckdns.org';
```

## 2. 응답 규칙

### JSON 응답 형식

일반 JSON 응답은 아래 구조를 사용합니다.

```json
{
	"statusCode": 200,
	"statusMsg": "OK",
	"datalist": [],
	"data": null
}
```

논리 오류인 경우에도 JSON으로 응답하며, HTTP 상태코드가 아니라 아래 바디 값으로 판단합니다.

```json
{
	"statusCode": 100,
	"statusMsg": "오류 원인",
	"datalist": [],
	"data": null
}
```

### 이미지 응답 형식

generate와 changeimage는 성공 시 아래처럼 이미지 바이너리를 반환합니다.

```text
HTTP/1.1 200 OK
Content-Type: image/png
```

React에서는 이 응답을 Blob으로 받아서 화면에 표시해야 합니다.

## 3. 가장 단순한 fetch 호출 예시

### 3-1. test 호출

```ts
const API_BASE_URL = 'https://gen-proj.duckdns.org';

export async function testConnection() {
	const response = await fetch(`${API_BASE_URL}/addhelper/model/test`);

	if (!response.ok) {
		throw new Error(`HTTP ${response.status}`);
	}

	const result = await response.json();
	return result;
}
```

사용 예시:

```ts
const result = await testConnection();
console.log(result.statusCode);
console.log(result.statusMsg);
console.log(result.data);
```

위 예시는 콘솔에만 출력합니다. 화면에 바로 보이게 하려면 state에 넣어서 렌더링해야 합니다.

```tsx
import { useState } from 'react';

const API_BASE_URL = 'https://gen-proj.duckdns.org';

async function testConnection() {
	const response = await fetch(`${API_BASE_URL}/addhelper/model/test`);
	if (!response.ok) {
		throw new Error(`HTTP ${response.status}`);
	}
	return await response.json();
}

export default function BackendCheck() {
	const [message, setMessage] = useState('');
	const [errorMsg, setErrorMsg] = useState('');

	const handleCheckBackend = async () => {
		try {
			setErrorMsg('');
			const result = await testConnection();
			setMessage(result.data || result.statusMsg);
		} catch (error) {
			const message = error instanceof Error ? error.message : '백엔드 확인 실패';
			setErrorMsg(message);
		}
	};

	return (
		<div>
			<button onClick={handleCheckBackend}>백엔드 확인</button>
			{message && <p>{message}</p>}
			{errorMsg && <p style={{ color: 'red' }}>{errorMsg}</p>}
		</div>
	);
	}
```

### 3-2. generate 호출

generate는 성공 시 이미지 바이너리를 반환하므로 response.json()이 아니라 response.blob()을 사용해야 합니다.

```ts
const API_BASE_URL = 'https://gen-proj.duckdns.org';

export async function generateImage(
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
	const response = await fetch(`${API_BASE_URL}/addhelper/model/generate?${query.toString()}`);

	const contentType = response.headers.get('content-type') || '';

	if (!response.ok) {
		if (contentType.includes('application/json')) {
			const errorBody = await response.json();
			throw new Error(errorBody.statusMsg || '이미지 생성 실패');
		}
		throw new Error(`HTTP ${response.status}`);
	}

	if (contentType.startsWith('image/')) {
		const imageBlob = await response.blob();
		return imageBlob;
	}

	if (contentType.includes('application/json')) {
		const errorBody = await response.json();
		throw new Error(errorBody.statusMsg || '이미지 생성 실패');
	}

	throw new Error('알 수 없는 응답 형식입니다.');
}
```

사용 예시:

```ts
const blob = await generateImage(
	'맛있는 크루아상과 커피',
	'fresh croissant, warm coffee, cozy cafe, realistic food photography',
	'blurry, low quality, text, watermark'
);
const imageUrl = URL.createObjectURL(blob);

setPreviewUrl(imageUrl);
```

### 3-3. changeimage 호출

changeimage는 JSON으로 요청하고, 성공 시 이미지 Blob을 반환합니다.

```ts
const API_BASE_URL = 'https://gen-proj.duckdns.org';

type ChangeImagePayload = {
	prompt: string;
	positive_prompt?: string;
	negative_prompt?: string;
	image_base64: string;
	strength?: number;
};

export async function changeImage(payload: ChangeImagePayload) {
	const response = await fetch(`${API_BASE_URL}/addhelper/model/changeimage`, {
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
		if (contentType.includes('application/json')) {
			const errorBody = await response.json();
			throw new Error(errorBody.statusMsg || '이미지 변환 실패');
		}
		throw new Error(`HTTP ${response.status}`);
	}

	if (contentType.startsWith('image/')) {
		return await response.blob();
	}

	if (contentType.includes('application/json')) {
		const errorBody = await response.json();
		throw new Error(errorBody.statusMsg || '이미지 변환 실패');
	}

	throw new Error('알 수 없는 응답 형식입니다.');
}
```

## 4. React에서 파일을 base64로 변환하는 방법

changeimage 호출 전에는 업로드한 이미지를 base64 문자열로 바꿔야 합니다. 필요하면 positive_prompt와 negative_prompt도 함께 넘길 수 있습니다.

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

백엔드에서는 앞부분 data:image/png;base64, 가 있어도 처리합니다.

## 5. React 컴포넌트 예시

아래는 가장 단순한 예시입니다.

```tsx
import { useState } from 'react';

const API_BASE_URL = 'https://gen-proj.duckdns.org';

function fileToBase64(file: File): Promise<string> {
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
		reader.onerror = () => reject(new Error('파일 읽기 실패'));
		reader.readAsDataURL(file);
	});
}

async function callGenerate(prompt: string) {
	const query = new URLSearchParams({ prompt });
	const response = await fetch(`${API_BASE_URL}/addhelper/model/generate?${query.toString()}`);
	const contentType = response.headers.get('content-type') || '';

	if (!response.ok || !contentType.startsWith('image/')) {
		const errorBody = contentType.includes('application/json') ? await response.json() : null;
		throw new Error(errorBody?.statusMsg || '이미지 생성 실패');
	}

	return await response.blob();
}

async function callChangeImage(prompt: string, imageBase64: string, strength: number) {
	const response = await fetch(`${API_BASE_URL}/addhelper/model/changeimage`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify({
			prompt,
			image_base64: imageBase64,
			strength,
		}),
	});

	const contentType = response.headers.get('content-type') || '';

	if (!response.ok || !contentType.startsWith('image/')) {
		const errorBody = contentType.includes('application/json') ? await response.json() : null;
		throw new Error(errorBody?.statusMsg || '이미지 변환 실패');
	}

	return await response.blob();
}

export default function ImageDemo() {
	const [prompt, setPrompt] = useState('맛있는 크루아상과 커피');
	const [file, setFile] = useState<File | null>(null);
	const [imageUrl, setImageUrl] = useState('');
	const [loading, setLoading] = useState(false);
	const [errorMsg, setErrorMsg] = useState('');

	const handleGenerate = async () => {
		try {
			setLoading(true);
			setErrorMsg('');

			const blob = await callGenerate(prompt);
			const url = URL.createObjectURL(blob);
			setImageUrl(url);
		} catch (error) {
			const message = error instanceof Error ? error.message : '오류 발생';
			setErrorMsg(message);
		} finally {
			setLoading(false);
		}
	};

	const handleChangeImage = async () => {
		if (!file) {
			setErrorMsg('이미지 파일을 먼저 선택해 주세요.');
			return;
		}

		try {
			setLoading(true);
			setErrorMsg('');

			const imageBase64 = await fileToBase64(file);
			const blob = await callChangeImage(prompt, imageBase64, 0.45);
			const url = URL.createObjectURL(blob);
			setImageUrl(url);
		} catch (error) {
			const message = error instanceof Error ? error.message : '오류 발생';
			setErrorMsg(message);
		} finally {
			setLoading(false);
		}
	};

	return (
		<div>
			<h1>이미지 API 테스트</h1>

			<input
				value={prompt}
				onChange={(event) => setPrompt(event.target.value)}
				placeholder="프롬프트를 입력하세요"
			/>

			<input
				type="file"
				accept="image/*"
				onChange={(event) => setFile(event.target.files?.[0] ?? null)}
			/>

			<button onClick={handleGenerate} disabled={loading}>
				새 이미지 생성
			</button>

			<button onClick={handleChangeImage} disabled={loading}>
				업로드 이미지 변환
			</button>

			{loading && <p>처리 중...</p>}
			{errorMsg && <p style={{ color: 'red' }}>{errorMsg}</p>}
			{imageUrl && <img src={imageUrl} alt="결과 이미지" style={{ maxWidth: 480 }} />}
		</div>
	);
}
```

## 6. Axios를 사용할 때 주의점

Axios를 쓰는 경우 이미지 응답은 responseType을 blob으로 지정해야 합니다.

```ts
import axios from 'axios';

const API_BASE_URL = 'https://gen-proj.duckdns.org';

export async function generateImageByAxios(prompt: string) {
	const response = await axios.get(`${API_BASE_URL}/addhelper/model/generate`, {
		params: { prompt },
		responseType: 'blob',
	});

	return response.data;
}
```

다만 이 API는 실패 시 JSON이 올 수 있으므로, 실제 운영 코드에서는 response header의 content-type 검사나 interceptor 처리가 필요합니다.

## 7. 프론트엔드 구현 시 권장 사항

1. JSON API와 이미지 API를 분리해서 생각하는 것이 좋습니다.
2. 이미지 응답은 Blob으로 받고 URL.createObjectURL로 화면에 표시합니다.
3. 업로드 이미지는 FileReader로 base64 문자열로 변환 후 전송합니다.
4. 에러 메시지는 JSON의 statusMsg를 우선 사용합니다.
5. 서버 주소는 상수 또는 .env 파일로 분리하는 것이 좋습니다.

## 8. 실제 호출 주소 요약

```text
GET  /addhelper/model/test
GET  /addhelper/model/generate?prompt=문자열
POST /addhelper/model/changeimage
```

POST /addhelper/model/changeimage 요청 바디:

```json
{
	"prompt": "카툰 스타일로 바꿔주세요",
	"image_base64": "data:image/png;base64,... 또는 순수 base64 문자열",
	"strength": 0.45
}
```
