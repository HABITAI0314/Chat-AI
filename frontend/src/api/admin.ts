import type {
  AdminCharacterDetail,
  AdminCharacterSummary,
  AdminPreviewRequest,
  AdminPreviewResponse,
  CharacterDraftPayload,
  CharacterValidationResponse,
  LLMConfig,
  LLMConfigPayload,
  PromptBundle,
  PromptConfig,
  TTSConfig,
  TTSConfigPayload,
} from '../types/admin'

const adminTokenKey = 'virtual-character-admin-token'

const request = async <T>(url: string, init: RequestInit = {}): Promise<T> => {
  const token = sessionStorage.getItem(adminTokenKey)
  const headers = new Headers(init.headers)
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (token) headers.set('X-Admin-Token', token)
  const response = await fetch(url, { ...init, headers })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const detail = body.detail
    if (typeof detail === 'object' && detail?.code) {
      const error = new Error(detail.code) as Error & { issues?: unknown }
      error.issues = detail.issues
      throw error
    }
    throw new Error(typeof detail === 'string' ? detail : '后台请求失败：' + response.status)
  }
  return response.json() as Promise<T>
}

export const adminApi = {
  async llmConfig(): Promise<LLMConfig> {
    return request<LLMConfig>('/api/admin/settings/chat-model')
  },

  async saveLlmConfig(payload: LLMConfigPayload): Promise<LLMConfig> {
    return request<LLMConfig>('/api/admin/settings/chat-model', {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  },

  async ttsConfig(): Promise<TTSConfig> {
    return request<TTSConfig>('/api/admin/settings/tts')
  },

  async saveTtsConfig(payload: TTSConfigPayload): Promise<TTSConfig> {
    return request<TTSConfig>('/api/admin/settings/tts', {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  },

  async promptConfig(version?: number): Promise<PromptConfig> {
    const query = version ? '?version=' + version : ''
    return request<PromptConfig>('/api/admin/settings/prompts' + query)
  },

  async createPromptVersion(name: string, prompts: PromptBundle): Promise<PromptConfig> {
    return request<PromptConfig>('/api/admin/settings/prompts/versions', {
      method: 'POST',
      body: JSON.stringify({ name, prompts, activate: true }),
    })
  },

  async activatePromptVersion(version: number): Promise<PromptConfig> {
    return request<PromptConfig>('/api/admin/settings/prompts/versions/' + version + '/activate', {
      method: 'PUT',
    })
  },

  async list(): Promise<AdminCharacterSummary[]> {
    return request<AdminCharacterSummary[]>('/api/admin/characters')
  },

  async detail(id: number): Promise<AdminCharacterDetail> {
    return request<AdminCharacterDetail>('/api/admin/characters/' + id)
  },

  async create(payload: CharacterDraftPayload): Promise<AdminCharacterDetail> {
    return request<AdminCharacterDetail>('/api/admin/characters', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async saveDraft(id: number, payload: CharacterDraftPayload): Promise<AdminCharacterDetail> {
    return request<AdminCharacterDetail>('/api/admin/characters/' + id + '/draft', {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  },

  async validate(id: number, payload: CharacterDraftPayload): Promise<CharacterValidationResponse> {
    return request<CharacterValidationResponse>('/api/admin/characters/' + id + '/validate', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async publish(id: number): Promise<AdminCharacterDetail> {
    return request<AdminCharacterDetail>('/api/admin/characters/' + id + '/publish', {
      method: 'POST',
    })
  },

  async setActive(id: number, isActive: boolean): Promise<AdminCharacterDetail> {
    return request<AdminCharacterDetail>('/api/admin/characters/' + id + '/active', {
      method: 'PATCH',
      body: JSON.stringify({ is_active: isActive }),
    })
  },

  async duplicate(id: number): Promise<AdminCharacterDetail> {
    return request<AdminCharacterDetail>('/api/admin/characters/' + id + '/duplicate', {
      method: 'POST',
    })
  },

  async preview(id: number, payload: AdminPreviewRequest): Promise<AdminPreviewResponse> {
    return request<AdminPreviewResponse>('/api/admin/characters/' + id + '/preview', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
}
