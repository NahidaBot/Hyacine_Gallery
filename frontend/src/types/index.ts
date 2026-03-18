export interface Artwork {
  id: number;
  platform: string;
  pid: string;
  title: string;
  author: string;
  author_id: string;
  source_url: string;
  page_count: number;
  width: number;
  height: number;
  is_nsfw: boolean;
  is_ai: boolean;
  images_json: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface ArtworkListResponse {
  data: Artwork[];
  total: number;
  page: number;
  page_size: number;
}

export interface TagCount {
  tag: string;
  count: number;
}
