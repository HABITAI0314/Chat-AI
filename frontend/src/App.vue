<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import AdminWorkspace from './components/AdminWorkspace.vue'
import CharacterList from './components/CharacterList.vue'
import Composer from './components/Composer.vue'
import MessageBubble from './components/MessageBubble.vue'
import TransferDialog from './components/TransferDialog.vue'
import TypingIndicator from './components/TypingIndicator.vue'
import { api } from './api/chat'
import { adminApi } from './api/admin'
import type { Character, ChatMemory, Conversation, Message } from './types/chat'
import type { LLMConfig, PromptConfig } from './types/admin'

const route = ref(window.location.hash || '#/chat')
const showAdmin = computed(() => route.value.startsWith('#/admin'))
const syncRoute = () => {
  route.value = window.location.hash || '#/chat'
}
const openAdmin = (target?: 'characters' | 'prompts' | 'model') => {
  if (target === 'prompts') {
    window.location.hash = '#/admin/prompts'
  } else if (target === 'model') {
    window.location.hash = '#/admin/model'
  } else {
    window.location.hash = '#/admin/characters'
  }
}
const openChat = () => {
  window.location.hash = '#/chat'
}

const promptConfig = ref<PromptConfig>()
const llmConfig = ref<LLMConfig>()
const isSwitchingPrompt = ref(false)

const loadSystemSettings = async () => {
  try {
    const [pConfig, lConfig] = await Promise.all([
      adminApi.promptConfig().catch(() => undefined),
      adminApi.llmConfig().catch(() => undefined),
    ])
    if (pConfig) promptConfig.value = pConfig
    if (lConfig) llmConfig.value = lConfig
  } catch {
    // ignore
  }
}

const switchPromptVersion = async (version: number) => {
  if (isSwitchingPrompt.value || version === promptConfig.value?.active_version) return
  isSwitchingPrompt.value = true
  try {
    promptConfig.value = await adminApi.activatePromptVersion(version)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '切换提示词版本失败'
  } finally {
    isSwitchingPrompt.value = false
  }
}

const userKey = 'virtual-character-demo-user'
const userId = localStorage.getItem(userKey) || crypto.randomUUID()
localStorage.setItem(userKey, userId)

const characters = ref<Character[]>([])
const selectedCharacter = ref<Character>()
const conversation = ref<Conversation>()
const messages = ref<Message[]>([])
const draft = ref('')
const isTyping = ref(false)
const isLoading = ref(true)
const isSending = ref(false)
const isTransferring = ref(false)
const isResetting = ref(false)
const showTransfer = ref(false)
const showMemories = ref(false)
const isLoadingMemories = ref(false)
const memories = ref<ChatMemory[]>([])
const error = ref('')
let loadRequestId = 0

const selectedScene = computed(() => {
  const current = conversation.value?.scene?.current
  return ({
    first_meet: '初识',
    familiar: '熟悉',
    daily: '日常',
    plot: '剧情中',
  } as Record<string, string>)[String(current)] || '聊天中'
})

const loadConversation = async (character: Character) => {
  const requestId = ++loadRequestId
  selectedCharacter.value = character
  showTransfer.value = false
  isLoading.value = true
  error.value = ''
  try {
    const opened = await api.openConversation(userId, character.id)
    if (requestId !== loadRequestId) return
    conversation.value = opened
    const history = await api.history(opened.id, userId)
    if (requestId !== loadRequestId) return
    conversation.value = history.conversation
    messages.value = history.messages
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载聊天失败'
  } finally {
    if (requestId === loadRequestId) isLoading.value = false
  }
}

const sleep = (milliseconds: number) => new Promise((resolve) => setTimeout(resolve, milliseconds))

const memoryTypeLabel = (type: ChatMemory['memory_type']) => ({
  preference: '偏好',
  experience: '经历',
  important_event: '重要事件',
  boundary: '边界',
})[type] || '记忆'

const openMemoryManager = async () => {
  if (!conversation.value) return
  showMemories.value = true
  isLoadingMemories.value = true
  error.value = ''
  try {
    memories.value = await api.memories(conversation.value.id, userId)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载记忆失败'
  } finally {
    isLoadingMemories.value = false
  }
}

const removeMemory = async (memoryId: number) => {
  if (!conversation.value) return
  try {
    await api.deleteMemory(conversation.value.id, memoryId, userId)
    memories.value = memories.value.filter((item) => item.id !== memoryId)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '删除记忆失败'
  }
}

const resetConversation = async () => {
  if (!conversation.value || isSending.value || isResetting.value) return
  const confirmed = window.confirm('确定重新开始吗？聊天记录、关系进度和长期记忆都会被清空。')
  if (!confirmed) return
  isResetting.value = true
  error.value = ''
  try {
    conversation.value = await api.resetConversation(conversation.value.id, userId)
    messages.value = []
    memories.value = []
    draft.value = ''
    showMemories.value = false
  } catch (err) {
    error.value = err instanceof Error ? err.message : '重新开始失败'
  } finally {
    isResetting.value = false
  }
}

const sendMessage = async () => {
  const content = draft.value.trim()
  if (!content || !conversation.value || isSending.value) return
  const conversationId = conversation.value.id
  const tempId = -Date.now()
  messages.value.push({
    id: tempId,
    role: 'user',
    message_type: 'text',
    content,
    created_at: new Date().toISOString(),
  })
  draft.value = ''
  isSending.value = true
  isTyping.value = true
  error.value = ''
  try {
    const response = await api.send(conversationId, userId, content)
    if (conversation.value?.id !== conversationId) return
    const optimisticIndex = messages.value.findIndex((message) => message.id === tempId)
    if (optimisticIndex >= 0) messages.value.splice(optimisticIndex, 1, response.user_message)
    conversation.value.relationship = response.state.relationship
    conversation.value.emotion = response.state.emotion
    conversation.value.scene = response.state.scene
    for (const message of response.assistant_messages) {
      await sleep(message.delay_ms || 0)
      messages.value.push(message)
    }
  } catch (err) {
    if (conversation.value?.id === conversationId) {
      const optimisticIndex = messages.value.findIndex((message) => message.id === tempId)
      if (optimisticIndex >= 0) messages.value.splice(optimisticIndex, 1)
    }
    error.value = err instanceof Error ? err.message : '发送失败，请稍后再试'
  } finally {
    isTyping.value = false
    isSending.value = false
  }
}

const openTransferDialog = () => {
  if (!conversation.value || isSending.value || isResetting.value) return
  error.value = ''
  showTransfer.value = true
}

const sendTransfer = async (amountCents: number, note: string) => {
  if (!conversation.value || isSending.value || isResetting.value) return
  const conversationId = conversation.value.id
  const tempId = -Date.now()
  const transferId = `local-${Date.now()}`
  messages.value.push({
    id: tempId,
    role: 'user',
    message_type: 'transfer',
    content: `模拟转账 ¥${(amountCents / 100).toFixed(2)}`,
    metadata: {
      event: 'simulated_transfer',
      transfer_id: transferId,
      amount_cents: amountCents,
      note,
      status: 'pending',
    },
    created_at: new Date().toISOString(),
  })
  isSending.value = true
  isTransferring.value = true
  isTyping.value = true
  error.value = ''
  try {
    const response = await api.transfer(conversationId, userId, amountCents, note)
    if (conversation.value?.id !== conversationId) return
    const optimisticIndex = messages.value.findIndex((message) => message.id === tempId)
    if (optimisticIndex >= 0) messages.value.splice(optimisticIndex, 1, response.user_message)
    conversation.value.relationship = response.state.relationship
    conversation.value.emotion = response.state.emotion
    conversation.value.scene = response.state.scene
    showTransfer.value = false
    for (const message of response.assistant_messages) {
      await sleep(message.delay_ms || 0)
      messages.value.push(message)
    }
  } catch (err) {
    if (conversation.value?.id === conversationId) {
      const optimisticIndex = messages.value.findIndex((message) => message.id === tempId)
      if (optimisticIndex >= 0) messages.value.splice(optimisticIndex, 1)
    }
    error.value = err instanceof Error ? err.message : '转账失败，请稍后再试'
  } finally {
    isTyping.value = false
    isTransferring.value = false
    isSending.value = false
  }
}

// 时间戳判定与格式化逻辑（解决用户反馈的时间混乱与连环重复显示）
const shouldShowTime = (current: Message, prev?: Message): boolean => {
  if (!prev) return true
  const prevTime = new Date(prev.created_at).getTime()
  const currTime = new Date(current.created_at).getTime()
  if (isNaN(prevTime) || isNaN(currTime)) return false
  // 间隔超过 3 分钟（180,000 毫秒）才展示一次居中时间分隔线
  return currTime - prevTime > 180000
}

const formatTimeDivider = (value: string): string => {
  const date = new Date(value)
  if (isNaN(date.getTime())) return ''
  const now = new Date()
  const isToday = date.toDateString() === now.toDateString()
  const timeStr = date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
  if (isToday) {
    return timeStr
  }
  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  if (date.toDateString() === yesterday.toDateString()) {
    return `昨天 ${timeStr}`
  }
  if (date.getFullYear() === now.getFullYear()) {
    return `${date.getMonth() + 1}月${date.getDate()}日 ${timeStr}`
  }
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 ${timeStr}`
}

const loadChat = async () => {
  if (characters.value.length) {
    if (!selectedCharacter.value && characters.value[0]) await loadConversation(characters.value[0])
    return
  }
  try {
    characters.value = await api.characters()
    if (characters.value[0]) await loadConversation(characters.value[0])
  } catch (err) {
    error.value = err instanceof Error ? err.message : '后端尚未启动'
    isLoading.value = false
  }
}

onMounted(async () => {
  window.addEventListener('hashchange', syncRoute)
  if (!showAdmin.value) {
    await Promise.all([loadChat(), loadSystemSettings()])
  }
})

onUnmounted(() => {
  window.removeEventListener('hashchange', syncRoute)
})

watch(showAdmin, async (isAdmin) => {
  if (!isAdmin) {
    await Promise.all([loadChat(), loadSystemSettings()])
  }
})
</script>

<template>
  <AdminWorkspace v-if="showAdmin" @go-chat="openChat" />
  <main v-else class="app-shell">
    <CharacterList
      :characters="characters"
      :selected-id="selectedCharacter?.id"
      @select="loadConversation"
      @open-admin="openAdmin"
    />

    <section class="chat-panel">
      <header v-if="selectedCharacter" class="chat-header">
        <div class="header-character">
          <img :src="selectedCharacter.avatar_url" :alt="selectedCharacter.name" />
          <div>
            <div class="header-name-row">
              <h1>{{ selectedCharacter.name }}</h1>
              <span class="virtual-badge">虚拟角色</span>
            </div>
            <p>{{ selectedScene }} · 私聊中</p>
          </div>
        </div>

        <div class="header-actions">
          <!-- 核心醒目按钮：配置模型 -->
          <button
            class="header-model-btn"
            type="button"
            title="配置大模型接口 (Base URL / API Key) 与语音服务"
            @click="openAdmin('model')"
          >
            <span class="model-status-dot" :class="{ active: llmConfig?.enabled && llmConfig?.has_api_key }" />
            <span class="model-btn-label">配置模型</span>
            <span class="model-name-pill">
              {{ llmConfig?.enabled && llmConfig?.model ? llmConfig.model : (llmConfig?.enabled ? 'LLM' : '未连接') }}
            </span>
          </button>

          <!-- 提示词版本快速切换 -->
          <div v-if="promptConfig?.versions?.length" class="header-prompt-selector" title="切换全局提示词生效版本">
            <span class="prompt-prefix">提示词</span>
            <select
              :value="promptConfig?.active_version"
              :disabled="isSwitchingPrompt || isSending"
              @change="switchPromptVersion(Number(($event.target as HTMLSelectElement).value))"
            >
              <option
                v-for="ver in promptConfig?.versions || []"
                :key="ver.version"
                :value="ver.version"
              >
                v{{ ver.version }} {{ ver.name }}
              </option>
            </select>
          </div>

          <button
            class="header-action"
            type="button"
            :disabled="isLoading || isSending || isResetting"
            @click="openMemoryManager"
          >
            记忆
          </button>
          <button
            class="header-action danger"
            type="button"
            :disabled="isLoading || isSending || isResetting"
            @click="resetConversation"
          >
            {{ isResetting ? '清空中…' : '重新开始' }}
          </button>
          <div class="header-status"><span /> 在线</div>
        </div>
      </header>

      <div v-if="error" class="error-banner">{{ error }}</div>

      <div class="message-scroll">
        <div v-if="isLoading" class="empty-state">
          <div class="loader" />
          <p>正在打开聊天…</p>
        </div>
        <div v-else-if="!messages.length" class="empty-state">
          <div class="empty-orb">✦</div>
          <h2>先打个招呼吧</h2>
          <p>不同的角色，会用不同的方式回应你。</p>
        </div>
        <template v-else>
          <div v-for="(message, index) in messages" :key="message.id" class="message-stream-item">
            <!-- 微信风格的居中时间分隔条（仅在会话开始或时间间隔超过 3 分钟时显示一次） -->
            <div v-if="shouldShowTime(message, messages[index - 1])" class="time-divider">
              <span>{{ formatTimeDivider(message.created_at) }}</span>
            </div>
            <div class="message-entry">
              <MessageBubble :message="message" :character-name="selectedCharacter?.name || ''" />
            </div>
          </div>
        </template>
        <TypingIndicator v-if="isTyping" />
      </div>

      <footer class="chat-footer">
        <Composer
          v-model="draft"
          :disabled="isSending || isLoading || isResetting"
          @send="sendMessage"
          @transfer="openTransferDialog"
        />
      </footer>
    </section>

    <TransferDialog
      v-if="showTransfer"
      :character-name="selectedCharacter?.name"
      :disabled="isLoading || isResetting"
      :submitting="isTransferring"
      @close="showTransfer = false"
      @confirm="sendTransfer"
    />

    <div v-if="showMemories" class="memory-backdrop" @click.self="showMemories = false">
      <section class="memory-panel" role="dialog" aria-modal="true" aria-label="长期记忆管理">
        <header>
          <div>
            <h2>长期记忆</h2>
            <p>角色会在后续聊天中参考这些内容。</p>
          </div>
          <button type="button" aria-label="关闭" @click="showMemories = false">×</button>
        </header>
        <div v-if="isLoadingMemories" class="memory-empty">正在读取…</div>
        <div v-else-if="!memories.length" class="memory-empty">还没有形成长期记忆</div>
        <div v-else class="memory-list">
          <article v-for="memory in memories" :key="memory.id" class="memory-item">
            <div>
              <span>{{ memoryTypeLabel(memory.memory_type) }}</span>
              <small>重要度 {{ memory.importance }}/5</small>
              <p>{{ memory.content }}</p>
            </div>
            <button type="button" @click="removeMemory(memory.id)">删除</button>
          </article>
        </div>
        <footer>
          “重新开始”会同时清空这里的全部记忆和关系进度。
        </footer>
      </section>
    </div>
  </main>
</template>

<style scoped>
/* 顶栏醒目的“配置模型”按钮 */
.header-model-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 6px 12px;
  background: #f1effb;
  border: 1.5px solid #cfc7f7;
  border-radius: 9px;
  color: #5546cd;
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
  transition: all .16s ease;
  box-shadow: 0 1px 3px rgba(85, 70, 205, 0.08);
}
.header-model-btn:hover {
  background: #e7e3fa;
  border-color: #b0a1f2;
  color: #3f31b5;
  box-shadow: 0 3px 8px rgba(85, 70, 205, 0.16);
  transform: translateY(-1px);
}
.header-model-btn:active {
  transform: translateY(0);
}
.model-status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #b5b7c7;
  flex-shrink: 0;
}
.model-status-dot.active {
  background: #34c483;
  box-shadow: 0 0 0 2px #dcf6ea;
}
.model-btn-label {
  letter-spacing: .02em;
}
.model-name-pill {
  padding: 1px 6px;
  background: #fff;
  border: 1px solid #dedaf5;
  border-radius: 5px;
  font-size: 11px;
  font-weight: 500;
  color: #6357d1;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 顶栏提示词版本选择器 */
.header-prompt-selector {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 9px;
  background: #f6f6fa;
  border: 1px solid #e2e3ed;
  border-radius: 8px;
  font-size: 11px;
  color: #6a6c7e;
}
.header-prompt-selector .prompt-prefix {
  color: #8c8ea0;
  font-weight: 500;
}
.header-prompt-selector select {
  background: transparent;
  border: 0;
  outline: 0;
  color: #36394d;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  max-width: 130px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 时间分隔条（微信风格） */
.message-stream-item {
  display: flex;
  flex-direction: column;
}
.time-divider {
  display: flex;
  justify-content: center;
  margin: 18px auto 14px;
}
.time-divider span {
  padding: 2px 10px;
  background: rgba(0, 0, 0, .04);
  color: #9c9eb0;
  border-radius: 10px;
  font-size: 11px;
  letter-spacing: .02em;
}
</style>
