<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import type { Message } from '../types/chat'
import TransferBubble from './TransferBubble.vue'

const props = defineProps<{
  message: Message
  characterName: string
}>()

const audioElement = ref<HTMLAudioElement | null>(null)
const isPlaying = ref(false)
const showTranscript = ref(false)

// 计算并展示语音时长（优先取传入的 audio_duration_ms，否则默认从元素获取或至少1秒）
const duration = ref(
  props.message.audio_duration_ms
    ? Math.max(1, Math.round(props.message.audio_duration_ms / 1000))
    : 1
)

// 微信语音条动态宽度：基准宽度 85px，每秒增加约 7px，上限 230px
const barWidth = computed(() => {
  const secs = duration.value || 1
  return Math.min(230, Math.max(85, 75 + secs * 7)) + 'px'
})

const onLoadedMetadata = () => {
  if (audioElement.value && audioElement.value.duration && !props.message.audio_duration_ms) {
    duration.value = Math.max(1, Math.round(audioElement.value.duration))
  }
}

const togglePlay = () => {
  if (!audioElement.value) return
  if (isPlaying.value) {
    audioElement.value.pause()
    isPlaying.value = false
  } else {
    // 触发全局广播，暂停其他正在播放的语音条
    window.dispatchEvent(new CustomEvent('app:audio-play', { detail: props.message.id }))
    audioElement.value.play().then(() => {
      isPlaying.value = true
    }).catch(() => {
      isPlaying.value = false
    })
  }
}

const onAudioPause = () => {
  isPlaying.value = false
}

const onAudioEnded = () => {
  isPlaying.value = false
}

const onGlobalAudioPlay = (e: Event) => {
  const customEvent = e as CustomEvent
  if (customEvent.detail !== props.message.id && isPlaying.value) {
    audioElement.value?.pause()
    isPlaying.value = false
  }
}

onMounted(() => {
  window.addEventListener('app:audio-play', onGlobalAudioPlay)
})

onUnmounted(() => {
  window.removeEventListener('app:audio-play', onGlobalAudioPlay)
  if (audioElement.value) {
    audioElement.value.pause()
  }
})
</script>

<template>
  <div class="message-row" :class="message.role">
    <div class="message-stack">
      <span v-if="message.role === 'assistant'" class="message-author">{{ characterName }}</span>
      
      <!-- 普通文本消息 -->
      <div v-if="message.message_type === 'text'" class="bubble text-bubble">
        {{ message.content }}
      </div>

      <!-- 图片消息 -->
      <div v-else-if="message.message_type === 'image'" class="image-bubble">
        <img :src="message.image_url || ''" alt="角色发送的图片" />
      </div>

      <!-- 模拟转账卡片 -->
      <TransferBubble v-else-if="message.message_type === 'transfer'" :message="message" />

      <!-- 微信风格语音条 -->
      <div v-else class="wechat-voice-container">
        <div
          class="wechat-voice-bar"
          :class="{ playing: isPlaying }"
          :style="{ width: barWidth }"
          title="点击播放/暂停语音"
          @click="togglePlay"
        >
          <!-- 微信同款声波波纹图标 -->
          <div class="voice-wave-icon">
            <svg
              class="wechat-wave-svg"
              :class="{ playing: isPlaying }"
              viewBox="0 0 24 24"
              width="18"
              height="18"
              fill="none"
              stroke="currentColor"
              stroke-width="2.2"
              stroke-linecap="round"
            >
              <path class="wave-arc wave-1" d="M6 9.5 A 3.5 3.5 0 0 1 6 14.5" />
              <path class="wave-arc wave-2" d="M10.5 7 A 7 7 0 0 1 10.5 17" />
              <path class="wave-arc wave-3" d="M15 4.5 A 10.5 10.5 0 0 1 15 19.5" />
            </svg>
          </div>

          <span class="voice-duration">{{ duration }}"</span>

          <audio
            ref="audioElement"
            :src="message.audio_url || ''"
            preload="metadata"
            @loadedmetadata="onLoadedMetadata"
            @pause="onAudioPause"
            @ended="onAudioEnded"
          />
        </div>

        <!-- 微信同款“转文字”展开卡片 -->
        <div v-if="message.transcript || message.content" class="transcript-section">
          <div v-if="showTranscript" class="transcript-card">
            <div class="transcript-meta">
              <span class="transcript-badge">转文字</span>
              <button class="btn-transcript-toggle" type="button" @click="showTranscript = false">
                隐藏
              </button>
            </div>
            <p class="transcript-content">{{ message.transcript || message.content }}</p>
          </div>
          <button
            v-else
            type="button"
            class="btn-transcript-text"
            @click="showTranscript = true"
          >
            转文字
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.wechat-voice-container {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}

/* 微信语音胶囊条 */
.wechat-voice-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 40px;
  padding: 0 14px;
  background: #ffffff;
  border: 1px solid #e5e5ec;
  border-radius: 4px 14px 14px 14px;
  box-shadow: 0 2px 8px rgba(35, 30, 65, .04);
  cursor: pointer;
  user-select: none;
  transition: background .15s, transform .1s, border-color .15s;
}
.wechat-voice-bar:hover {
  background: #fbfbfe;
  border-color: #dcdce8;
}
.wechat-voice-bar:active {
  background: #f0f0f5;
  transform: scale(.98);
}
.wechat-voice-bar.playing {
  border-color: #cac5f6;
  background: #f9f8ff;
}

/* 声波动画 */
.voice-wave-icon {
  display: flex;
  align-items: center;
  color: #555768;
}
.wechat-voice-bar.playing .voice-wave-icon {
  color: #6a5ce8;
}

.wechat-wave-svg .wave-arc {
  opacity: .85;
}

@keyframes wechatVoiceWave {
  0% { opacity: .2; }
  33% { opacity: 1; }
  66% { opacity: 1; }
  100% { opacity: .2; }
}

.wechat-wave-svg.playing .wave-1 {
  animation: wechatVoiceWave 1.1s infinite 0s;
}
.wechat-wave-svg.playing .wave-2 {
  animation: wechatVoiceWave 1.1s infinite .25s;
}
.wechat-wave-svg.playing .wave-3 {
  animation: wechatVoiceWave 1.1s infinite .5s;
}

.voice-duration {
  font-size: 13px;
  font-weight: 500;
  color: #6b6d7d;
  letter-spacing: .05em;
}
.wechat-voice-bar.playing .voice-duration {
  color: #6a5ce8;
}

/* 微信转文字卡片 */
.transcript-section {
  max-width: min(440px, 85vw);
}

.btn-transcript-text {
  padding: 2px 6px;
  color: #9c9eb0;
  background: transparent;
  border: 0;
  font-size: 11px;
  cursor: pointer;
  transition: color .15s;
}
.btn-transcript-text:hover {
  color: #6a5ce8;
}

.transcript-card {
  padding: 10px 14px;
  background: #ffffff;
  border: 1px solid #e7e7ee;
  border-radius: 4px 12px 12px 12px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, .03);
  animation: cardFade .15s ease-out;
}
@keyframes cardFade {
  from { opacity: 0; transform: translateY(-3px); }
  to { opacity: 1; transform: translateY(0); }
}

.transcript-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid #f2f2f7;
}
.transcript-badge {
  font-size: 10px;
  color: #9ea0af;
}
.btn-transcript-toggle {
  padding: 0;
  color: #9ea0af;
  background: transparent;
  border: 0;
  font-size: 10px;
  cursor: pointer;
}
.btn-transcript-toggle:hover {
  color: #6a5ce8;
}

.transcript-content {
  margin: 0;
  color: #383a48;
  font-size: 13px;
  line-height: 1.55;
  white-space: pre-wrap;
}
</style>
