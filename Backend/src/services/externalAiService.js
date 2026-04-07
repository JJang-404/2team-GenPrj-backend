import path from 'path';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';
import { InferenceClient } from '@huggingface/inference';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '../../..');
const pythonBin = path.resolve(projectRoot, '.venv/bin/python');
const alphaMaskScript = path.resolve(__dirname, '../../scripts/apply_alpha_mask.py');

function getHfToken() {
  return process.env.HF_TOKEN || process.env.HUGGINGFACE_API_KEY || process.env.HUGGINGFACEHUB_API_TOKEN || '';
}

function getOpenAiKey() {
  return process.env.OPENAI_API_KEY || '';
}

function getInferenceClient() {
  const token = getHfToken();
  if (!token) {
    throw new Error('HF_TOKEN 또는 HUGGINGFACE_API_KEY가 필요합니다.');
  }
  return new InferenceClient(token);
}

function dataUrlToParts(dataUrl) {
  const match = /^data:(.+?);base64,(.+)$/.exec(dataUrl);
  if (!match) {
    throw new Error('유효한 data URL 형식이 아닙니다.');
  }
  return {
    mimeType: match[1],
    buffer: Buffer.from(match[2], 'base64'),
  };
}

function bufferToDataUrl(buffer, mimeType = 'image/png') {
  return `data:${mimeType};base64,${buffer.toString('base64')}`;
}

function buildBlobFromDataUrl(dataUrl) {
  const { mimeType, buffer } = dataUrlToParts(dataUrl);
  return new Blob([buffer], { type: mimeType });
}

function pickBestMask(masks) {
  if (!Array.isArray(masks) || masks.length === 0) {
    throw new Error('배경 제거용 마스크를 받지 못했습니다.');
  }

  return masks
    .slice()
    .sort((left, right) => {
      const leftScore = typeof left.score === 'number' ? left.score : 0;
      const rightScore = typeof right.score === 'number' ? right.score : 0;
      return rightScore - leftScore;
    })[0];
}

async function applyAlphaMask(imageDataUrl, maskDataUrl) {
  const payload = JSON.stringify({
    image_data: imageDataUrl,
    mask_data: maskDataUrl,
  });

  const output = await new Promise((resolve, reject) => {
    const child = spawn(pythonBin, [alphaMaskScript], {
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString();
    });

    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
    });

    child.on('error', reject);
    child.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(stderr.trim() || `마스크 합성 스크립트가 ${code} 코드로 종료되었습니다.`));
        return;
      }
      resolve(stdout);
    });

    child.stdin.write(payload);
    child.stdin.end();
  });

  const parsed = JSON.parse(output);
  return parsed.image_data_url;
}

export async function translatePromptWithOpenAI(promptKo, backgroundMode, guideSummary = '') {
  const apiKey = getOpenAiKey();
  if (!apiKey) return null;

  const response = await fetch('https://api.openai.com/v1/responses', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: process.env.OPENAI_TRANSLATION_MODEL || 'gpt-5-mini',
      input: [
        {
          role: 'system',
          content: [
            {
              type: 'input_text',
              text:
                'Translate Korean ad-background prompts into concise production English for photoreal image generation. Keep it background-only, preserve layout guidance, and never introduce products, hands, people, text, logos, vector graphics, splashes, floating cream, or decorative objects.',
            },
          ],
        },
        {
          role: 'user',
          content: [
            {
              type: 'input_text',
              text: `Background mode: ${backgroundMode}\nGuide summary: ${guideSummary}\nKorean prompt: ${promptKo}\nReturn one English prompt sentence only.`,
            },
          ],
        },
      ],
    }),
  });

  if (!response.ok) {
    const message = await response.text().catch(() => '');
    throw new Error(message || 'OpenAI 프롬프트 번역에 실패했습니다.');
  }

  const result = await response.json();
  return typeof result.output_text === 'string' ? result.output_text.trim() : null;
}

export async function removeBackgroundWithHf(imageDataUrl) {
  const client = getInferenceClient();
  const masks = await client.imageSegmentation({
    provider: process.env.HF_BG_REMOVAL_PROVIDER || undefined,
    model: process.env.HF_BG_REMOVAL_MODEL || 'briaai/RMBG-2.0',
    inputs: buildBlobFromDataUrl(imageDataUrl),
    parameters: {
      threshold: Number(process.env.HF_BG_REMOVAL_THRESHOLD || 0.1),
    },
  });

  const bestMask = pickBestMask(masks);
  const maskDataUrl = bestMask.mask.startsWith('data:')
    ? bestMask.mask
    : `data:image/png;base64,${bestMask.mask}`;
  const imageDataUrlWithAlpha = await applyAlphaMask(imageDataUrl, maskDataUrl);

  return {
    imageDataUrl: imageDataUrlWithAlpha,
    maskDataUrl,
    label: bestMask.label,
    score: bestMask.score ?? null,
  };
}

export async function generateImageToImageVariants({
  guideImage,
  translatedPrompt,
  negativePrompt,
  count = 4,
}) {
  const client = getInferenceClient();
  const promptVariants = [
    { name: 'AI 프리미엄 스튜디오', suffix: 'photoreal premium studio lighting, dark refined backdrop, realistic material textures, high-end beverage campaign set, no decorative graphics' },
    { name: 'AI 카페 우드 무드', suffix: 'photoreal coffee shop interior, rich wooden tabletop, cinematic spotlight, natural reflections, no floating objects' },
    { name: 'AI 골든 아워 밸리', suffix: 'photoreal golden hour landscape backdrop, atmospheric depth, realistic mountains and field, natural premium campaign mood, no graphic elements' },
    { name: 'AI 소프트 윈도 라이트', suffix: 'photoreal daylight through cafe window, elegant wall texture, realistic shadows, soft lens depth, no decorative splash' },
  ].slice(0, count);

  const outputs = [];

  for (const variant of promptVariants) {
    const blob = await client.imageToImage({
      provider: process.env.HF_IMAGE_TO_IMAGE_PROVIDER || undefined,
      model: process.env.HF_IMAGE_TO_IMAGE_MODEL || 'stabilityai/stable-diffusion-3.5-medium',
      inputs: buildBlobFromDataUrl(guideImage),
      parameters: {
        prompt: `${translatedPrompt}, ${variant.suffix}`,
        negative_prompt: negativePrompt,
        guidance_scale: Number(process.env.HF_GUIDANCE_SCALE || 6),
        num_inference_steps: Number(process.env.HF_NUM_INFERENCE_STEPS || 30),
        target_size: {
          width: Number(process.env.HF_TARGET_WIDTH || 768),
          height: Number(process.env.HF_TARGET_HEIGHT || 1024),
        },
      },
    });

    const arrayBuffer = await blob.arrayBuffer();
    outputs.push({
      name: variant.name,
      imageUrl: bufferToDataUrl(Buffer.from(arrayBuffer), blob.type || 'image/png'),
      note: variant.suffix,
    });
  }

  return outputs;
}
