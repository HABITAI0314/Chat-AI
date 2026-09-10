<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { adminApi } from '../../api/admin'
import type {
  AdminCharacterDetail,
  AdminCharacterSummary,
  CharacterDraftPayload,
  CharacterProfile,
  PreviewMessage,
  ValidationIssue,
} from '../../types/admin'

const sections = [
  { id: 'identity', label: '身份与人设', hint: '角色是谁，以及怎样说话' },
  { id: 'state', label: '关系与剧情', hint: '初始关系、情绪和场景目标' },
  { id: 'media', label: '图片与语音', hint: '媒体发送条件和素材白名单' },
  { id: 'fallback', label: '兜底与安全', hint: '异常回复和固定安全边界' },
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
let previewId = -1

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
    ? (clone(detail.value?.draft_profile || detail.value?.profile || {}) as Partial<CharacterProfile>)
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
    const id =
      selectedId.value && characters.value.some((item) => item.id === selectedId.value)
        ? selectedId.value
        : characters.value[0]?.id
    if (id) await selectCharacter(id)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载角色列表失败'
    isLoading.value = false
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
    if (showMessage) statusMessage.value = '草稿已保存，尚未发布到前台聊天。'
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
    statusMessage.value = result.valid ? '配置校验通过，各项边界符合规范。' : '配置存在需要修正的提醒。'
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
    statusMessage.value = `已成功发布 v${updated.profile_version}！前台聊天端即刻应用最新人设与规则。`
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
    statusMessage.value = updated.is_active ? '角色已启用。' : '角色已停用，将不会出现在前台会话选择列表中。'
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
    statusMessage.value = '已克隆复制角色，请修改编码与名称后再行发布。'
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
    statusMessage.value = '已新建草稿角色，请完善各项人设与策略后发布。'
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

onMounted(() => {
  refresh()
})
</script>

<template>
  <div class="character-studio-container">
    <aside class="studio-sidebar">
      <div class="sidebar-top">
        <div>
          <span class="eyebrow">CHARACTERS</span>
          <h2>角色列表</h2>
        </div>
        <div class="sidebar-actions">
          <button class="new-btn" type="button" @click="createCharacter">+ 新建角色</button>
          <button class="icon-btn" type="button" title="刷新列表" @click="refresh">↻</button>
        </div>
      </div>
      <p class="sidebar-desc">选择角色以配置人设、初始状态与媒体策略，发布后直接生效。</p>

      <div v-if="isLoading && !characters.length" class="sidebar-loading">正在读取角色库…</div>
      <div class="character-scroll">
        <button
          v-for="character in characters"
          :key="character.id"
          class="character-item"
          :class="{ selected: character.id === selectedId }"
          type="button"
          @click="selectCharacter(character.id)"
        >
          <img :src="character.avatar_url" :alt="character.name" />
          <div class="item-meta">
            <span class="item-name">{{ character.name }}</span>
            <span class="item-code">{{ character.code }} · v{{ character.profile_version }}</span>
          </div>
          <span class="status-dot" :class="{ muted: !character.is_active }" :title="character.is_active ? '已启用' : '已停用'" />
        </button>
      </div>

      <div class="sidebar-footer">
        <span>共 {{ characters.length }} 个角色</span>
        <span>草稿需发布才会在前台生效</span>
      </div>
    </aside>

    <section v-if="detail" class="studio-main">
      <header class="studio-header">
        <div class="character-headline">
          <img :src="form.avatarPath" :alt="form.name" />
          <div>
            <div class="title-row">
              <h2>{{ form.name || '未命名角色' }}</h2>
              <span class="status-tag" :class="detail.has_draft ? 'draft' : detail.config_status">
                {{ statusLabel(detail.config_status, detail.has_draft) }}
              </span>
              <span v-if="!detail.is_active" class="offline-tag">已停用</span>
            </div>
            <p>{{ form.code || '等待设置编码' }} · 当前生效发布版本 v{{ detail.profile_version }}</p>
          </div>
        </div>

        <div class="header-operations">
          <button class="btn-ghost" type="button" title="克隆当前角色副本" @click="duplicate">复制</button>
          <button class="btn-ghost" type="button" @click="toggleActive">{{ detail.is_active ? '停用' : '启用' }}</button>
          <button class="btn-outline" type="button" :disabled="isSaving || isPublishing" @click="saveDraft()">
            {{ isSaving ? '保存中…' : '保存草稿' }}
          </button>
          <button class="btn-solid" type="button" :disabled="isSaving || isPublishing" @click="publish">
            {{ isPublishing ? '发布中…' : '发布配置' }}
          </button>
        </div>
      </header>

      <div v-if="statusMessage" class="feedback-banner success">{{ statusMessage }}</div>
      <div v-if="errorMessage" class="feedback-banner error">{{ errorMessage }}</div>

      <div class="studio-content-layout">
        <!-- 表单区域 -->
        <div class="editor-col">
          <nav class="inner-tabs" aria-label="角色属性分类">
            <button
              v-for="section in sections"
              :key="section.id"
              type="button"
              :class="{ active: section.id === activeSection }"
              @click="activeSection = section.id"
            >
              <span class="tab-label">{{ section.label }}</span>
              <small class="tab-hint">{{ section.hint }}</small>
            </button>
          </nav>

          <div class="form-card">
            <div class="card-header">
              <div>
                <span class="eyebrow">{{ activeSection.toUpperCase() }}</span>
                <h3>{{ currentSection.label }}</h3>
              </div>
              <button class="btn-validate" type="button" @click="validate">
                校验配置规则
              </button>
            </div>

            <!-- 1. 身份与人设 -->
            <template v-if="activeSection === 'identity'">
              <div class="field-grid two-cols">
                <label>角色名称<input v-model="form.name" type="text" maxlength="100" placeholder="例如：苏禾" /></label>
                <label>唯一编码<input v-model="form.code" type="text" maxlength="64" placeholder="例如：suhe" /></label>
              </div>
              <label>头像路径<input v-model="form.avatarPath" type="text" placeholder="/static/characters/suhe/avatar.svg" /></label>
              <div class="field-grid two-cols">
                <label>对外简介<textarea v-model="form.description" rows="3" placeholder="列表展示的一句话简介" /></label>
                <label>背景与当前生活<textarea v-model="form.background" rows="3" placeholder="人物身世、成长背景或工作日常" /></label>
              </div>
              <label>性格标签<small class="hint">用逗号、顿号或换行分隔，例如：慢热、嘴硬、细腻</small>
                <textarea v-model="form.personalityText" rows="3" />
              </label>
              <div class="field-grid three-cols">
                <label>称呼用户为<input v-model="form.address" type="text" placeholder="你" /></label>
                <label>句子长度
                  <select v-model="form.sentenceLength">
                    <option value="very_short">很短（口语化短促）</option>
                    <option value="short">短句（默认日常聊天）</option>
                    <option value="medium">适中（完整表意）</option>
                  </select>
                </label>
                <label>说话口头禅<textarea v-model="form.habitsText" rows="2" placeholder="常挂在嘴边的小词或语气" /></label>
              </div>
              <label>补充人设规则<small class="hint">仅填写角色专属行为边界或习惯，不要填写现实交易或 API 密钥。</small>
                <textarea v-model="form.customRules" rows="4" placeholder="例如：不喜欢被连续追问，被触碰隐私会主动转开话题。" />
              </label>
            </template>

            <!-- 2. 关系与剧情 -->
            <template v-else-if="activeSection === 'state'">
              <div class="field-grid two-cols">
                <label>主要行动目标
                  <select v-model="form.primaryGoal">
                    <option value="get_familiar">逐渐熟悉（自然破冰）</option>
                    <option value="sell_tea">推进虚构茶铺剧情</option>
                    <option value="share_life">分享日常生活碎片</option>
                    <option value="observe">先保持距离观察用户</option>
                  </select>
                </label>
                <label>剧情名称<input v-model="form.plotName" type="text" placeholder="可选，例如：虚构茶铺试饮剧情" /></label>
              </div>

              <div class="sub-heading">
                <h4>新会话初始关系数值</h4>
                <span>0～100，聊天交互中会随上下文动态流转</span>
              </div>
              <div class="slider-grid">
                <label>熟悉度 <strong>{{ form.familiarity }}</strong>
                  <input v-model.number="form.familiarity" type="range" min="0" max="100" />
                </label>
                <label>信任值 <strong>{{ form.trust }}</strong>
                  <input v-model.number="form.trust" type="range" min="0" max="100" />
                </label>
                <label>好感度 <strong>{{ form.affection }}</strong>
                  <input v-model.number="form.affection" type="range" min="0" max="100" />
                </label>
                <label>烦躁度 <strong>{{ form.annoyance }}</strong>
                  <input v-model.number="form.annoyance" type="range" min="0" max="100" />
                </label>
              </div>

              <div class="field-grid three-cols">
                <label>初始情绪
                  <select v-model="form.emotion">
                    <option value="calm">平静</option>
                    <option value="happy">开心</option>
                    <option value="shy">害羞</option>
                    <option value="curious">好奇</option>
                    <option value="guarded">戒备</option>
                    <option value="sad">低落</option>
                  </select>
                </label>
                <label>情绪强度 (0-100)<input v-model.number="form.emotionIntensity" type="number" min="0" max="100" /></label>
                <label>初始场景阶段
                  <select v-model="form.scene">
                    <option value="first_meet">初识</option>
                    <option value="familiar">熟悉</option>
                    <option value="daily">日常</option>
                    <option value="plot">剧情中</option>
                  </select>
                </label>
              </div>
              <div class="info-box">
                <span class="icon">i</span>
                <p>关系、情绪和场景会持久化记录在用户的独立会话中。此处的设置只对新建会话生效，不破坏已有用户的聊天关系进度。</p>
              </div>
            </template>

            <!-- 3. 图片与语音 -->
            <template v-else-if="activeSection === 'media'">
              <div class="sub-heading">
                <h4>照片发送策略</h4>
                <span>仅允许引用角色的白名单素材 ID</span>
              </div>
              <label class="checkbox-row">
                <input v-model="form.photoEnabled" type="checkbox" />
                <span>允许该角色在合适时机发送照片</span>
              </label>
              <label>白名单素材 ID<small class="hint">例如 photo-1、photo-2，用逗号或换行分隔</small>
                <textarea v-model="form.photoAssetsText" rows="2" />
              </label>
              <div class="field-grid three-cols">
                <label>最低熟悉度门槛<input v-model.number="form.photoMinFamiliarity" type="number" min="0" max="100" /></label>
                <label>最低信任值门槛<input v-model.number="form.photoMinTrust" type="number" min="0" max="100" /></label>
                <label>未达门槛表现
                  <select v-model="form.photoEarlyOutcome">
                    <option value="delay">延迟再发（找借口推后）</option>
                    <option value="decline">直接委婉拒绝</option>
                    <option value="send">仍然发送（测试用）</option>
                  </select>
                </label>
              </div>

              <div class="sub-heading" style="margin-top: 28px">
                <h4>语音回复策略</h4>
                <span>音色 ID 由全局模型或角色专属指定</span>
              </div>
              <div class="field-grid three-cols">
                <label>发送触发模式
                  <select v-model="form.voiceMode">
                    <option value="never">不发送语音</option>
                    <option value="on_request">用户索要时发送</option>
                    <option value="occasional">偶尔主动发送</option>
                    <option value="emotional">情绪高涨时触发</option>
                  </select>
                </label>
                <label>角色音色 ID<input v-model="form.voiceId" type="text" placeholder="fictional-default" /></label>
                <label>气泡展示方式
                  <select v-model="form.displayMode">
                    <option value="text_and_audio">文字 + 语音条</option>
                    <option value="audio_only">纯语音消息</option>
                  </select>
                </label>
              </div>
              <div class="info-box alert">
                <span class="icon">!</span>
                <p>照片和语音素材遵循虚构规范，严禁将金钱、转账或现实身份索要作为解锁条件。</p>
              </div>
            </template>

            <!-- 4. 兜底与安全 -->
            <template v-else-if="activeSection === 'fallback'">
              <div class="sub-heading">
                <h4>本地确定性短回复（模型不可用或兜底触发时）</h4>
                <span>单条尽量口语化短句，符合该角色的调性</span>
              </div>
              <label>暂不发照片时的回复<textarea v-model="form.fallbackPhoto" rows="2" maxlength="80" placeholder="例如：照片啊，先不急，等熟一点再说。" /></label>
              <label>决定发照片时的引导语<textarea v-model="form.fallbackPhotoSend" rows="2" maxlength="80" placeholder="例如：好吧，给你看一张。" /></label>
              <label>用户索要语音时的回复<textarea v-model="form.fallbackVoice" rows="2" maxlength="80" placeholder="例如：等下发你语音。" /></label>
              <label>角色需要回避时的回复<textarea v-model="form.fallbackAvoid" rows="2" maxlength="80" placeholder="例如：这个之后再说吧。" /></label>
              <label>角色固定安全说明<small class="hint">强制遵守系统安全底线，优先级高于自定义人设。</small>
                <textarea v-model="form.safetyNotes" rows="3" />
              </label>
              <div class="info-box safety">
                <span class="icon">✓</span>
                <p>安全合规机制：后台可以充分调整角色的语气与虚构剧情，但永远不会覆盖虚拟角色标识、反诈防线与隐私保护原则。</p>
              </div>
            </template>

            <!-- 校验提示 -->
            <div v-if="issues.length" class="validation-summary">
              <div class="val-header">
                <strong>配置校验提醒</strong>
                <span>共 {{ issues.length }} 项提示</span>
              </div>
              <p v-for="issue in issues" :key="issue.path + issue.message" :class="issue.level">
                {{ issueLabel(issue) }}
              </p>
            </div>
          </div>
        </div>

        <!-- 右侧专属：实时草稿对话测试 -->
        <aside class="preview-col">
          <div class="preview-head">
            <div>
              <span class="eyebrow">LIVE PREVIEW</span>
              <h3>草稿即时测试</h3>
            </div>
            <button class="btn-clear" type="button" @click="resetPreview">清空会话</button>
          </div>
          <p class="preview-tip">使用当前编辑区草稿配置进行交互验证，不影响正式聊天记录。</p>

          <div class="preview-state-tags">
            <span>熟悉度 {{ stateLabel(previewState?.relationship.familiarity ?? form.familiarity) }}</span>
            <span>情绪 {{ stateLabel(previewState?.emotion.dominant ?? form.emotion) }}</span>
            <span>场景 {{ stateLabel(previewState?.scene.current ?? form.scene) }}</span>
          </div>

          <div class="preview-chat-body">
            <div v-if="!previewMessages.length" class="preview-blank">
              <span class="sparkle">✦</span>
              <p>向 {{ form.name || '角色' }} 发送一句话，测试当前草稿的人设回复。</p>
            </div>
            <div v-for="message in previewMessages" :key="message.id" class="p-msg" :class="message.role">
              <img v-if="message.role === 'assistant'" :src="form.avatarPath" :alt="form.name" />
              <div v-if="message.message_type === 'text'" class="p-bubble">{{ message.content }}</div>
              <img v-else-if="message.message_type === 'image'" class="p-image" :src="message.image_url || ''" alt="预览照片" />
              <div v-else class="p-bubble">语音消息 · {{ message.audio_duration_ms ? `${message.audio_duration_ms}ms` : '已生成' }}</div>
            </div>
            <div v-if="isPreviewing" class="p-typing"><i /><i /><i /></div>
          </div>

          <div class="preview-composer-box">
            <textarea
              v-model="previewInput"
              rows="2"
              placeholder="输入测试消息，按 Enter 发送…"
              @keydown.enter.exact.prevent="preview"
            />
            <button type="button" :disabled="isPreviewing || !previewInput.trim()" @click="preview">
              {{ isPreviewing ? '…' : '发送' }}
            </button>
          </div>

          <details v-if="Object.keys(previewDebug).length" class="debug-box">
            <summary>查看本轮 LangGraph 行为决策详情</summary>
            <pre>{{ JSON.stringify(previewDebug, null, 2) }}</pre>
          </details>
        </aside>
      </div>
    </section>

    <div v-else class="studio-loading-state">
      正在载入角色工坊数据…
    </div>
  </div>
</template>

<style scoped>
.character-studio-container {
  display: flex;
  min-height: calc(100vh - 64px);
  background: #f7f7fa;
}

/* 侧边栏：角色列表 */
.studio-sidebar {
  display: flex;
  flex: 0 0 330px;
  width: 330px;
  flex-direction: column;
  padding: 30px 20px;
  background: #f0f1f6;
  border-right: 1px solid #e2e3eb;
}
.sidebar-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}
.eyebrow {
  color: #9a9cab;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: .14em;
  display: block;
}
.sidebar-top h2 {
  margin: 4px 0 0;
  font-size: 17px;
  font-weight: 650;
  color: #262836;
}
.sidebar-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}
.new-btn {
  padding: 6px 9px;
  color: #655bd0;
  background: #e9e8ff;
  border: 0;
  border-radius: 7px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: background .15s;
}
.new-btn:hover {
  background: #dedbff;
}
.icon-btn {
  padding: 4px 8px;
  color: #7b7d8c;
  background: transparent;
  border: 0;
  font-size: 16px;
  cursor: pointer;
}
.sidebar-desc {
  margin: 10px 2px 18px;
  color: #9294a3;
  font-size: 11px;
  line-height: 1.6;
}
.sidebar-loading {
  padding: 20px 10px;
  color: #999baa;
  font-size: 12px;
}
.character-scroll {
  flex: 1;
  overflow-y: auto;
}
.character-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px;
  margin-bottom: 7px;
  text-align: left;
  color: inherit;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 14px;
  cursor: pointer;
  transition: all .15s;
}
.character-item:hover {
  background: #e7e8f0;
}
.character-item.selected {
  background: #fff;
  border-color: #dfdef0;
  box-shadow: 0 4px 14px rgba(54, 52, 91, .06);
}
.character-item img {
  width: 44px;
  height: 44px;
  object-fit: cover;
  border-radius: 12px;
  background: #ddd;
}
.item-meta {
  min-width: 0;
  flex: 1;
}
.item-name {
  display: block;
  font-size: 13px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.item-code {
  display: block;
  margin-top: 3px;
  color: #a0a1ad;
  font-size: 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.status-dot {
  width: 7px;
  height: 7px;
  background: #55c49a;
  border-radius: 50%;
}
.status-dot.muted {
  background: #b5b5bf;
}
.sidebar-footer {
  display: flex;
  justify-content: space-between;
  margin-top: auto;
  padding: 16px 4px 0;
  color: #a2a3af;
  font-size: 10px;
}

/* 主编辑区 */
.studio-main {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
}
.studio-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 28px;
  background: #fff;
  border-bottom: 1px solid #e8e8ee;
}
.character-headline {
  display: flex;
  align-items: center;
  gap: 14px;
}
.character-headline img {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  object-fit: cover;
}
.title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.title-row h2 {
  margin: 0;
  font-size: 17px;
  color: #222533;
}
.character-headline p {
  margin: 4px 0 0;
  color: #9ea0ad;
  font-size: 11px;
}
.status-tag {
  padding: 3px 8px;
  border-radius: 5px;
  font-size: 10px;
  font-weight: 600;
}
.status-tag.published {
  color: #4d9a78;
  background: #e8f7ef;
}
.status-tag.draft {
  color: #aa7c48;
  background: #fff4df;
}
.offline-tag {
  padding: 3px 7px;
  color: #8d8e99;
  background: #eeeeF2;
  border-radius: 5px;
  font-size: 10px;
}
.header-operations {
  display: flex;
  align-items: center;
  gap: 8px;
}
.btn-ghost {
  padding: 7px 11px;
  color: #787a89;
  background: transparent;
  border: 0;
  border-radius: 7px;
  font-size: 12px;
  cursor: pointer;
}
.btn-ghost:hover {
  background: #f0f0f4;
  color: #484b5a;
}
.btn-outline {
  padding: 7px 14px;
  color: #655bd0;
  background: #f0efff;
  border: 0;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
}
.btn-outline:hover {
  background: #e5e3ff;
}
.btn-solid {
  padding: 7px 16px;
  color: #fff;
  background: #7667e8;
  border: 0;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(118, 103, 232, .2);
}
.btn-solid:hover {
  background: #6858e0;
}
.btn-solid:disabled, .btn-outline:disabled {
  opacity: .5;
  cursor: wait;
}

.feedback-banner {
  margin: 14px 28px 0;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 12px;
}
.feedback-banner.success {
  color: #3b8a67;
  background: #e8f7ee;
  border: 1px solid #c9efdc;
}
.feedback-banner.error {
  color: #a84b5c;
  background: #fff0f3;
  border: 1px solid #fed2db;
}

/* 左右分栏布局 */
.studio-content-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 20px;
  padding: 20px 28px 36px;
}
.editor-col {
  min-width: 0;
}
.inner-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 12px;
}
.inner-tabs button {
  flex: 1;
  padding: 10px 12px;
  text-align: left;
  background: #ececf3;
  border: 0;
  border-radius: 9px;
  color: #7b7d8d;
  cursor: pointer;
  transition: all .15s;
}
.inner-tabs button.active {
  background: #fff;
  color: #655bd0;
  box-shadow: 0 2px 8px rgba(50, 48, 80, .06);
}
.tab-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
}
.tab-hint {
  display: block;
  margin-top: 3px;
  font-size: 9px;
  color: #a3a4b0;
}
.form-card {
  padding: 22px;
  background: #fff;
  border: 1px solid #e8e8ee;
  border-radius: 12px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f2f2f6;
}
.card-header h3 {
  margin: 4px 0 0;
  font-size: 16px;
  color: #2b2e3c;
}
.btn-validate {
  padding: 6px 12px;
  color: #655bd0;
  background: #f0efff;
  border: 0;
  border-radius: 7px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
}
.field-grid {
  display: grid;
  gap: 14px;
  margin-top: 14px;
}
.field-grid.two-cols {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.field-grid.three-cols {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
label {
  display: block;
  margin-top: 14px;
  color: #6a6c7c;
  font-size: 11px;
  font-weight: 500;
}
.field-grid label {
  margin-top: 0;
}
input, textarea, select {
  display: block;
  width: 100%;
  margin-top: 6px;
  padding: 8px 10px;
  color: #313444;
  background: #fafafd;
  border: 1px solid #e3e3eb;
  border-radius: 8px;
  outline: 0;
  font-size: 12px;
  transition: border-color .15s;
}
textarea {
  min-height: 44px;
  resize: vertical;
  line-height: 1.5;
}
input:focus, textarea:focus, select:focus {
  border-color: #9d94eb;
  box-shadow: 0 0 0 3px #f0efff;
}
.hint {
  display: block;
  margin-top: 4px;
  color: #aaaab7;
  font-size: 10px;
  font-weight: 400;
}
.sub-heading {
  margin-top: 22px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f2f2f7;
}
.sub-heading h4 {
  margin: 0;
  color: #4b4d5e;
  font-size: 12px;
}
.sub-heading span {
  color: #aaaab6;
  font-size: 10px;
}
.slider-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px 20px;
  margin-top: 14px;
}
.slider-grid label {
  margin: 0;
}
.slider-grid strong {
  float: right;
  color: #7667e8;
  font-size: 12px;
}
input[type='range'] {
  height: 4px;
  padding: 0;
  accent-color: #7667e8;
  border: 0;
  box-shadow: none;
}
.checkbox-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 14px 0 2px;
  color: #555767;
}
.checkbox-row input {
  width: 16px;
  height: 16px;
  margin: 0;
  accent-color: #7667e8;
}
.info-box {
  display: flex;
  gap: 10px;
  margin-top: 18px;
  padding: 10px 12px;
  color: #7d808f;
  background: #f7f7fb;
  border-radius: 8px;
  font-size: 11px;
  line-height: 1.6;
}
.info-box .icon {
  display: inline-grid;
  flex: 0 0 16px;
  width: 16px;
  height: 16px;
  place-items: center;
  color: #7667e8;
  background: #ebe9ff;
  border-radius: 50%;
  font-weight: 700;
  font-size: 10px;
}
.info-box.alert {
  color: #a17042;
  background: #fff8ee;
}
.info-box.alert .icon {
  color: #cf7c2b;
  background: #fee6cb;
}
.info-box.safety {
  color: #518567;
  background: #edf8f2;
}
.info-box.safety .icon {
  color: #3b9467;
  background: #d3f3e2;
}
.validation-summary {
  margin-top: 20px;
  padding: 12px 14px;
  background: #fff8ec;
  border: 1px solid #f6e3c0;
  border-radius: 8px;
}
.val-header {
  display: flex;
  justify-content: space-between;
}
.val-header strong {
  color: #855f30;
  font-size: 11px;
}
.val-header span {
  color: #af8951;
  font-size: 10px;
}
.validation-summary p {
  margin: 6px 0 0;
  color: #9f6c31;
  font-size: 11px;
}

/* 右侧预览栏 */
.preview-col {
  display: flex;
  flex-direction: column;
  padding: 18px;
  background: #fff;
  border: 1px solid #e8e8ee;
  border-radius: 12px;
  min-height: 580px;
}
.preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.preview-head h3 {
  margin: 3px 0 0;
  font-size: 15px;
  color: #2b2e3c;
}
.btn-clear {
  padding: 4px 8px;
  color: #8c8ea0;
  background: transparent;
  border: 0;
  font-size: 11px;
  cursor: pointer;
}
.btn-clear:hover {
  color: #555767;
}
.preview-tip {
  margin: 8px 0 12px;
  color: #9ea0af;
  font-size: 10px;
  line-height: 1.5;
}
.preview-state-tags {
  display: flex;
  gap: 5px;
  margin-bottom: 12px;
  overflow-x: auto;
}
.preview-state-tags span {
  padding: 4px 7px;
  color: #6a61c5;
  background: #f1efff;
  border-radius: 5px;
  font-size: 10px;
  white-space: nowrap;
}
.preview-chat-body {
  flex: 1;
  min-height: 280px;
  max-height: 420px;
  overflow-y: auto;
  padding: 12px 6px;
  background: #fafafd;
  border: 1px solid #efeff5;
  border-radius: 9px;
}
.preview-blank {
  display: grid;
  place-items: center;
  height: 100%;
  min-height: 220px;
  padding: 24px;
  color: #a8a9b6;
  text-align: center;
}
.sparkle {
  color: #7667e8;
  font-size: 20px;
}
.preview-blank p {
  margin: 8px 0 0;
  font-size: 11px;
  line-height: 1.6;
}
.p-msg {
  display: flex;
  align-items: flex-end;
  gap: 7px;
  margin: 10px 4px;
}
.p-msg.user {
  justify-content: flex-end;
}
.p-msg > img {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  object-fit: cover;
}
.p-bubble {
  max-width: 78%;
  padding: 8px 10px;
  color: #424452;
  background: #efeff5;
  border-radius: 11px 11px 11px 3px;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
}
.p-msg.user .p-bubble {
  color: #fff;
  background: #7667e8;
  border-radius: 11px 11px 3px 11px;
}
.p-image {
  width: 140px;
  max-height: 180px;
  border-radius: 8px;
  object-fit: cover;
}
.p-typing {
  display: flex;
  gap: 3px;
  padding: 8px 10px;
}
.p-typing i {
  width: 4px;
  height: 4px;
  background: #abaab6;
  border-radius: 50%;
  animation: typing-dot 1s infinite;
}
.p-typing i:nth-child(2) { animation-delay: .15s; }
.p-typing i:nth-child(3) { animation-delay: .3s; }
@keyframes typing-dot { 35% { transform: translateY(-3px); opacity: 1; } 100% { opacity: .45; } }
.preview-composer-box {
  display: flex;
  gap: 6px;
  align-items: flex-end;
  margin-top: 10px;
}
.preview-composer-box textarea {
  flex: 1;
  min-height: 40px;
  margin: 0;
}
.preview-composer-box button {
  padding: 9px 12px;
  color: #fff;
  background: #7667e8;
  border: 0;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
}
.preview-composer-box button:disabled {
  opacity: .5;
  cursor: wait;
}
.debug-box {
  margin-top: 12px;
  color: #828493;
  font-size: 10px;
}
.debug-box summary {
  cursor: pointer;
}
.debug-box pre {
  max-height: 160px;
  overflow: auto;
  padding: 8px;
  margin-top: 6px;
  background: #f7f7fa;
  border-radius: 6px;
  font-size: 9px;
  white-space: pre-wrap;
}
.studio-loading-state {
  display: grid;
  flex: 1;
  place-items: center;
  color: #999baa;
  font-size: 13px;
}

@media (max-width: 1100px) {
  .studio-content-layout {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 760px) {
  .character-studio-container {
    flex-direction: column;
  }
  .studio-sidebar {
    border-right: 0;
    border-bottom: 1px solid #e2e3eb;
  }
  .inner-tabs {
    flex-wrap: wrap;
  }
}
</style>
