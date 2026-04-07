import crypto from 'crypto';

const BRIDGE_TTL_MS = 10 * 60 * 1000;
const bridgeStore = new Map();

function cleanupExpiredPayloads() {
  const now = Date.now();
  for (const [token, entry] of bridgeStore.entries()) {
    if (entry.expiresAt <= now) {
      bridgeStore.delete(token);
    }
  }
}

export function createEditingBridgePayload(payload) {
  cleanupExpiredPayloads();

  const token = crypto.randomUUID();
  bridgeStore.set(token, {
    payload,
    expiresAt: Date.now() + BRIDGE_TTL_MS,
  });

  return {
    token,
    expiresInMs: BRIDGE_TTL_MS,
  };
}

export function consumeEditingBridgePayload(token) {
  cleanupExpiredPayloads();

  const entry = bridgeStore.get(token);
  if (!entry) return null;

  bridgeStore.delete(token);
  return entry.payload;
}
