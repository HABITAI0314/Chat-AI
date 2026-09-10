<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { adminApi } from '../../api/admin'
import type { PromptBundle, PromptConfig } from '../../types/admin'

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
const promptSubTab = ref<'behavior' | 'reply' | 'memory'>('behavior')
const statusMessage = ref('')
const errorMessage = ref('')

const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T

const applyPromptConfig = (config: PromptConfig) => {
  promptConfig.value = config
  selectedPromptVersion.value = config.selected_version
  Object.assign(promptDraft, config.prompts)
}

const loadPromptConfig = async (version?: number) => {
  try {
    applyPromptConfig(await adminApi.promptConfig(version))
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载提示词配置失败'
  }
}

const selectPromptVersion = async () => {
  if (selectedPromptVersion.value) {
    errorMessage.value = ''
    statusMessage.value = ''
    await loadPromptConfig(selectedPromptVersion.value)
  }
}

const createPromptVersion = async () => {
  if (isSavingPrompt.value) return
  isSavingPrompt.value = true
  errorMessage.value = ''
  statusMessage.value = ''
  try {
    const name = promptVersionName.value.trim() || '提示词优化版'
    applyPromptConfig(await adminApi.createPromptVersion(name, clone(promptDraft)))
    promptVersionName.value = ''
    statusMessage.value = '新提示词版本已成功创建并自动切换为当前生效版本！'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '保存提示词版本失败'
  } finally {
    isSavingPrompt.value = false
  }
}

const activatePromptVersion = async () => {
  if (!selectedPromptVersion.value || isSavingPrompt.value) return
  isSavingPrompt.value = true
  errorMessage.value = ''
  statusMessage.value = ''
  try {
    applyPromptConfig(await adminApi.activatePromptVersion(selectedPromptVersion.value))
    statusMessage.value = `已成功切换为 v${selectedPromptVersion.value}，前台及后台测试下一条消息立即生效。`
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '切换提示词版本失败'
  } finally {
    isSavingPrompt.value = false
  }
}

const resetPromptDraft = () => {
  if (promptConfig.value) {
    Object.assign(promptDraft, promptConfig.value.prompts)
    statusMessage.value = '已重置为当前选中版本的初始提示词内容。'
  }
}

const isViewingActive = computed(() => {
  return selectedPromptVersion.value === promptConfig.value?.active_version
})

const copyVariable = (tag: string) => {
  navigator.clipboard?.writeText(tag)
  statusMessage.value = `已复制变量标签 ${tag} 到剪贴板，可粘贴到提示词模板中。`
}

onMounted(() => {
  loadPromptConfig()
})
</script>

<template>
  <div class="prompt-lab-container">
    <header class="prompt-lab-header">
      <div class="lab-title">
        <div>
          <div class="title-line">
            <h2>提示词编排工作区</h2>
            <span class="version-tag active">当前生效：v{{ promptConfig?.active_version || 1 }}</span>
            <span v-if="!isViewingActive" class="version-tag viewing">当前查看：v{{ selectedPromptVersion }}</span>
          </div>
          <p>编排与调试 LangGraph 三阶段提示词链（行为决策、回复生成、记忆提取），支持版本热切换与即时回退。</p>
        </div>
      </div>

      <div class="lab-header-actions">
        <button class="btn-reset" type="button" @click="resetPromptDraft">重置为本版初值</button>
        <button
          v-if="!isViewingActive"
          class="btn-activate"
          type="button"
          :disabled="isSavingPrompt"
          @click="activatePromptVersion"
        >
          {{ isSavingPrompt ? '切换中…' : '设为当前生效版本' }}
        </button>
      </div>
    </header>

    <div v-if="statusMessage" class="feedback-banner success">{{ statusMessage }}</div>
    <div v-if="errorMessage" class="feedback-banner error">{{ errorMessage }}</div>

    <!-- 版本控制条 -->
    <div class="version-control-bar">
      <div class="version-field-group">
        <label>选择版本查看与调整</label>
        <div class="input-row">
          <select v-model.number="selectedPromptVersion" @change="selectPromptVersion">
            <option
              v-for="ver in promptConfig?.versions || []"
              :key="ver.version"
              :value="ver.version"
            >
              v{{ ver.version }}: {{ ver.name }} {{ ver.version === promptConfig?.active_version ? '（当前生效中）' : '' }}
            </option>
          </select>
          <button
            v-if="!isViewingActive"
            class="btn-inline-activate"
            type="button"
            :disabled="isSavingPrompt"
            @click="activatePromptVersion"
          >
            切换生效
          </button>
          <span v-else class="active-badge">✓ 生效中</span>
        </div>
      </div>

      <div class="version-field-group create-group">
        <label>基于当前修改另存为新版本</label>
        <div class="input-row">
          <input
            v-model="promptVersionName"
            type="text"
            placeholder="新版本名称（例如：更口语化回复版）"
          />
          <button
            class="btn-save-new"
            type="button"
            :disabled="isSavingPrompt"
            @click="createPromptVersion"
          >
            {{ isSavingPrompt ? '保存中…' : '另存并立即生效' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 模块切换选项卡 -->
    <div class="module-nav-tabs">
      <button
        type="button"
        :class="{ active: promptSubTab === 'behavior' }"
        @click="promptSubTab = 'behavior'"
      >
        <span class="tab-num">1</span>
        <span class="tab-txt">行为决策提示词 (Behavior Decision)</span>
      </button>
      <button
        type="button"
        :class="{ active: promptSubTab === 'reply' }"
        @click="promptSubTab = 'reply'"
      >
        <span class="tab-num">2</span>
        <span class="tab-txt">回复生成提示词 (Reply Generation)</span>
      </button>
      <button
        type="button"
        :class="{ active: promptSubTab === 'memory' }"
        @click="promptSubTab = 'memory'"
      >
        <span class="tab-num">3</span>
        <span class="tab-txt">记忆提取提示词 (Memory Extraction)</span>
      </button>
    </div>

    <!-- 模版编辑主卡片 -->
    <div class="prompt-workspace-card">
      <!-- 1. 行为决策 -->
      <div v-show="promptSubTab === 'behavior'" class="tab-content">
        <div class="module-desc">
          <h4>第一阶段：行为决策 (Behavior Decision)</h4>
          <p>控制 LLM 解析用户本轮意图，计算关系增减量（熟悉度/信任/好感/烦躁），推导情绪变化及照片/语音发送决断。</p>
        </div>

        <div class="variable-banner">
          <span class="banner-title">点击复制可用变量：</span>
          <div class="tags-wrap">
            <span class="v-pill" title="点击复制" @click="copyVariable('[[character_name]]')">[[character_name]]</span>
            <span class="v-pill" title="点击复制" @click="copyVariable('[[profile_json]]')">[[profile_json]]</span>
            <span class="v-pill" title="点击复制" @click="copyVariable('[[relationship_json]]')">[[relationship_json]]</span>
            <span class="v-pill" title="点击复制" @click="copyVariable('[[emotion_json]]')">[[emotion_json]]</span>
            <span class="v-pill" title="点击复制" @click="copyVariable('[[scene_json]]')">[[scene_json]]</span>
            <span class="v-pill" title="点击复制" @click="copyVariable('[[conversation_text]]')">[[conversation_text]]</span>
            <span class="v-pill" title="点击复制" @click="copyVariable('[[memories_json]]')">[[memories_json]]</span>
            <span class="v-pill" title="点击复制" @click="copyVariable('[[user_message]]')">[[user_message]]</span>
          </div>
        </div>

        <div class="editor-pair">
          <label>
            <span class="field-title">系统提示词 (System Prompt)</span>
            <small class="field-tip">定义分析规则、输出 JSON Schema 与安全边界</small>
            <textarea v-model="promptDraft.behavior_system" rows="8" spellcheck="false" />
          </label>

          <label>
            <span class="field-title">用户提示词模板 (User Prompt Template)</span>
            <small class="field-tip">动态注入当前会话上下文变量</small>
            <textarea v-model="promptDraft.behavior_user" rows="8" spellcheck="false" />
          </label>
        </div>
      </div>

      <!-- 2. 回复生成 -->
      <div v-show="promptSubTab === 'reply'" class="tab-content">
        <div class="module-desc">
          <h4>第二阶段：回复生成 (Reply Generation)</h4>
          <p>角色真正发出的私聊短消息内容。遵循口语化、断句和人设语气规则，执行第一阶段输出的发图/语音动作。</p>
        </div>

        <div class="variable-banner">
          <span class="banner-title">点击复制可用变量：</span>
          <div class="tags-wrap">
            <span class="v-pill" title="点击复制" @click="copyVariable('[[character_name]]')">[[character_name]]</span>
            <span class="v-pill" title="点击复制" @click="copyVariable('[[profile_json]]')">[[profile_json]]</span>
            <span class="v-pill" title="点击复制" @click="copyVariable('[[relationship_json]]')">[[relationship_json]]</span>
            <span class="v-pill" title="点击复制" @click="copyVariable('[[emotion_json]]')">[[emotion_json]]</span>
            <span class="v-pill" title="点击复制" @click="copyVariable('[[scene_json]]')">[[scene_json]]</span>
            <span class="v-pill" title="点击复制" @click="copyVariable('[[decision_json]]')">[[decision_json]]</span>
            <span class="v-pill" title="点击复制" @click="copyVariable('[[conversation_text]]')">[[conversation_text]]</span>
            <span class="v-pill" title="点击复制" @click="copyVariable('[[memories_json]]')">[[memories_json]]</span>
            <span class="v-pill" title="点击复制" @click="copyVariable('[[user_message]]')">[[user_message]]</span>
          </div>
        </div>

        <div class="editor-pair">
          <label>
            <span class="field-title">系统提示词 (System Prompt)</span>
            <small class="field-tip">核心回复指导规范、多气泡切分策略与人设执行准则</small>
            <textarea v-model="promptDraft.reply_system" rows="12" spellcheck="false" />
          </label>

          <label>
            <span class="field-title">用户提示词模板 (User Prompt Template)</span>
            <small class="field-tip">组织行为决策结果与本轮用户对话</small>
            <textarea v-model="promptDraft.reply_user" rows="8" spellcheck="false" />
          </label>
        </div>
      </div>

      <!-- 3. 记忆提取 -->
      <div v-show="promptSubTab === 'memory'" class="tab-content">
        <div class="module-desc">
          <h4>第三阶段：长期记忆提取 (Memory Extraction)</h4>
          <p>从用户发言和对话历史中抽离出具有长期价值的偏好（preference）、经历（experience）或边界事实（boundary）。</p>
        </div>

        <div class="variable-banner">
          <span class="banner-title">点击复制可用变量：</span>
          <div class="tags-wrap">
            <span class="v-pill" title="点击复制" @click="copyVariable('[[user_message]]')">[[user_message]]</span>
            <span class="v-pill" title="点击复制" @click="copyVariable('[[conversation_text]]')">[[conversation_text]]</span>
          </div>
        </div>

        <div class="editor-pair">
          <label>
            <span class="field-title">系统提示词 (System Prompt)</span>
            <small class="field-tip">提取过滤准则与 JSON 格式约定</small>
            <textarea v-model="promptDraft.memory_system" rows="8" spellcheck="false" />
          </label>

          <label>
            <span class="field-title">用户提示词模板 (User Prompt Template)</span>
            <small class="field-tip">注入本轮用户消息与上下文</small>
            <textarea v-model="promptDraft.memory_user" rows="6" spellcheck="false" />
          </label>
        </div>
      </div>

      <!-- 底部保存浮栏 -->
      <div class="card-footer-actions">
        <span class="footer-hint">提示词支持多版本热回退。若要保留调整，请使用“另存为新版本”或激活对应版本。</span>
        <div class="btn-group">
          <button
            v-if="!isViewingActive"
            class="btn-activate-secondary"
            type="button"
            :disabled="isSavingPrompt"
            @click="activatePromptVersion"
          >
            {{ isSavingPrompt ? '处理中…' : '设为当前生效版本' }}
          </button>
          <button
            class="btn-save-primary"
            type="button"
            :disabled="isSavingPrompt"
            @click="createPromptVersion"
          >
            {{ isSavingPrompt ? '保存中…' : '保存修改为新版本' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.prompt-lab-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 32px 48px;
}

.prompt-lab-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 20px;
  border-bottom: 1px solid #e8e8ee;
}
.lab-title {
  display: flex;
  align-items: center;
  gap: 14px;
}
.lab-icon {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: #eeeaff;
  color: #6a5ce8;
  font-size: 22px;
}
.title-line {
  display: flex;
  align-items: center;
  gap: 10px;
}
.title-line h2 {
  margin: 0;
  font-size: 18px;
  color: #242736;
}
.version-tag {
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
}
.version-tag.active {
  color: #3b9467;
  background: #e6f6ee;
}
.version-tag.viewing {
  color: #b07c42;
  background: #fff4e2;
}
.lab-title p {
  margin: 5px 0 0;
  color: #8f91a0;
  font-size: 12px;
}
.lab-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.btn-reset {
  padding: 8px 14px;
  color: #7b7d8d;
  background: #fff;
  border: 1px solid #dcdee8;
  border-radius: 8px;
  font-size: 12px;
  cursor: pointer;
}
.btn-reset:hover {
  background: #f7f7fa;
  color: #4a4c59;
}
.btn-activate {
  padding: 8px 16px;
  color: #655bd0;
  background: #eeeaff;
  border: 0;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
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

/* 版本控制条 */
.version-control-bar {
  display: flex;
  gap: 20px;
  margin-top: 18px;
  padding: 16px 20px;
  background: #fff;
  border: 1px solid #e7e7ef;
  border-radius: 12px;
}
.version-field-group {
  flex: 1;
}
.version-field-group label {
  display: block;
  margin-bottom: 7px;
  font-size: 11px;
  font-weight: 600;
  color: #636577;
}
.input-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.input-row select, .input-row input {
  flex: 1;
  padding: 8px 10px;
  background: #fafafd;
  border: 1px solid #e1e2ec;
  border-radius: 8px;
  font-size: 12px;
  color: #2d3040;
  outline: 0;
}
.input-row select:focus, .input-row input:focus {
  border-color: #9d94eb;
}
.btn-inline-activate {
  padding: 8px 12px;
  color: #655bd0;
  background: #eeeaff;
  border: 0;
  border-radius: 7px;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
  cursor: pointer;
}
.active-badge {
  padding: 7px 10px;
  color: #3b8a67;
  background: #e7f7ee;
  border-radius: 7px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}
.btn-save-new {
  padding: 8px 14px;
  color: #fff;
  background: #7667e8;
  border: 0;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  cursor: pointer;
  box-shadow: 0 4px 10px rgba(118, 103, 232, .18);
}
.btn-save-new:hover {
  background: #6858e0;
}

/* 模块切换 */
.module-nav-tabs {
  display: flex;
  gap: 8px;
  margin-top: 22px;
}
.module-nav-tabs button {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #eaeaf1;
  border: 0;
  border-radius: 10px;
  color: #7b7e8e;
  cursor: pointer;
  transition: all .15s;
}
.module-nav-tabs button.active {
  background: #fff;
  color: #655bd0;
  box-shadow: 0 4px 12px rgba(50, 48, 80, .07);
}
.tab-num {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  background: rgba(0,0,0,.06);
  border-radius: 50%;
  font-size: 11px;
  font-weight: 700;
}
.module-nav-tabs button.active .tab-num {
  background: #eeeaff;
  color: #655bd0;
}
.tab-txt {
  font-size: 12px;
  font-weight: 600;
}

/* 编辑区主卡片 */
.prompt-workspace-card {
  margin-top: 14px;
  padding: 24px;
  background: #fff;
  border: 1px solid #e8e8ee;
  border-radius: 12px;
}
.module-desc h4 {
  margin: 0;
  font-size: 15px;
  color: #2b2e3d;
}
.module-desc p {
  margin: 5px 0 16px;
  color: #8c8f9e;
  font-size: 12px;
  line-height: 1.5;
}

.variable-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: #f9f9fd;
  border: 1px dashed #dcdcf0;
  border-radius: 8px;
  margin-bottom: 20px;
}
.banner-title {
  font-size: 11px;
  font-weight: 600;
  color: #7d8091;
  white-space: nowrap;
}
.tags-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.v-pill {
  padding: 3px 8px;
  background: #eeeaff;
  color: #5c4fd6;
  border-radius: 5px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 11px;
  cursor: pointer;
  transition: all .15s;
}
.v-pill:hover {
  background: #655bd0;
  color: #fff;
}

.editor-pair {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.editor-pair label {
  display: block;
}
.field-title {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #333647;
}
.field-tip {
  display: block;
  margin: 3px 0 8px;
  color: #a4a5b3;
  font-size: 11px;
}
.editor-pair textarea {
  display: block;
  width: 100%;
  padding: 12px 14px;
  background: #fbfbfd;
  border: 1px solid #e1e2ec;
  border-radius: 9px;
  color: #282b3a;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
  outline: 0;
  resize: vertical;
  transition: border-color .15s;
}
.editor-pair textarea:focus {
  border-color: #9d94eb;
  background: #fff;
  box-shadow: 0 0 0 3px #f0efff;
}

.card-footer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 28px;
  padding-top: 18px;
  border-top: 1px solid #f0f0f5;
}
.footer-hint {
  color: #9da0ae;
  font-size: 11px;
}
.btn-group {
  display: flex;
  gap: 10px;
}
.btn-activate-secondary {
  padding: 9px 16px;
  color: #655bd0;
  background: #f0efff;
  border: 0;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
}
.btn-save-primary {
  padding: 9px 18px;
  color: #fff;
  background: #7667e8;
  border: 0;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(118, 103, 232, .18);
}
.btn-save-primary:hover {
  background: #6858e0;
}
.btn-save-primary:disabled, .btn-activate-secondary:disabled {
  opacity: .5;
  cursor: wait;
}

@media (max-width: 760px) {
  .prompt-lab-container {
    padding: 16px;
  }
  .prompt-lab-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  .version-control-bar {
    flex-direction: column;
  }
  .module-nav-tabs {
    flex-direction: column;
  }
  .card-footer-actions {
    flex-direction: column;
    gap: 12px;
  }
}
</style>
