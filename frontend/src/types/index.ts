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
  created_at: string;
  updated_at: string;
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
