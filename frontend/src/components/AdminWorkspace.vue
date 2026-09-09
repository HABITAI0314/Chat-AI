<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { adminApi } from '../api/admin'
import type {
  AdminCharacterDetail,
  AdminCharacterSummary,
  CharacterDraftPayload,
  CharacterProfile,
  LLMConfig,
  PromptBundle,
  PromptConfig,
  PreviewMessage,
  TTSConfig,
  ValidationIssue,
} from '../types/admin'

const emit = defineEmits<{
  goChat: []
}>()

const sections = [
  { id: 'model', label: '聊天模型', hint: 'API 地址、密钥和模型' },
  { id: 'prompts', label: '提示词版本', hint: '编辑、切换和回退' },
  { id: 'identity', label: '身份与人设', hint: '角色是谁，以及怎样说话' },
  { id: 'state', label: '关系与剧情', hint: '初始关系、情绪和场景目标' },
  { id: 'media', label: '图片与语音', hint: '媒体发送条件和素材白名单' },
  { id: 'fallback', label: '兜底与安全', hint: '异常回复和固定边界' },
]

interface CharacterForm {
  code: string
  name: string
  avatarPath: string
  description: string
  background: string
  personalityText: string
  address: string
  sentenceLength: string
  habitsText: string
  customRules: string
  primaryGoal: string
  plotName: string
  familiarity: number
  trust: number
  affection: number
  annoyance: number
  emotion: string
  emotionIntensity: number
  scene: string
  photoEnabled: boolean
  photoAssetsText: string
  photoMinFamiliarity: number
  photoMinTrust: number
  photoEarlyOutcome: string
  voiceMode: string
  voiceId: string
  displayMode: string
  fallbackPhoto: string
  fallbackPhotoSend: string
  fallbackVoice: string
  fallbackAvoid: string
  safetyNotes: string
}

const createEmptyForm = (): CharacterForm => ({
  code: '',
  name: '',
  avatarPath: '/static/characters/suhe/avatar.svg',
  description: '',
  background: '',
  personalityText: '',
  address: '你',
  sentenceLength: 'short',
  habitsText: '',
  customRules: '',
  primaryGoal: 'get_familiar',
  plotName: '',
  familiarity: 0,
  trust: 0,
  affection: 0,
  annoyance: 0,
  emotion: 'calm',
  emotionIntensity: 35,
  scene: 'first_meet',
  photoEnabled: true,
  photoAssetsText: 'photo-1',
  photoMinFamiliarity: 0,
  photoMinTrust: 0,
  photoEarlyOutcome: 'delay',
  voiceMode: 'on_request',
  voiceId: 'fictional-default',
  displayMode: 'text_and_audio',
  fallbackPhoto: '',
  fallbackPhotoSend: '好吧，给你看一张。',
  fallbackVoice: '',
  fallbackAvoid: '',
  safetyNotes: '虚构角色，不代表现实中的任何人。',
})

const characters = ref<AdminCharacterSummary[]>([])
const selectedId = ref<number>()
const detail = ref<AdminCharacterDetail>()
const form = reactive<CharacterForm>(createEmptyForm())
const activeSection = ref('identity')
const isLoading = ref(true)
const isSaving = ref(false)
const isPublishing = ref(false)
const isPreviewing = ref(false)
const statusMessage = ref('')
const errorMessage = ref('')
const issues = ref<ValidationIssue[]>([])
const previewInput = ref('你好，今天过得怎么样？')
const previewMessages = ref<PreviewMessage[]>([])
const previewState = ref<{
  relationship: Record<string, unknown>
  emotion: Record<string, unknown>
  scene: Record<string, unknown>
}>()
const previewDebug = ref<Record<string, unknown>>({})
const llmConfig = reactive<LLMConfig>({
  enabled: true,
  base_url: '',
  model: '',
  has_api_key: false,
  api_key_masked: '',
})
const llmApiKey = ref('')
const isSavingLlm = ref(false)
const ttsConfig = reactive<TTSConfig>({
  enabled: false,
  provider: 'doubao_bidirection',
  base_url: '',
  model: '',
  has_api_key: false,
  api_key_masked: '',
  speaker: '',
  websocket_url: '',
  app_id: '',
  resource_id: '',
  output_format: 'pcm',
  output_sample_rate: 24000,
  output_file_format: 'mp3',
  max_retries: 2,
  max_chars: 180,
  timeout_seconds: 20,
  connect_timeout_seconds: 10,
})
const ttsApiKey = ref('')
const isSavingTts = ref(false)
const promptConfig = ref<PromptConfig>()
const promptDraft = reactive<PromptBundle>({
  behavior_system: '',
  behavior_user: '',
  reply_system: '',
  reply_user: '',
  memory_system: '',
  memory_user: '',
})
const promptVersionName = ref('')
const isSavingPrompt = ref(false)
const selectedPromptVersion = ref<number>()
let previewId = -1

const selectedCharacter = computed(() => characters.value.find((item) => item.id === selectedId.value))
const currentSection = computed(() => sections.find((item) => item.id === activeSection.value) || sections[0])

const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T

const readNumber = (value: unknown, fallback: number) => {
  const number = Number(value)
  return Number.isFinite(number) ? number : fallback
}

const splitList = (value: string) =>
  value
    .split(/[\n,，、]/)
    .map((item) => item.trim())
    .filter(Boolean)

const listText = (value: unknown) => (Array.isArray(value) ? value.join('、') : '')

const applyDetail = (item: AdminCharacterDetail) => {
  detail.value = item
  selectedId.value = item.id
  const profile = item.draft_profile || item.profile
  const speechStyle = profile.speech_style || {}
  const defaults = profile.defaults || {}
  const photo = profile.photo_policy || {}
  const voice = profile.voice_policy || {}
  const fallback = profile.fallback_replies || {}
  Object.assign(form, {
    code: item.code,
    name: item.name,
    avatarPath: item.avatar_path,
    description: profile.description || '',
    background: profile.background || '',
    personalityText: listText(profile.personality),
    address: String(speechStyle.address || '你'),
    sentenceLength: String(speechStyle.sentence_length || 'short'),
    habitsText: listText(speechStyle.habits),
    customRules: String(profile.custom_rules || ''),
    primaryGoal: String(profile.goals?.primary || 'get_familiar'),
    plotName: String(profile.scene_rules?.plot_name || ''),
    familiarity: readNumber(defaults.familiarity, 0),
    trust: readNumber(defaults.trust, 0),
    affection: readNumber(defaults.affection, 0),
    annoyance: readNumber(defaults.annoyance, 0),
    emotion: String(defaults.emotion || 'calm'),
    emotionIntensity: readNumber(defaults.emotion_intensity, 35),
    scene: String(defaults.scene || 'first_meet'),
    photoEnabled: photo.enabled !== false,
    photoAssetsText: listText(photo.assets),
    photoMinFamiliarity: readNumber(photo.min_familiarity, 0),
    photoMinTrust: readNumber(photo.min_trust, 0),
    photoEarlyOutcome: String(photo.early_outcome || 'delay'),
    voiceMode: String(voice.mode || 'on_request'),
    voiceId: String(voice.voice_id || 'fictional-default'),
    displayMode: String(voice.display_mode || 'text_and_audio'),
    fallbackPhoto: String(fallback.photo || ''),
    fallbackPhotoSend: String(fallback.photo_send || '好吧，给你看一张。'),
    fallbackVoice: String(fallback.voice || ''),
    fallbackAvoid: String(fallback.avoid || ''),
    safetyNotes: String(profile.safety_notes || ''),
  })
  issues.value = []
  statusMessage.value = ''
  errorMessage.value = ''
  resetPreview()
}

const profileFromForm = (includeCurrent = true): CharacterProfile => {
  const current = includeCurrent
    ? clone(detail.value?.draft_profile || detail.value?.profile || {}) as Partial<CharacterProfile>
    : {}
  return {
    ...current,
    description: form.description.trim(),
    background: form.background.trim(),
    personality: splitList(form.personalityText),
    speech_style: {
      ...(current.speech_style || {}),
      address: form.address.trim(),
      sentence_length: form.sentenceLength,
      habits: splitList(form.habitsText),
    },
    goals: {
      ...(current.goals || {}),
      primary: form.primaryGoal.trim(),
    },
    scene_rules: {
      ...(current.scene_rules || {}),
      plot_name: form.plotName.trim(),
    },
    defaults: {
      ...(current.defaults || {}),
      familiarity: form.familiarity,
      trust: form.trust,
      affection: form.affection,
      annoyance: form.annoyance,
      emotion: form.emotion,
      emotion_intensity: form.emotionIntensity,
      scene: form.scene,
    },
    photo_policy: {
      ...(current.photo_policy || {}),
      enabled: form.photoEnabled,
      assets: splitList(form.photoAssetsText),
      min_familiarity: form.photoMinFamiliarity,
      min_trust: form.photoMinTrust,
      early_outcome: form.photoEarlyOutcome,
      send_on_explicit_request: true,
    },
    voice_policy: {
      ...(current.voice_policy || {}),
      mode: form.voiceMode,
      voice_id: form.voiceId.trim(),
      display_mode: form.displayMode,
    },
    fallback_replies: {
      ...(current.fallback_replies || {}),
      photo: form.fallbackPhoto.trim(),
      photo_send: form.fallbackPhotoSend.trim(),
      voice: form.fallbackVoice.trim(),
      avoid: form.fallbackAvoid.trim(),
    },
    custom_rules: form.customRules.trim(),
    safety_notes: form.safetyNotes.trim(),
  } as CharacterProfile
}

const payloadFromForm = (includeCurrent = true): CharacterDraftPayload => ({
  code: form.code.trim(),
  name: form.name.trim(),
  avatar_path: form.avatarPath.trim(),
  profile: profileFromForm(includeCurrent),
})

const updateListItem = (item: AdminCharacterDetail) => {
  const index = characters.value.findIndex((character) => character.id === item.id)
  if (index >= 0) {
    characters.value[index] = item
  }
}

const selectCharacter = async (id: number) => {
  isLoading.value = true
  errorMessage.value = ''
  try {
    applyDetail(await adminApi.detail(id))
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载角色失败'
  } finally {
    isLoading.value = false
  }
}

const refresh = async () => {
  isLoading.value = true
  errorMessage.value = ''
  try {
    characters.value = await adminApi.list()
    const id = selectedId.value && characters.value.some((item) => item.id === selectedId.value)
      ? selectedId.value
      : characters.value[0]?.id
    if (id) await selectCharacter(id)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载后台失败'
    isLoading.value = false
  }
}

const loadLlmConfig = async () => {
  try {
    Object.assign(llmConfig, await adminApi.llmConfig())
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载模型配置失败'
  }
}

const saveLlmConfig = async () => {
  if (isSavingLlm.value) return
  isSavingLlm.value = true
  errorMessage.value = ''
  try {
    const saved = await adminApi.saveLlmConfig({
      enabled: llmConfig.enabled,
      base_url: llmConfig.base_url,
      model: llmConfig.model,
      api_key: llmApiKey.value,
    })
    Object.assign(llmConfig, saved)
    llmApiKey.value = ''
    statusMessage.value = '聊天模型配置已保存，下一条消息立即生效。'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '保存模型配置失败'
  } finally {
    isSavingLlm.value = false
  }
}

const loadTtsConfig = async () => {
  try {
    Object.assign(ttsConfig, await adminApi.ttsConfig())
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载语音配置失败'
  }
}

const saveTtsConfig = async () => {
  if (isSavingTts.value) return
  isSavingTts.value = true
  errorMessage.value = ''
  try {
    const saved = await adminApi.saveTtsConfig({
      enabled: ttsConfig.enabled,
      provider: ttsConfig.provider,
      base_url: ttsConfig.base_url,
      model: ttsConfig.model,
      api_key: ttsApiKey.value,
      speaker: ttsConfig.speaker,
      websocket_url: ttsConfig.websocket_url,
      app_id: ttsConfig.app_id,
      resource_id: ttsConfig.resource_id,
      output_format: ttsConfig.output_format,
      output_sample_rate: ttsConfig.output_sample_rate,
      output_file_format: ttsConfig.output_file_format,
      max_retries: ttsConfig.max_retries,
      max_chars: ttsConfig.max_chars,
      timeout_seconds: ttsConfig.timeout_seconds,
      connect_timeout_seconds: ttsConfig.connect_timeout_seconds,
    })
    Object.assign(ttsConfig, saved)
    ttsApiKey.value = ''
    statusMessage.value = 'TTS 配置已保存，下一条语音立即生效。'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '保存语音配置失败'
  } finally {
    isSavingTts.value = false
  }
}

const applyPromptConfig = (config: PromptConfig) => {
  promptConfig.value = config
  selectedPromptVersion.value = config.selected_version
  Object.assign(promptDraft, config.prompts)
}

const loadPromptConfig = async (version?: number) => {
  try {
    applyPromptConfig(await adminApi.promptConfig(version))
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载提示词失败'
  }
}

const selectPromptVersion = async () => {
  if (selectedPromptVersion.value) await loadPromptConfig(selectedPromptVersion.value)
}

const createPromptVersion = async () => {
  if (isSavingPrompt.value) return
  isSavingPrompt.value = true
  errorMessage.value = ''
  try {
    const name = promptVersionName.value.trim() || '提示词优化版'
    applyPromptConfig(await adminApi.createPromptVersion(name, clone(promptDraft)))
    promptVersionName.value = ''
    statusMessage.value = '新提示词版本已创建并切换生效。'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '保存提示词版本失败'
  } finally {
    isSavingPrompt.value = false
  }
}

const activatePromptVersion = async () => {
  if (!selectedPromptVersion.value || isSavingPrompt.value) return
  isSavingPrompt.value = true
  try {
    applyPromptConfig(await adminApi.activatePromptVersion(selectedPromptVersion.value))
    statusMessage.value = '已切换提示词版本，下一条消息立即生效。'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '切换提示词版本失败'
  } finally {
    isSavingPrompt.value = false
  }
}

const saveDraft = async (showMessage = true) => {
  if (!detail.value || isSaving.value) return false
  isSaving.value = true
  errorMessage.value = ''
  try {
    const updated = await adminApi.saveDraft(detail.value.id, payloadFromForm())
    applyDetail(updated)
    updateListItem(updated)
    if (showMessage) statusMessage.value = '草稿已保存，尚未影响聊天端。'
    return true
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '保存草稿失败'
    return false
  } finally {
    isSaving.value = false
  }
}

const validate = async () => {
  if (!detail.value) return
  errorMessage.value = ''
  try {
    const result = await adminApi.validate(detail.value.id, payloadFromForm())
    issues.value = result.issues
    statusMessage.value = result.valid ? '配置校验通过，可以发布。' : '配置还有需要修正的项目。'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '配置校验失败'
  }
}

const publish = async () => {
  if (!detail.value || isPublishing.value) return
  isPublishing.value = true
  try {
    const saved = await saveDraft(false)
    if (!saved) return
    const updated = await adminApi.publish(detail.value.id)
    applyDetail(updated)
    updateListItem(updated)
    statusMessage.value = `已发布 v${updated.profile_version}，聊天端现在会使用这份配置。`
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '发布失败'
  } finally {
    isPublishing.value = false
  }
}

const toggleActive = async () => {
  if (!detail.value) return
  try {
    const updated = await adminApi.setActive(detail.value.id, !detail.value.is_active)
    applyDetail(updated)
    updateListItem(updated)
    statusMessage.value = updated.is_active ? '角色已启用。' : '角色已停用，不会出现在新的聊天角色列表中。'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '更新角色状态失败'
  }
}

const duplicate = async () => {
  if (!detail.value) return
  try {
    const copy = await adminApi.duplicate(detail.value.id)
    characters.value.push(copy)
    applyDetail(copy)
    statusMessage.value = '已复制角色，请修改编码后再发布。'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '复制角色失败'
  }
}

const createCharacter = async () => {
  const empty = createEmptyForm()
  Object.assign(form, empty, {
    code: `new-character-${Date.now().toString(36)}`,
    name: '新角色',
  })
  try {
    const created = await adminApi.create(payloadFromForm(false))
    characters.value.push(created)
    applyDetail(created)
    statusMessage.value = '已创建草稿角色，请补充人设后校验并发布。'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '创建角色失败'
  }
}

const resetPreview = () => {
  previewMessages.value = []
  previewState.value = undefined
  previewDebug.value = {}
  previewInput.value = '你好，今天过得怎么样？'
}

const preview = async () => {
  if (!detail.value || !previewInput.value.trim() || isPreviewing.value) return
  const userMessage = previewInput.value.trim()
  const history = clone(previewMessages.value)
  previewMessages.value.push({
    id: previewId--,
    role: 'user',
    message_type: 'text',
    content: userMessage,
    created_at: new Date().toISOString(),
  })
  previewInput.value = ''
  isPreviewing.value = true
  errorMessage.value = ''
  try {
    const result = await adminApi.preview(detail.value.id, {
      profile: profileFromForm(),
      name: form.name,
      avatar_url: form.avatarPath,
      user_message: userMessage,
      recent_messages: history,
      relationship: previewState.value?.relationship || {},
      emotion: previewState.value?.emotion || {},
      scene: previewState.value?.scene || {},
      memories: [],
    })
    previewMessages.value.push(...result.assistant_messages)
    previewState.value = result.state
    previewDebug.value = result.debug
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '预览失败'
  } finally {
    isPreviewing.value = false
  }
}

const statusLabel = (status: string, hasDraft: boolean) => {
  if (status !== 'published') return '未发布草稿'
  return hasDraft ? '已发布 · 有草稿' : '已发布'
}
const stateLabel = (value: unknown) => String(value || '—')
const issueLabel = (issue: ValidationIssue) => issue.path.replace(/^profile\./, '') + '：' + issue.message

onMounted(() => Promise.all([
  refresh(),
  loadLlmConfig(),
  loadTtsConfig(),
  loadPromptConfig(),
]))
</script>

<template>
  <main class="admin-workspace">
    <header class="admin-topbar">
      <div class="admin-brand">
        <span class="brand-dot" />
        <div>
          <strong>角色工作台</strong>
          <small>CHARACTER STUDIO</small>
        </div>
      </div>
      <nav class="workspace-nav" aria-label="工作区切换">
        <button type="button" @click="emit('goChat')">聊天体验</button>
        <button class="active" type="button">角色后台</button>
      </nav>
      <span class="admin-mode">本地管理模式</span>
    </header>

    <div class="admin-body">
      <aside class="admin-list-panel">
        <div class="admin-list-heading">
          <div>
            <span class="eyebrow">CHARACTERS</span>
            <h1>角色配置</h1>
          </div>
          <div class="list-heading-actions">
            <button class="new-character-button" type="button" @click="createCharacter">+ 新建</button>
            <button class="icon-button" type="button" title="刷新" @click="refresh">↻</button>
          </div>
        </div>
        <p class="list-description">修改人设、状态与媒体规则，发布后即可在聊天端生效。</p>

        <div v-if="isLoading && !characters.length" class="admin-list-loading">正在读取角色…</div>
        <button
          v-for="character in characters"
          :key="character.id"
          class="admin-character-item"
          :class="{ selected: character.id === selectedId }"
          type="button"
          @click="selectCharacter(character.id)"
        >
          <img :src="character.avatar_url" :alt="character.name" />
          <span class="admin-character-copy">
            <span class="admin-character-name">{{ character.name }}</span>
            <span class="admin-character-meta">{{ character.code }} · v{{ character.profile_version }}</span>
          </span>
          <span class="status-dot" :class="{ muted: !character.is_active }" />
        </button>

        <div class="admin-list-footer">
          <span>{{ characters.length }} 个角色</span>
          <span>草稿不会直接生效</span>
        </div>
      </aside>

      <section v-if="detail" class="admin-editor-panel">
        <header class="editor-header">
          <div class="editor-title">
            <img :src="form.avatarPath" :alt="form.name" />
            <div>
              <div class="title-line">
                <h2>{{ form.name || '未命名角色' }}</h2>
                <span class="status-badge" :class="detail.has_draft ? 'draft' : detail.config_status">{{ statusLabel(detail.config_status, detail.has_draft) }}</span>
                <span v-if="!detail.is_active" class="offline-badge">已停用</span>
              </div>
              <p>{{ form.code || '等待编码' }} · 当前发布版本 v{{ detail.profile_version }}</p>
            </div>
          </div>
          <div class="editor-actions">
            <button class="text-button" type="button" @click="duplicate">复制</button>
            <button class="text-button" type="button" @click="toggleActive">{{ detail.is_active ? '停用' : '启用' }}</button>
            <button class="secondary-button" type="button" :disabled="isSaving || isPublishing" @click="saveDraft()">{{ isSaving ? '保存中…' : '保存草稿' }}</button>
            <button class="primary-button" type="button" :disabled="isSaving || isPublishing" @click="publish">{{ isPublishing ? '发布中…' : '发布配置' }}</button>
          </div>
        </header>

        <div v-if="statusMessage" class="status-message">{{ statusMessage }}</div>
        <div v-if="errorMessage" class="admin-error">{{ errorMessage }}</div>

        <div class="editor-layout">
          <div class="form-column">
            <nav class="section-tabs" aria-label="角色配置分区">
              <button
                v-for="section in sections"
                :key="section.id"
                type="button"
                :class="{ active: section.id === activeSection }"
                @click="activeSection = section.id"
              >
                <span>{{ section.label }}</span>
                <small>{{ section.hint }}</small>
              </button>
            </nav>

            <section class="form-section">
              <div class="section-heading">
                <div>
                  <span class="eyebrow">{{ activeSection.toUpperCase() }}</span>
                  <h3>{{ currentSection.label }}</h3>
                </div>
                <button class="validate-button" type="button" @click="validate">校验配置</button>
              </div>

              <template v-if="activeSection === 'model'">
                <div class="subsection-heading"><h4>OpenAI 兼容聊天接口</h4><span>保存后无需重启服务</span></div>
                <label class="switch-field"><input v-model="llmConfig.enabled" type="checkbox" /><span>启用聊天模型</span></label>
                <label>Base URL<small class="field-hint">填写到 /v1，例如 https://api.openai.com/v1</small><input v-model="llmConfig.base_url" type="url" placeholder="https://api.example.com/v1" /></label>
                <div class="field-grid two-columns">
                  <label>模型名称<input v-model="llmConfig.model" type="text" placeholder="例如 qwen-plus" /></label>
                  <label>API Key<small class="field-hint">{{ llmConfig.has_api_key ? '已配置 ' + llmConfig.api_key_masked + '；留空则保持不变' : '尚未配置' }}</small><input v-model="llmApiKey" type="password" autocomplete="new-password" placeholder="sk-..." /></label>
                </div>
                <button class="primary-button model-save" type="button" :disabled="isSavingLlm" @click="saveLlmConfig">{{ isSavingLlm ? '保存中…' : '保存模型配置' }}</button>
                <div class="info-callout"><span>i</span><p>支持 OpenAI 兼容接口。配置只保存在本机 data/llm-config.json，聊天请求会读取最新值。</p></div>
              </template>

              <template v-else-if="activeSection === 'identity'">
                <div class="field-grid two-columns">
                  <label>角色名称<input v-model="form.name" type="text" maxlength="100" /></label>
                  <label>唯一编码<input v-model="form.code" type="text" maxlength="64" /></label>
                </div>
                <label>头像路径<input v-model="form.avatarPath" type="text" placeholder="/static/characters/name/avatar.svg" /></label>
                <div class="field-grid two-columns">
                  <label>对外简介<textarea v-model="form.description" rows="3" /></label>
                  <label>背景与当前生活<textarea v-model="form.background" rows="3" /></label>
                </div>
                <label>性格标签<small class="field-hint">用逗号或换行分隔，例如：慢热、嘴硬、细腻</small><textarea v-model="form.personalityText" rows="3" /></label>
                <div class="field-grid three-columns">
                  <label>称呼用户<input v-model="form.address" type="text" /></label>
                  <label>句子长度<select v-model="form.sentenceLength"><option value="very_short">很短</option><option value="short">短句</option><option value="medium">适中</option></select></label>
                  <label>口头禅<textarea v-model="form.habitsText" rows="2" /></label>
                </div>
                <label>补充规则<small class="field-hint">仅填写角色行为补充，不要放 API Key、文件路径或现实交易要求。</small><textarea v-model="form.customRules" rows="4" placeholder="例如：不喜欢被连续追问，会先转开话题。" /></label>
              </template>

              <template v-else-if="activeSection === 'state'">
                <div class="field-grid two-columns">
                  <label>主要目标<select v-model="form.primaryGoal"><option value="get_familiar">逐渐熟悉</option><option value="sell_tea">推进虚构茶铺剧情</option><option value="share_life">分享日常生活</option><option value="observe">先观察用户</option></select></label>
                  <label>剧情名称<input v-model="form.plotName" type="text" placeholder="可选，例如：虚构茶铺试饮剧情" /></label>
                </div>
                <div class="subsection-heading"><h4>新会话初始关系</h4><span>0～100，聊天过程中会继续变化</span></div>
                <div class="state-sliders">
                  <label>熟悉度<strong>{{ form.familiarity }}</strong><input v-model.number="form.familiarity" type="range" min="0" max="100" /></label>
                  <label>信任<strong>{{ form.trust }}</strong><input v-model.number="form.trust" type="range" min="0" max="100" /></label>
                  <label>好感<strong>{{ form.affection }}</strong><input v-model.number="form.affection" type="range" min="0" max="100" /></label>
                  <label>烦躁<strong>{{ form.annoyance }}</strong><input v-model.number="form.annoyance" type="range" min="0" max="100" /></label>
                </div>
                <div class="field-grid three-columns">
                  <label>初始情绪<select v-model="form.emotion"><option value="calm">平静</option><option value="happy">开心</option><option value="shy">害羞</option><option value="curious">好奇</option><option value="guarded">戒备</option><option value="sad">低落</option></select></label>
                  <label>情绪强度<input v-model.number="form.emotionIntensity" type="number" min="0" max="100" /></label>
                  <label>初始场景<select v-model="form.scene"><option value="first_meet">初识</option><option value="familiar">熟悉</option><option value="daily">日常</option><option value="plot">剧情中</option></select></label>
                </div>
                <div class="info-callout"><span>i</span><p>关系、情绪和场景会保存在每个用户的会话中。修改这里，只影响新建会话；已有会话会继续使用自己的状态。</p></div>
              </template>

              <template v-else-if="activeSection === 'media'">
                <div class="subsection-heading"><h4>照片策略</h4><span>只允许引用角色素材目录中的 asset ID</span></div>
                <label class="switch-field"><input v-model="form.photoEnabled" type="checkbox" /><span>允许角色发送照片</span></label>
                <label>可用素材 ID<small class="field-hint">例如 photo-1、photo-2，用逗号或换行分隔</small><textarea v-model="form.photoAssetsText" rows="2" /></label>
                <div class="field-grid three-columns">
                  <label>最低熟悉度<input v-model.number="form.photoMinFamiliarity" type="number" min="0" max="100" /></label>
                  <label>最低信任值<input v-model.number="form.photoMinTrust" type="number" min="0" max="100" /></label>
                  <label>条件不足时<select v-model="form.photoEarlyOutcome"><option value="delay">延迟再发</option><option value="decline">直接拒绝</option><option value="send">仍然发送</option></select></label>
                </div>
                <div class="subsection-heading"><h4>语音策略</h4><span>音色由后端服务配置，前端不保存密钥</span></div>
                <div class="field-grid three-columns">
                  <label>发送模式<select v-model="form.voiceMode"><option value="never">不发送</option><option value="on_request">用户请求时</option><option value="occasional">偶尔发送</option><option value="emotional">情绪触发</option></select></label>
                  <label>音色 ID<input v-model="form.voiceId" type="text" /></label>
                  <label>展示方式<select v-model="form.displayMode"><option value="text_and_audio">文字 + 语音</option><option value="audio_only">仅语音</option></select></label>
                </div>
                <div class="info-callout"><span>!</span><p>照片和语音只使用虚构素材或已授权合成音色，不将红包、转账或现实身份作为解锁条件。</p></div>
              </template>

              <template v-else-if="activeSection === 'fallback'">
                <div class="subsection-heading"><h4>模型不可用时的短回复</h4><span>建议每条保持口语化、简短</span></div>
                <label>暂不发送照片时<textarea v-model="form.fallbackPhoto" rows="3" maxlength="80" /></label>
                <label>决定发送照片时<textarea v-model="form.fallbackPhotoSend" rows="3" maxlength="80" /></label>
                <label>用户索要语音时<textarea v-model="form.fallbackVoice" rows="3" maxlength="80" /></label>
                <label>角色需要回避时<textarea v-model="form.fallbackAvoid" rows="3" maxlength="80" /></label>
                <label>固定安全说明<small class="field-hint">服务端安全规则优先于角色补充规则。</small><textarea v-model="form.safetyNotes" rows="4" /></label>
                <div class="info-callout safety"><span>✓</span><p>后台可以调整角色的语气和剧情，但不能覆盖虚拟角色标识、反诈骗、敏感信息和现实身份边界。</p></div>
              </template>

              <div v-if="issues.length" class="validation-panel">
                <div class="validation-heading"><strong>配置检查</strong><span>{{ issues.length }} 项提示</span></div>
                <p v-for="issue in issues" :key="issue.path + issue.message" :class="issue.level">{{ issueLabel(issue) }}</p>
              </div>
            </section>
          </div>

          <aside class="preview-column">
            <div class="preview-heading">
              <div><span class="eyebrow">LIVE PREVIEW</span><h3>草稿测试</h3></div>
              <button class="reset-preview" type="button" @click="resetPreview">清空</button>
            </div>
            <div class="preview-note">这里使用当前草稿配置，不会写入正式聊天记录。</div>
            <div class="preview-state">
              <span>熟悉度 {{ stateLabel(previewState?.relationship.familiarity ?? form.familiarity) }}</span>
              <span>{{ stateLabel(previewState?.emotion.dominant ?? form.emotion) }}</span>
              <span>{{ stateLabel(previewState?.scene.current ?? form.scene) }}</span>
            </div>
            <div class="preview-messages">
              <div v-if="!previewMessages.length" class="preview-empty"><span>✦</span><p>输入一句话，看看这个草稿角色会怎样回应。</p></div>
              <div v-for="message in previewMessages" :key="message.id" class="preview-message" :class="message.role">
                <img v-if="message.role === 'assistant'" :src="form.avatarPath" :alt="form.name" />
                <div v-if="message.message_type === 'text'" class="preview-bubble">{{ message.content }}</div>
                <img v-else-if="message.message_type === 'image'" class="preview-image" :src="message.image_url || ''" alt="预览图片" />
                <div v-else class="preview-bubble">语音消息{{ message.audio_duration_ms ? ` · ${message.audio_duration_ms}ms` : '' }}</div>
              </div>
              <div v-if="isPreviewing" class="preview-typing"><i /><i /><i /></div>
            </div>
            <div class="preview-composer">
              <textarea v-model="previewInput" rows="2" placeholder="测试一句话…" @keydown.enter.exact.prevent="preview" />
              <button type="button" :disabled="isPreviewing || !previewInput.trim()" @click="preview">{{ isPreviewing ? '生成中…' : '发送测试' }}</button>
            </div>
            <details v-if="Object.keys(previewDebug).length" class="debug-details">
              <summary>查看本轮行为判定</summary>
              <pre>{{ JSON.stringify(previewDebug, null, 2) }}</pre>
            </details>
          </aside>
        </div>
      </section>
      <section v-else class="admin-empty">正在准备角色工作台…</section>
    </div>
  </main>
</template>

<style scoped>
.admin-workspace { min-height: 100vh; color: #282b39; background: #f7f7fa; }
.admin-topbar { display: flex; align-items: center; gap: 34px; height: 72px; padding: 0 32px; background: #fff; border-bottom: 1px solid #e8e8ee; }
.admin-brand { display: flex; align-items: center; gap: 11px; min-width: 225px; }
.admin-brand .brand-dot { display: block; width: 12px; height: 12px; background: #7667e8; border-radius: 50%; box-shadow: 0 0 0 5px #e8e5ff; }
.admin-brand strong, .admin-brand small { display: block; }
.admin-brand strong { font-size: 15px; }
.admin-brand small { margin-top: 4px; color: #a0a2af; font-size: 9px; letter-spacing: .13em; }
.workspace-nav { display: flex; gap: 4px; align-self: stretch; }
.workspace-nav button { padding: 0 15px; color: #9a9cab; background: transparent; border: 0; border-bottom: 2px solid transparent; font-size: 12px; }
.workspace-nav button.active { color: #665bd1; border-bottom-color: #7667e8; }
.admin-mode { margin-left: auto; color: #a2a3af; font-size: 11px; }
.admin-body { display: flex; min-height: calc(100vh - 72px); }
.admin-list-panel { display: flex; flex: 0 0 285px; flex-direction: column; padding: 30px 20px; background: #f0f1f6; border-right: 1px solid #e2e3eb; }
.admin-list-heading { display: flex; align-items: flex-start; justify-content: space-between; }
.list-heading-actions { display: flex; align-items: center; gap: 4px; }
.eyebrow { color: #9a9cab; font-size: 9px; font-weight: 700; letter-spacing: .14em; }
.admin-list-heading h1, .preview-heading h3, .section-heading h3 { margin: 7px 0 0; font-size: 18px; font-weight: 650; }
.icon-button, .reset-preview { padding: 5px; color: #848695; background: transparent; border: 0; font-size: 18px; }
.new-character-button { padding: 6px 8px; color: #655bd0; background: #e9e8ff; border: 0; border-radius: 7px; font-size: 10px; }
.list-description { margin: 12px 4px 22px; color: #9294a3; font-size: 11px; line-height: 1.7; }
.admin-list-loading { padding: 18px 10px; color: #999baa; font-size: 12px; }
.admin-character-item { display: flex; align-items: center; gap: 11px; width: 100%; padding: 11px 10px; margin-bottom: 6px; text-align: left; color: inherit; background: transparent; border: 1px solid transparent; border-radius: 12px; }
.admin-character-item:hover { background: #e8e9f0; }
.admin-character-item.selected { background: #fff; border-color: #dfdef0; box-shadow: 0 6px 16px rgba(54, 52, 91, .06); }
.admin-character-item img, .editor-title img, .preview-message > img { width: 42px; height: 42px; object-fit: cover; border-radius: 12px; background: #ddd; }
.admin-character-copy { min-width: 0; flex: 1; }
.admin-character-name, .admin-character-meta { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.admin-character-name { font-size: 13px; font-weight: 600; }
.admin-character-meta { margin-top: 4px; color: #a0a1ad; font-size: 10px; }
.status-dot { width: 7px; height: 7px; background: #55c49a; border-radius: 50%; }
.status-dot.muted { background: #b5b5bf; }
.admin-list-footer { display: flex; justify-content: space-between; margin-top: auto; padding: 18px 4px 0; color: #a2a3af; font-size: 10px; }
.admin-editor-panel { min-width: 0; flex: 1; }
.editor-header { display: flex; align-items: center; justify-content: space-between; min-height: 86px; padding: 18px 32px; background: #fff; border-bottom: 1px solid #e8e8ee; }
.editor-title { display: flex; align-items: center; gap: 12px; min-width: 0; }
.editor-title img { width: 48px; height: 48px; }
.title-line { display: flex; align-items: center; gap: 8px; }
.title-line h2 { margin: 0; font-size: 17px; }
.editor-title p { margin: 5px 0 0; color: #a0a1ad; font-size: 10px; }
.status-badge, .offline-badge { padding: 4px 7px; border-radius: 5px; font-size: 10px; }
.status-badge.published { color: #4d9a78; background: #e8f7ef; }
.status-badge.draft { color: #aa7c48; background: #fff4df; }
.offline-badge { color: #8d8e99; background: #eeeeF2; }
.editor-actions { display: flex; align-items: center; gap: 7px; }
.text-button, .secondary-button, .primary-button, .validate-button { padding: 8px 11px; border: 0; border-radius: 8px; font-size: 11px; }
.text-button { color: #828391; background: transparent; }
.secondary-button { color: #655bd0; background: #f0efff; }
.primary-button { color: #fff; background: #7667e8; box-shadow: 0 5px 12px rgba(118, 103, 232, .17); }
.primary-button:disabled, .secondary-button:disabled { cursor: wait; opacity: .5; }
.model-save { margin-top: 18px; }
.status-message, .admin-error { margin: 14px 32px 0; padding: 9px 12px; border-radius: 8px; font-size: 11px; }
.status-message { color: #4f8f74; background: #eaf8f0; }
.admin-error { color: #a45769; background: #fff0f3; }
.editor-layout { display: grid; grid-template-columns: minmax(0, 1fr) 330px; gap: 20px; padding: 24px 32px 40px; }
.form-column { min-width: 0; }
.section-tabs { display: flex; gap: 3px; margin-bottom: 14px; overflow-x: auto; }
.section-tabs button { min-width: 145px; padding: 10px 12px; text-align: left; color: #9596a3; background: transparent; border: 0; border-bottom: 2px solid transparent; }
.section-tabs button.active { color: #6359d0; background: #fff; border-bottom-color: #7667e8; }
.section-tabs span, .section-tabs small { display: block; }
.section-tabs span { font-size: 11px; font-weight: 600; }
.section-tabs small { margin-top: 4px; color: #aaabb5; font-size: 9px; }
.form-section { padding: 22px; background: #fff; border: 1px solid #e8e8ee; border-radius: 13px; }
.section-heading, .preview-heading, .subsection-heading, .validation-heading { display: flex; align-items: center; justify-content: space-between; }
.validate-button { color: #655bd0; background: #f1efff; }
.field-grid { display: grid; gap: 14px; margin-top: 16px; }
.field-grid.two-columns { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.field-grid.three-columns { grid-template-columns: repeat(3, minmax(0, 1fr)); }
label { display: block; margin-top: 16px; color: #6f7180; font-size: 11px; }
.field-grid label { margin-top: 0; }
input, textarea, select { display: block; width: 100%; margin-top: 7px; padding: 9px 10px; color: #383b49; background: #fafafd; border: 1px solid #e6e6ee; border-radius: 8px; outline: 0; font-size: 12px; }
textarea { min-height: 42px; resize: vertical; line-height: 1.55; }
input:focus, textarea:focus, select:focus { border-color: #b5aff5; box-shadow: 0 0 0 3px #f0efff; }
.field-hint { display: block; margin-top: 5px; color: #aaaab5; font-size: 10px; line-height: 1.5; }
.subsection-heading { margin-top: 24px; padding-bottom: 9px; border-bottom: 1px solid #f0f0f4; }
.subsection-heading h4 { margin: 0; color: #505260; font-size: 12px; }
.subsection-heading span { color: #aaaab5; font-size: 10px; }
.state-sliders { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px 20px; margin-top: 16px; }
.state-sliders label { margin: 0; }
.state-sliders strong { float: right; color: #7667e8; font-size: 12px; }
input[type='range'] { height: 4px; padding: 0; accent-color: #7667e8; border: 0; box-shadow: none; }
.switch-field { display: flex; align-items: center; gap: 8px; margin: 17px 0 2px; color: #585a69; }
.switch-field input { width: 16px; height: 16px; margin: 0; accent-color: #7667e8; }
.info-callout { display: flex; gap: 9px; margin-top: 20px; padding: 11px 12px; color: #858694; background: #f7f7fb; border-radius: 8px; font-size: 10px; line-height: 1.6; }
.info-callout span { display: inline-grid; flex: 0 0 16px; width: 16px; height: 16px; place-items: center; color: #7667e8; background: #ebe9ff; border-radius: 50%; font-weight: 700; }
.info-callout p { margin: 0; }
.info-callout.safety { color: #688875; background: #f0faf4; }
.info-callout.safety span { color: #4d9a78; background: #dbf2e5; }
.validation-panel { margin-top: 22px; padding: 13px; background: #fff9ed; border: 1px solid #f5e5c2; border-radius: 9px; }
.validation-heading strong { color: #806035; font-size: 11px; }
.validation-heading span { color: #b08d56; font-size: 10px; }
.validation-panel p { margin: 8px 0 0; color: #9b6d37; font-size: 10px; }
.preview-column { display: flex; min-height: 620px; flex-direction: column; padding: 19px; background: #fff; border: 1px solid #e8e8ee; border-radius: 13px; }
.preview-heading h3 { margin-bottom: 0; }
.reset-preview { font-size: 11px; }
.preview-note { margin: 12px 0; color: #9899a6; font-size: 10px; line-height: 1.5; }
.preview-state { display: flex; gap: 5px; margin-bottom: 12px; overflow-x: auto; }
.preview-state span { padding: 5px 7px; color: #7169b5; background: #f1efff; border-radius: 5px; white-space: nowrap; font-size: 9px; }
.preview-messages { flex: 1; min-height: 300px; max-height: 430px; overflow-y: auto; padding: 15px 4px; background: #fafafd; border: 1px solid #f0f0f4; border-radius: 10px; }
.preview-empty { display: grid; place-items: center; height: 100%; min-height: 260px; padding: 30px; color: #a5a6b2; text-align: center; }
.preview-empty span { color: #7667e8; font-size: 22px; }
.preview-empty p { max-width: 150px; margin: 10px 0 0; font-size: 11px; line-height: 1.6; }
.preview-message { display: flex; align-items: flex-end; gap: 7px; margin: 10px 5px; }
.preview-message.user { justify-content: flex-end; }
.preview-message > img { width: 25px; height: 25px; border-radius: 8px; }
.preview-bubble { max-width: 78%; padding: 8px 10px; color: #464856; background: #efeff5; border-radius: 11px 11px 11px 3px; font-size: 11px; line-height: 1.55; white-space: pre-wrap; }
.preview-message.user .preview-bubble { color: #fff; background: #7667e8; border-radius: 11px 11px 3px 11px; }
.preview-image { width: 150px !important; height: auto !important; max-height: 200px; border-radius: 10px !important; }
.preview-typing { display: flex; gap: 3px; padding: 10px 12px; }
.preview-typing i { width: 4px; height: 4px; background: #aaaab4; border-radius: 50%; animation: preview-typing 1s infinite; }
.preview-typing i:nth-child(2) { animation-delay: .15s; }.preview-typing i:nth-child(3) { animation-delay: .3s; }
@keyframes preview-typing { 35% { transform: translateY(-3px); opacity: 1; } 100% { opacity: .45; } }
.preview-composer { display: flex; gap: 7px; align-items: flex-end; margin-top: 11px; }
.preview-composer textarea { flex: 1; min-height: 42px; margin: 0; }
.preview-composer button { padding: 9px 10px; color: #fff; background: #7667e8; border: 0; border-radius: 8px; font-size: 10px; white-space: nowrap; }
.preview-composer button:disabled { cursor: wait; opacity: .5; }
.debug-details { margin-top: 12px; color: #858694; font-size: 10px; }
.debug-details summary { cursor: pointer; }
.debug-details pre { max-height: 180px; overflow: auto; padding: 9px; margin-top: 7px; color: #626474; background: #f7f7fa; border-radius: 7px; font-size: 9px; white-space: pre-wrap; }
.admin-empty { display: grid; flex: 1; place-items: center; color: #9a9ba8; font-size: 12px; }

@media (max-width: 1100px) {
  .editor-layout { grid-template-columns: 1fr; }
  .preview-column { min-height: 0; }
  .preview-messages { max-height: 320px; }
}

@media (max-width: 760px) {
  .admin-topbar { gap: 14px; height: 62px; padding: 0 15px; }
  .admin-brand { min-width: 0; }.admin-brand small, .admin-mode { display: none; }
  .workspace-nav { margin-left: auto; }.workspace-nav button { padding: 0 7px; font-size: 10px; }
  .admin-body { display: block; }
  .admin-list-panel { padding: 17px 12px 10px; border-right: 0; border-bottom: 1px solid #e2e3eb; }
  .list-description, .admin-list-footer { display: none; }
  .admin-list-heading { align-items: center; }.admin-list-heading h1 { margin-top: 4px; font-size: 15px; }
  .admin-list-panel > .admin-character-item { display: inline-flex; width: auto; min-width: 145px; margin: 14px 4px 0 0; }
  .admin-character-item img { width: 34px; height: 34px; border-radius: 9px; }.admin-character-meta { font-size: 9px; }
  .admin-editor-panel { width: 100%; }
  .editor-header { align-items: flex-start; flex-direction: column; gap: 14px; padding: 17px 15px; }
  .editor-actions { flex-wrap: wrap; }.editor-layout { padding: 15px; }
  .form-section { padding: 16px; }.field-grid.two-columns, .field-grid.three-columns, .state-sliders { grid-template-columns: 1fr; }
  .section-tabs button { min-width: 125px; padding: 8px 9px; }.section-tabs small { display: none; }
}
</style>
