<script setup lang="ts">
import type { Message } from '../types/chat'

defineProps<{
  message: Message
  characterName: string
}>()
</script>

<template>
  <div class="message-row" :class="message.role">
    <div class="message-stack">
      <span v-if="message.role === 'assistant'" class="message-author">{{ characterName }}</span>
      <div v-if="message.message_type === 'text'" class="bubble text-bubble">
        {{ message.content }}
      </div>
      <div v-else-if="message.message_type === 'image'" class="image-bubble">
        <img :src="message.image_url || ''" alt="角色发送的图片" />
      </div>
      <div v-else class="audio-bubble">
        <div class="audio-line">
          <span class="audio-icon">◖</span>
          <audio :src="message.audio_url || ''" controls preload="metadata" />
        </div>
        <details v-if="message.transcript">
          <summary>查看文字</summary>
          <p>{{ message.transcript }}</p>
        </details>
      </div>
    </div>
  </div>
</template>
