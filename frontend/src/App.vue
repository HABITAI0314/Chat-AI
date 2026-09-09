<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import AdminWorkspace from './components/AdminWorkspace.vue'
import CharacterList from './components/CharacterList.vue'
import Composer from './components/Composer.vue'
import MessageBubble from './components/MessageBubble.vue'
import TypingIndicator from './components/TypingIndicator.vue'
import { api } from './api/chat'
import type { Character, ChatMemory, Conversation, Message } from './types/chat'

const route = ref(window.location.hash || '#/chat')
const showAdmin = computed(() => route.value.startsWith('#/admin'))
const syncRoute = () => {
  route.value = window.location.hash || '#/chat'
}
const openAdmin = () => {
  window.location.hash = '#/admin/characters'
}
const openChat = () => {
  window.location.hash = '#/chat'
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
const isResetting = ref(false)
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

const formatTime = (value: string) => {
  const date = new Date(value)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
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
  if (!showAdmin.value) await loadChat()
})

onUnmounted(() => window.removeEventListener('hashchange', syncRoute))

watch(showAdmin, async (isAdmin) => {
  if (!isAdmin) await loadChat()
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
          <div class="day-divider">今天</div>
          <div v-for="message in messages" :key="message.id" class="message-entry">
            <MessageBubble :message="message" :character-name="selectedCharacter?.name || ''" />
            <time>{{ formatTime(message.created_at) }}</time>
          </div>
        </template>
        <TypingIndicator v-if="isTyping" />
      </div>

      <footer class="chat-footer">
        <div class="composer-hint">
          <span class="virtual-mark">V</span>
          <span>虚拟角色不会代表现实中的任何人</span>
        </div>
        <Composer v-model="draft" :disabled="isSending || isLoading" @send="sendMessage" />
      </footer>
    </section>

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
