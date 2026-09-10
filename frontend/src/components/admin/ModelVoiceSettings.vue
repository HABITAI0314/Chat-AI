<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { adminApi } from '../../api/admin'
import type { LLMConfig, TTSConfig } from '../../types/admin'

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

const statusMessage = ref('')
const errorMessage = ref('')

const loadLlmConfig = async () => {
  try {
    Object.assign(llmConfig, await adminApi.llmConfig())
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载聊天模型配置失败'
  }
}

const saveLlmConfig = async () => {
  if (isSavingLlm.value) return
  isSavingLlm.value = true
  errorMessage.value = ''
  statusMessage.value = ''
  try {
    const saved = await adminApi.saveLlmConfig({
      enabled: llmConfig.enabled,
      base_url: llmConfig.base_url,
      model: llmConfig.model,
      api_key: llmApiKey.value,
    })
    Object.assign(llmConfig, saved)
    llmApiKey.value = ''
    statusMessage.value = '聊天模型配置已成功保存！前台与草稿测试立即生效。'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '保存聊天模型配置失败'
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
  statusMessage.value = ''
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
    statusMessage.value = '语音合成配置已成功保存！下一条语音消息立即生效。'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '保存语音配置失败'
  } finally {
    isSavingTts.value = false
  }
}

onMounted(() => {
  loadLlmConfig()
  loadTtsConfig()
})
</script>

<template>
  <div class="settings-page-container">
    <header class="settings-header">
      <div class="header-left">
        <div>
          <div class="header-title-row">
            <h2>模型与语音合成设置</h2>
            <span class="badge" :class="llmConfig.enabled ? 'active' : 'inactive'">
              {{ llmConfig.enabled ? 'LLM 已启用' : 'LLM 未启用 (本地兜底)' }}
            </span>
            <span class="badge" :class="ttsConfig.enabled ? 'active' : 'inactive'">
              {{ ttsConfig.enabled ? 'TTS 语音已启用' : 'TTS 语音未启用' }}
            </span>
          </div>
          <p>全局共享底层基础模型与语音能力，参数热加载写入本地配置，无需重启 Python 后端服务。</p>
        </div>
      </div>
    </header>

    <div v-if="statusMessage" class="feedback-banner success">{{ statusMessage }}</div>
    <div v-if="errorMessage" class="feedback-banner error">{{ errorMessage }}</div>

    <div class="settings-grid">
      <!-- 1. LLM 聊天大语言模型 -->
      <section class="config-card">
        <div class="card-head">
          <div>
            <span class="card-eyebrow">CHAT MODEL</span>
            <h3>1. 聊天大语言模型 (LLM)</h3>
          </div>
          <label class="toggle-switch">
            <input v-model="llmConfig.enabled" type="checkbox" />
            <span class="toggle-slider" />
          </label>
        </div>
        <p class="card-desc">兼容 OpenAI 标准接口协议（支持 OpenAI、DeepSeek、Qwen、Moonshot 等大模型服务）。未启用时将使用本地内置的确定性 Demo 兜底。</p>

        <div class="fields-form">
          <label>
            API Base URL
            <small class="field-hint">一般填写到 /v1，例如 https://dashscope.aliyuncs.com/compatible-mode/v1 或 https://api.openai.com/v1</small>
            <input v-model="llmConfig.base_url" type="url" placeholder="https://api.openai.com/v1" />
          </label>

          <label>
            模型名称 (Model)
            <small class="field-hint">例如 qwen-plus, qwen3.7-plus, deepseek-chat, gpt-4o-mini</small>
            <input v-model="llmConfig.model" type="text" placeholder="qwen-plus" />
          </label>

          <label>
            API Key (密钥)
            <small class="field-hint">
              {{ llmConfig.has_api_key ? `已配置有效密钥（${llmConfig.api_key_masked}），留空则保持不变` : '尚未配置 API Key' }}
            </small>
            <input
              v-model="llmApiKey"
              type="password"
              autocomplete="new-password"
              placeholder="sk-..."
            />
          </label>
        </div>

        <div class="card-action-bar">
          <span class="storage-note">保存在 data/llm-config.json</span>
          <button
            class="btn-save"
            type="button"
            :disabled="isSavingLlm"
            @click="saveLlmConfig"
          >
            {{ isSavingLlm ? '保存中…' : '保存模型配置' }}
          </button>
        </div>
      </section>

      <!-- 2. TTS 语音合成 -->
      <section class="config-card">
        <div class="card-head">
          <div>
            <span class="card-eyebrow">SPEECH SYNTHESIS</span>
            <h3>2. 语音合成配置 (TTS)</h3>
          </div>
          <label class="toggle-switch">
            <input v-model="ttsConfig.enabled" type="checkbox" />
            <span class="toggle-slider" />
          </label>
        </div>
        <p class="card-desc">支持字节跳动豆包双向流式协议（Seed-TTS）与 OpenAI 兼容音频语音接口。未配置或生成失败时自动降级为文字，不中断会话。</p>

        <div class="fields-form">
          <label>
            供应商协议
            <select v-model="ttsConfig.provider">
              <option value="doubao_bidirection">豆包双向流式 (WebSocket V3 协议)</option>
              <option value="openai_compatible">OpenAI 兼容接口 (POST /audio/speech)</option>
            </select>
          </label>

          <!-- 豆包参数 -->
          <template v-if="ttsConfig.provider === 'doubao_bidirection'">
            <label>
              WebSocket 接口地址
              <input v-model="ttsConfig.websocket_url" type="url" placeholder="wss://openspeech.bytedance.com/api/v3/tts/bidirection" />
            </label>

            <div class="two-cols">
              <label>
                默认音色 (Speaker)
                <input v-model="ttsConfig.speaker" type="text" placeholder="zh_female_shuangkuaisisi_uranus_bigtts" />
              </label>
              <label>
                Resource ID
                <input v-model="ttsConfig.resource_id" type="text" placeholder="seed-tts-2.0" />
              </label>
            </div>

            <div class="two-cols">
              <label>
                App ID
                <input v-model="ttsConfig.app_id" type="text" placeholder="火山引擎 App ID" />
              </label>
              <label>
                Access Token / API Key
                <small class="field-hint">{{ ttsConfig.has_api_key ? `已配置（${ttsConfig.api_key_masked}）` : '未配置' }}</small>
                <input v-model="ttsApiKey" type="password" autocomplete="new-password" placeholder="留空保持不变" />
              </label>
            </div>

            <div class="two-cols">
              <label>
                输出格式
                <select v-model="ttsConfig.output_file_format">
                  <option value="mp3">MP3 格式</option>
                  <option value="wav">WAV 格式</option>
                </select>
              </label>
              <label>
                采样率 (Hz)
                <input v-model.number="ttsConfig.output_sample_rate" type="number" placeholder="24000" />
              </label>
            </div>
          </template>

          <!-- OpenAI 兼容参数 -->
          <template v-else>
            <label>
              Base URL
              <input v-model="ttsConfig.base_url" type="url" placeholder="https://api.openai.com/v1" />
            </label>
            <div class="two-cols">
              <label>
                TTS 模型
                <input v-model="ttsConfig.model" type="text" placeholder="tts-1" />
              </label>
              <label>
                API Key
                <small class="field-hint">{{ ttsConfig.has_api_key ? `已配置（${ttsConfig.api_key_masked}）` : '未配置' }}</small>
                <input v-model="ttsApiKey" type="password" autocomplete="new-password" placeholder="sk-..." />
              </label>
            </div>
          </template>
        </div>

        <div class="card-action-bar">
          <span class="storage-note">合成音频存储在 data/audio/ 目录</span>
          <button
            class="btn-save"
            type="button"
            :disabled="isSavingTts"
            @click="saveTtsConfig"
          >
            {{ isSavingTts ? '保存中…' : '保存语音配置' }}
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.settings-page-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 32px 48px;
}

.settings-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 20px;
  border-bottom: 1px solid #e8e8ee;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}
.settings-icon {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: #eeeaff;
  color: #6a5ce8;
  font-size: 24px;
}
.header-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.header-title-row h2 {
  margin: 0;
  font-size: 18px;
  color: #242736;
}
.badge {
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
}
.badge.active {
  color: #3b9467;
  background: #e6f6ee;
}
.badge.inactive {
  color: #8b8d9c;
  background: #eeeef3;
}
.header-left p {
  margin: 5px 0 0;
  color: #8f91a0;
  font-size: 12px;
}

.feedback-banner {
  margin: 16px 0 0;
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

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
  margin-top: 24px;
}

.config-card {
  display: flex;
  flex-direction: column;
  padding: 24px;
  background: #fff;
  border: 1px solid #e8e8ee;
  border-radius: 14px;
  box-shadow: 0 4px 16px rgba(45, 42, 75, .03);
}

.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}
.card-eyebrow {
  display: block;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: .12em;
  color: #9d9fae;
}
.card-head h3 {
  margin: 3px 0 0;
  font-size: 16px;
  color: #272a38;
}
.card-desc {
  margin: 10px 0 20px;
  color: #8c8e9d;
  font-size: 12px;
  line-height: 1.55;
  min-height: 38px;
}

/* 开关组件 */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
}
.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
  margin: 0;
}
.toggle-slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background-color: #dedee8;
  transition: .2s ease;
  border-radius: 24px;
}
.toggle-slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: .2s ease;
  border-radius: 50%;
  box-shadow: 0 2px 4px rgba(0,0,0,.15);
}
.toggle-switch input:checked + .toggle-slider {
  background-color: #6a5ce8;
}
.toggle-switch input:checked + .toggle-slider:before {
  transform: translateX(20px);
}

.fields-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
}
.fields-form label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: #555767;
}
.field-hint {
  display: block;
  margin-top: 3px;
  color: #a4a5b3;
  font-size: 11px;
  font-weight: 400;
}
.fields-form input, .fields-form select {
  display: block;
  width: 100%;
  margin-top: 6px;
  padding: 9px 12px;
  background: #fafafd;
  border: 1px solid #e1e2eb;
  border-radius: 8px;
  font-size: 12px;
  color: #2b2e3d;
  outline: 0;
  transition: border-color .15s;
}
.fields-form input:focus, .fields-form select:focus {
  border-color: #9d94eb;
  background: #fff;
  box-shadow: 0 0 0 3px #f0efff;
}

.two-cols {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.two-cols label {
  margin-top: 0;
}

.card-action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #f2f2f7;
}
.storage-note {
  color: #a4a6b5;
  font-size: 11px;
}
.btn-save {
  padding: 9px 18px;
  color: #fff;
  background: #7667e8;
  border: 0;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(118, 103, 232, .18);
  transition: background .15s;
}
.btn-save:hover {
  background: #6858e0;
}
.btn-save:disabled {
  opacity: .5;
  cursor: wait;
}

@media (max-width: 960px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 760px) {
  .settings-page-container {
    padding: 16px;
  }
  .settings-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
}
</style>
