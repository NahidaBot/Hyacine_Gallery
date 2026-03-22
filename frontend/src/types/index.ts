export interface ArtworkImage {
  id: number;
  page_index: number;
  url_original: string;
  url_thumb: string;
  width: number;
  height: number;
  file_size: number;
  file_name: string;
  storage_path: string;
}

export interface TagBrief {
  id: number;
  name: string;
  type: string;
}

export interface ArtworkSource {
  id: number;
  platform: string;
  pid: string;
  source_url: string;
  is_primary: boolean;
  created_at: string;
}

export interface Artwork {
  id: number;
  platform: string;
  pid: string;
  title: string;
  author: string;
  author_id: string;
  source_url: string;
  page_count: number;
  is_nsfw: boolean;
  is_ai: boolean;
  images: ArtworkImage[];
  tags: TagBrief[];
  sources: ArtworkSource[];
  created_at: string;
  updated_at: string;
}

export interface SimilarArtworkInfo {
  artwork_id: number;
  distance: number;
  platform: string;
  pid: string;
  title: string;
  thumb_url: string;
}

export interface ImportResponse {
  artwork: Artwork | null;
  similar: SimilarArtworkInfo[];
  merged: boolean;
  message: string;
  queued: boolean;
}

export interface ArtworkListResponse {
  data: Artwork[];
  total: number;
  page: number;
  page_size: number;
}

export interface Tag {
  id: number;
  name: string;
  type: string;
  alias_of_id: number | null;
  created_at: string;
  artwork_count: number;
}

export interface TagListResponse {
  data: Tag[];
  total: number;
}

// ── Bot ──

export interface BotChannel {
  id: number;
  platform: string;
  channel_id: string;
  name: string;
  is_default: boolean;
  priority: number;
  conditions: Record<string, unknown>;
  enabled: boolean;
  created_at: string;
}

export interface BotPostLog {
  id: number;
  artwork_id: number;
  bot_platform: string;
  channel_id: string;
  message_id: string;
  message_link: string;
  posted_by: string;
  posted_at: string;
}

export interface BotPostLogListResponse {
  data: BotPostLog[];
  total: number;
  page: number;
  page_size: number;
}

export interface BotSetting {
  key: string;
  value: string;
  description: string;
}

// ── Users ──

export interface AdminUser {
  id: number;
  tg_id: number | null;
  tg_username: string;
  email: string | null;
  role: "owner" | "admin";
  created_at: string;
  last_login_at: string | null;
  import_count: number;
  post_count: number;
}

export interface PasskeyCredential {
  id: number;
  credential_id: string;
  device_name: string;
  sign_count: number;
  created_at: string;
  last_used_at: string | null;
}

// ── Friend Links ──

export interface FriendLink {
  id: number;
  name: string;
  url: string;
  description: string;
  avatar_url: string;
  sort_order: number;
  enabled: boolean;
  created_at: string;
}

// ── Tag Types ──

export interface TagType {
  id: number;
  name: string;
  label: string;
  color: string;
  sort_order: number;
  tag_count: number;
}
