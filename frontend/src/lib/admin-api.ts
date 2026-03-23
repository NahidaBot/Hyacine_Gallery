import type {
  AdminUser,
  Artwork,
  ArtworkListResponse,
  ArtworkSource,
  Author,
  BotChannel,
  BotPostLogListResponse,
  BotSetting,
  FriendLink,
  ImportResponse,
  PasskeyCredential,
  SimilarArtworkInfo,
  Tag,
  TagListResponse,
  TagType,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function getToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("jwt_token") ?? "";
}

export function clearToken(): void {
  if (typeof window !== "undefined") localStorage.removeItem("jwt_token");
}

export function saveToken(token: string): void {
  if (typeof window !== "undefined") localStorage.setItem("jwt_token", token);
}

export interface TelegramAuthResult {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  auth_date: number;
  hash: string;
}

/** 通过 Telegram Widget 回调数据登录，返回 JWT。*/
export async function loginWithTelegram(
  data: TelegramAuthResult,
): Promise<{ access_token: string; role: string }> {
  const res = await fetch(`${API_BASE}/api/auth/telegram`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<{ access_token: string; role: string }>;
}

/** 验证当前 JWT 并返回用户信息（401 时抛出）。*/
export async function fetchMe(): Promise<{
  id: number;
  tg_id: number | null;
  tg_username: string;
  role: string;
}> {
  const token = getToken();
  const res = await fetch(`${API_BASE}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Unauthorized");
  return res.json();
}

/** 获取 Telegram bot username（用于初始化 Login Widget）。*/
export async function fetchAuthConfig(): Promise<{ bot_username: string }> {
  const res = await fetch(`${API_BASE}/api/auth/config`);
  if (!res.ok) throw new Error("无法获取认证配置");
  return res.json();
}

async function adminFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken()}`,
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

// ── Artworks ──

export async function adminFetchArtworks(params?: {
  page?: number;
  pageSize?: number;
  platform?: string;
  tag?: string;
  q?: string;
}): Promise<ArtworkListResponse> {
  const sp = new URLSearchParams();
  if (params?.page) sp.set("page", String(params.page));
  if (params?.pageSize) sp.set("page_size", String(params.pageSize));
  if (params?.platform) sp.set("platform", params.platform);
  if (params?.tag) sp.set("tag", params.tag);
  if (params?.q) sp.set("q", params.q);
  const qs = sp.toString();
  return adminFetch<ArtworkListResponse>(`/api/artworks${qs ? `?${qs}` : ""}`);
}

export async function adminFetchArtwork(id: number): Promise<Artwork> {
  return adminFetch<Artwork>(`/api/artworks/${id}`);
}

export async function adminDeleteArtwork(id: number): Promise<void> {
  await adminFetch<unknown>(`/api/admin/artworks/${id}`, { method: "DELETE" });
}

export async function adminUpdateArtwork(
  id: number,
  data: {
    title?: string;
    title_zh?: string;
    author?: string;
    is_nsfw?: boolean;
    is_ai?: boolean;
    tags?: string[];
  },
): Promise<Artwork> {
  return adminFetch<Artwork>(`/api/admin/artworks/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function adminDeleteArtworkImage(
  artworkId: number,
  imageId: number,
): Promise<void> {
  await adminFetch<unknown>(
    `/api/admin/artworks/${artworkId}/images/${imageId}`,
    { method: "DELETE" },
  );
}

export async function adminImportArtwork(
  url: string,
  tags?: string[],
  autoMerge?: boolean,
  addToQueue?: boolean,
): Promise<ImportResponse> {
  return adminFetch<ImportResponse>("/api/admin/artworks/import", {
    method: "POST",
    body: JSON.stringify({
      url,
      tags: tags ?? [],
      auto_merge: autoMerge ?? false,
      add_to_queue: addToQueue ?? false,
    }),
  });
}

// ── Artwork Sources ──

export async function adminAddSource(
  artworkId: number,
  url: string,
): Promise<ArtworkSource> {
  return adminFetch<ArtworkSource>(`/api/admin/artworks/${artworkId}/sources`, {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export async function adminDeleteSource(
  artworkId: number,
  sourceId: number,
): Promise<void> {
  await adminFetch<unknown>(
    `/api/admin/artworks/${artworkId}/sources/${sourceId}`,
    { method: "DELETE" },
  );
}

export async function adminMergeArtwork(
  targetId: number,
  sourceArtworkId: number,
): Promise<Artwork> {
  return adminFetch<Artwork>(`/api/admin/artworks/${targetId}/merge`, {
    method: "POST",
    body: JSON.stringify({ source_artwork_id: sourceArtworkId }),
  });
}

// ── Image Search ──

export async function adminSearchByImage(
  file: File,
  threshold = 10,
): Promise<SimilarArtworkInfo[]> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(
    `${API_BASE}/api/admin/artworks/search-by-image?threshold=${threshold}`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${getToken()}` },
      body: formData,
    },
  );
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<SimilarArtworkInfo[]>;
}

// ── Tags ──

export async function adminFetchTags(type?: string): Promise<TagListResponse> {
  const qs = type ? `?type=${encodeURIComponent(type)}` : "";
  return adminFetch<TagListResponse>(`/api/tags${qs}`);
}

export async function adminCreateTag(data: {
  name: string;
  type?: string;
}): Promise<Tag> {
  return adminFetch<Tag>("/api/admin/tags", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function adminUpdateTag(
  id: number,
  data: { name?: string; type?: string; alias_of_id?: number | null },
): Promise<Tag> {
  return adminFetch<Tag>(`/api/admin/tags/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function adminDeleteTag(id: number): Promise<void> {
  await adminFetch<unknown>(`/api/admin/tags/${id}`, { method: "DELETE" });
}

// ── Bot Channels ──

export async function adminFetchBotChannels(
  platform = "telegram",
): Promise<BotChannel[]> {
  return adminFetch<BotChannel[]>(
    `/api/admin/bot/channels?platform=${encodeURIComponent(platform)}`,
  );
}

export async function adminCreateBotChannel(data: {
  platform?: string;
  channel_id: string;
  name?: string;
  is_default?: boolean;
  priority?: number;
  conditions?: Record<string, unknown>;
  enabled?: boolean;
}): Promise<BotChannel> {
  return adminFetch<BotChannel>("/api/admin/bot/channels", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function adminUpdateBotChannel(
  id: number,
  data: {
    channel_id?: string;
    name?: string;
    is_default?: boolean;
    priority?: number;
    conditions?: Record<string, unknown>;
    enabled?: boolean;
  },
): Promise<BotChannel> {
  return adminFetch<BotChannel>(`/api/admin/bot/channels/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function adminDeleteBotChannel(id: number): Promise<void> {
  await adminFetch<unknown>(`/api/admin/bot/channels/${id}`, {
    method: "DELETE",
  });
}

// ── Bot Settings ──

export async function adminFetchBotSettings(): Promise<BotSetting[]> {
  return adminFetch<BotSetting[]>("/api/admin/bot/settings");
}

export async function adminUpdateBotSettings(
  settings: Record<string, string>,
): Promise<void> {
  await adminFetch<unknown>("/api/admin/bot/settings", {
    method: "PUT",
    body: JSON.stringify({ settings }),
  });
}

// ── Post Logs ──

// ── Tag Types ──

export async function adminFetchTagTypes(): Promise<TagType[]> {
  return adminFetch<TagType[]>("/api/tags/types");
}

export async function adminCreateTagType(data: {
  name: string;
  label?: string;
  color?: string;
  sort_order?: number;
}): Promise<TagType> {
  return adminFetch<TagType>("/api/admin/tag-types", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function adminUpdateTagType(
  id: number,
  data: {
    name?: string;
    label?: string;
    color?: string;
    sort_order?: number;
  },
): Promise<TagType> {
  return adminFetch<TagType>(`/api/admin/tag-types/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function adminDeleteTagType(id: number): Promise<void> {
  await adminFetch<unknown>(`/api/admin/tag-types/${id}`, {
    method: "DELETE",
  });
}

// ── Users（站长专属） ──

export async function adminFetchUsers(): Promise<AdminUser[]> {
  return adminFetch<AdminUser[]>("/api/admin/users");
}

export async function adminCreateUser(data: {
  tg_id?: number | null;
  tg_username?: string;
  email?: string | null;
  role?: string;
}): Promise<AdminUser> {
  return adminFetch<AdminUser>("/api/admin/users", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function adminUpdateUser(
  id: number,
  data: { tg_username?: string; email?: string | null; role?: string },
): Promise<AdminUser> {
  return adminFetch<AdminUser>(`/api/admin/users/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function adminDeleteUser(id: number): Promise<void> {
  await adminFetch<unknown>(`/api/admin/users/${id}`, { method: "DELETE" });
}

export async function adminFetchUserCredentials(
  userId: number,
): Promise<PasskeyCredential[]> {
  return adminFetch<PasskeyCredential[]>(
    `/api/admin/users/${userId}/credentials`,
  );
}

export async function adminDeleteUserCredential(
  userId: number,
  credId: number,
): Promise<void> {
  await adminFetch<unknown>(
    `/api/admin/users/${userId}/credentials/${credId}`,
    { method: "DELETE" },
  );
}

// ── Passkey（当前用户） ──

function bufferToBase64url(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let str = "";
  for (const byte of bytes) str += String.fromCharCode(byte);
  return btoa(str).replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
}

function base64urlToBuffer(b64: string): ArrayBuffer {
  const padded = b64.replace(/-/g, "+").replace(/_/g, "/");
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

export async function passkeyRegisterBegin(): Promise<Record<string, unknown>> {
  return adminFetch<Record<string, unknown>>(
    "/api/auth/passkey/register/begin",
    { method: "POST" },
  );
}

export async function passkeyRegisterComplete(
  credential: PublicKeyCredential,
  deviceName: string,
): Promise<void> {
  const response = credential.response as AuthenticatorAttestationResponse;
  const credentialJson = {
    id: credential.id,
    rawId: bufferToBase64url(credential.rawId),
    response: {
      clientDataJSON: bufferToBase64url(response.clientDataJSON),
      attestationObject: bufferToBase64url(response.attestationObject),
    },
    type: credential.type,
  };
  await adminFetch<unknown>("/api/auth/passkey/register/complete", {
    method: "POST",
    body: JSON.stringify({ credential: credentialJson, device_name: deviceName }),
  });
}

export async function passkeyAuthBegin(): Promise<
  Record<string, unknown> & { challengeToken: string }
> {
  const res = await fetch(`${API_BASE}/api/auth/passkey/auth/begin`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<
    Record<string, unknown> & { challengeToken: string }
  >;
}

export async function passkeyAuthComplete(
  credential: PublicKeyCredential,
  challengeToken: string,
): Promise<{ access_token: string; role: string }> {
  const response = credential.response as AuthenticatorAssertionResponse;
  const credentialJson = {
    id: credential.id,
    rawId: bufferToBase64url(credential.rawId),
    response: {
      clientDataJSON: bufferToBase64url(response.clientDataJSON),
      authenticatorData: bufferToBase64url(response.authenticatorData),
      signature: bufferToBase64url(response.signature),
      userHandle: response.userHandle
        ? bufferToBase64url(response.userHandle)
        : null,
    },
    type: credential.type,
  };
  const res = await fetch(`${API_BASE}/api/auth/passkey/auth/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      credential: credentialJson,
      challenge_token: challengeToken,
    }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<{ access_token: string; role: string }>;
}

/** 将后端返回的 options（challenge/ids 为 base64url string）转换为浏览器 API 所需的 ArrayBuffer 格式。*/
export function prepareAuthOptions(
  options: Record<string, unknown>,
): PublicKeyCredentialRequestOptions {
  const challenge = base64urlToBuffer(options.challenge as string);
  const allowCredentials = (
    (options.allowCredentials as Array<Record<string, unknown>>) ?? []
  ).map((c) => ({
    type: "public-key" as const,
    id: base64urlToBuffer(c.id as string),
  }));
  return {
    challenge,
    allowCredentials,
    timeout: (options.timeout as number) ?? 60000,
    userVerification:
      (options.userVerification as UserVerificationRequirement) ?? "preferred",
    rpId: options.rpId as string | undefined,
  };
}

/** 将后端返回的注册 options 转换为浏览器 API 所需格式。*/
export function prepareCreationOptions(
  options: Record<string, unknown>,
): PublicKeyCredentialCreationOptions {
  const rp = options.rp as Record<string, unknown>;
  const user = options.user as Record<string, unknown>;
  const challenge = base64urlToBuffer(options.challenge as string);
  const pubKeyCredParams = (
    options.pubKeyCredParams as Array<Record<string, unknown>>
  ).map((p) => ({ type: "public-key" as const, alg: p.alg as number }));
  const excludeCredentials = (
    (options.excludeCredentials as Array<Record<string, unknown>>) ?? []
  ).map((c) => ({
    type: "public-key" as const,
    id: base64urlToBuffer(c.id as string),
  }));
  return {
    rp: { id: rp.id as string | undefined, name: rp.name as string },
    user: {
      id: base64urlToBuffer(user.id as string),
      name: user.name as string,
      displayName: user.displayName as string,
    },
    challenge,
    pubKeyCredParams,
    timeout: (options.timeout as number) ?? 60000,
    excludeCredentials,
    authenticatorSelection: options.authenticatorSelection as
      | AuthenticatorSelectionCriteria
      | undefined,
  };
}

// ── Friend Links ──

// ── Authors ──

export async function adminFetchAuthors(
  platform?: string,
): Promise<Author[]> {
  const qs = platform ? `?platform=${encodeURIComponent(platform)}` : "";
  return adminFetch<Author[]>(`/api/authors${qs}`);
}

export async function adminUpdateAuthor(
  id: number,
  data: { name?: string; canonical_id?: number | null },
): Promise<Author> {
  return adminFetch<Author>(`/api/admin/authors/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function adminDeleteAuthor(id: number): Promise<void> {
  await adminFetch<unknown>(`/api/admin/authors/${id}`, { method: "DELETE" });
}

// ── Links ──

export async function adminFetchLinks(): Promise<FriendLink[]> {
  return adminFetch<FriendLink[]>("/api/admin/links");
}

export async function adminCreateLink(data: {
  name: string;
  url: string;
  description?: string;
  avatar_url?: string;
  sort_order?: number;
  enabled?: boolean;
}): Promise<FriendLink> {
  return adminFetch<FriendLink>("/api/admin/links", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function adminUpdateLink(
  id: number,
  data: {
    name?: string;
    url?: string;
    description?: string;
    avatar_url?: string;
    sort_order?: number;
    enabled?: boolean;
  },
): Promise<FriendLink> {
  return adminFetch<FriendLink>(`/api/admin/links/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function adminDeleteLink(id: number): Promise<void> {
  await adminFetch<unknown>(`/api/admin/links/${id}`, { method: "DELETE" });
}

// ── Post Logs ──

export async function adminFetchPostLogs(params?: {
  artwork_id?: number;
  channel_id?: string;
  page?: number;
  page_size?: number;
}): Promise<BotPostLogListResponse> {
  const sp = new URLSearchParams();
  if (params?.artwork_id) sp.set("artwork_id", String(params.artwork_id));
  if (params?.channel_id) sp.set("channel_id", params.channel_id);
  if (params?.page) sp.set("page", String(params.page));
  if (params?.page_size) sp.set("page_size", String(params.page_size));
  const qs = sp.toString();
  return adminFetch<BotPostLogListResponse>(
    `/api/admin/bot/post-logs${qs ? `?${qs}` : ""}`,
  );
}
