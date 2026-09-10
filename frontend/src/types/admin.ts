export interface CharacterProfile {
  description: string
  background: string
  personality: string[]
  speech_style: {
    address?: string
    sentence_length?: string
    habits?: string[]
    [key: string]: unknown
  }
  goals: {
    primary?: string
    [key: string]: unknown
  }
  scene_rules: Record<string, unknown>
  photo_policy: {
    enabled?: boolean
    assets?: string[]
    min_familiarity?: number
    min_trust?: number
    early_outcome?: string
    send_on_explicit_request?: boolean
    [key: string]: unknown
  }
  voice_policy: {
    mode?: string
    voice_id?: string
    display_mode?: string
    [key: string]: unknown
  }
  transfer_policy: {
    enabled?: boolean
    mode?: 'accept' | 'return' | 'conditional' | string
    min_familiarity?: number
    min_trust?: number
    max_accept_amount_cents?: number
    accept_reply?: string
    return_reply?: string
    [key: string]: unknown
  }
  defaults: {
    familiarity?: number
    trust?: number
    affection?: number
    annoyance?: number
    emotion?: string
    emotion_intensity?: number
    emotion_valence?: number
    scene?: string
    [key: string]: unknown
  }
  fallback_replies: {
    photo?: string
    photo_send?: string
    voice?: string
    avoid?: string
    [key: string]: unknown
  }
  safety_notes: string
  custom_rules?: string
  [key: string]: unknown
}

export interface AdminCharacterSummary {
  id: number
  code: string
  name: string
  description: string
  avatar_url: string
  is_virtual: boolean
  is_active: boolean
  config_status: 'draft' | 'published' | string
  has_draft: boolean
  profile_version: number
  updated_at: string
}

export interface AdminCharacterDetail extends AdminCharacterSummary {
  avatar_path: string
  profile: CharacterProfile
  draft_profile: CharacterProfile
  published_profile: CharacterProfile
  published_at: string | null
}

export interface CharacterDraftPayload {
  code: string
  name: string
  avatar_path: string
  profile: CharacterProfile
}

export interface ValidationIssue {
  path: string
  message: string
  level: string
}

export interface CharacterValidationResponse {
  valid: boolean
  issues: ValidationIssue[]
}

export interface LLMConfig {
  enabled: boolean
  base_url: string
  model: string
  has_api_key: boolean
  api_key_masked: string
}

export interface LLMConfigPayload {
  enabled: boolean
  base_url: string
  model: string
  api_key: string
}

export interface TTSConfig {
  enabled: boolean
  provider: 'doubao_bidirection' | 'openai_compatible' | string
  base_url: string
  model: string
  has_api_key: boolean
  api_key_masked: string
  speaker: string
  websocket_url: string
  app_id: string
  resource_id: string
  output_format: string
  output_sample_rate: number
  output_file_format: string
  max_retries: number
  max_chars: number
  timeout_seconds: number
  connect_timeout_seconds: number
}

export type TTSConfigPayload = Omit<TTSConfig, 'has_api_key' | 'api_key_masked'> & {
  api_key: string
}

export interface PromptBundle {
  behavior_system: string
  behavior_user: string
  reply_system: string
  reply_user: string
  memory_system: string
  memory_user: string
}

export interface PromptConfig {
  active_version: number
  selected_version: number
  versions: { version: number; name: string; created_at: string }[]
  prompts: PromptBundle
}

export interface PreviewMessage {
  id: number
  role: 'user' | 'assistant'
  message_type: 'text' | 'image' | 'audio' | 'transfer'
  content: string | null
  image_url?: string | null
  audio_url?: string | null
  audio_duration_ms?: number | null
  transcript?: string | null
  metadata?: Record<string, unknown>
  created_at: string
  delay_ms?: number
}

export interface AdminPreviewRequest {
  profile: CharacterProfile
  name: string
  avatar_url: string
  user_message: string
  recent_messages: PreviewMessage[]
  relationship: Record<string, unknown>
  emotion: Record<string, unknown>
  scene: Record<string, unknown>
  memories: Record<string, unknown>[]
}

export interface AdminPreviewResponse {
  assistant_messages: PreviewMessage[]
  state: {
    relationship: Record<string, unknown>
    emotion: Record<string, unknown>
    scene: Record<string, unknown>
  }
  debug: Record<string, unknown>
}
