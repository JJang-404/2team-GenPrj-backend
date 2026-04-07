import express from 'express';
import { generateBackgroundCandidates } from '../services/backgroundService.js';
import { consumeEditingBridgePayload, createEditingBridgePayload } from '../services/bridgeService.js';
import { removeBackgroundWithHf } from '../services/externalAiService.js';
import { getSidebarRecommendations, getTemplates } from '../services/templateService.js';
import { buildNegativePrompt, translatePromptToEnglish } from '../services/promptService.js';

const router = express.Router();

router.get('/editor/bootstrap', (_req, res) => {
  res.json({
    templates: getTemplates(),
    sidebarRecommendations: getSidebarRecommendations(),
  });
});

router.post('/bridge/editing', (req, res) => {
  const { payload } = req.body ?? {};
  if (!payload?.projectData) {
    res.status(400).send('payload.projectData가 필요합니다.');
    return;
  }

  res.json(createEditingBridgePayload(payload));
});

router.get('/bridge/editing/:token', (req, res) => {
  const payload = consumeEditingBridgePayload(req.params.token);
  if (!payload) {
    res.status(404).send('브리지 payload를 찾을 수 없습니다.');
    return;
  }

  res.json(payload);
});

router.post('/images/remove-background', async (req, res) => {
  const { imageDataUrl } = req.body ?? {};
  if (!imageDataUrl) {
    res.status(400).send('imageDataUrl이 필요합니다.');
    return;
  }

  try {
    const result = await removeBackgroundWithHf(imageDataUrl);
    res.json(result);
  } catch (error) {
    res.status(500).send(error instanceof Error ? error.message : '배경 제거에 실패했습니다.');
  }
});

router.post('/backgrounds/generate', async (req, res) => {
  const { templateId, backgroundMode, promptKo, guideImage, guideSummary } = req.body ?? {};
  if (!templateId || !backgroundMode) {
    res.status(400).send('templateId와 backgroundMode가 필요합니다.');
    return;
  }

  try {
    const result = await generateBackgroundCandidates({
      templateId,
      backgroundMode,
      promptKo: promptKo ?? '',
      guideImage: guideImage ?? '',
      guideSummary: guideSummary ?? '',
    });
    res.json(result);
  } catch (error) {
    res.status(500).send(error instanceof Error ? error.message : '배경 생성에 실패했습니다.');
  }
});

router.post('/prompts/translate', async (req, res) => {
  const { promptKo = '', backgroundMode = 'solid' } = req.body ?? {};
  res.json({
    translatedPrompt: await translatePromptToEnglish(promptKo, backgroundMode),
    negativePrompt: buildNegativePrompt(),
  });
});

router.get('/health', (_req, res) => {
  res.json({ ok: true });
});

export default router;
