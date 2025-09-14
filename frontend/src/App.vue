<script setup lang="ts">
import { ref, computed } from 'vue'
import PlanckSim from './components/PlanckSim.vue'
import EnergyChart from './components/EnergyChart.vue'
import EventStream from './components/EventStream.vue'

const query = ref('')
const loading = ref(false)
const error = ref<string | null>(null)
const scene = ref<any | null>(null)
const thinking = ref(false)
const isDark = ref(false)
const assistantMsg = ref<string | null>(null)

function delay(ms: number) { return new Promise<void>(resolve => setTimeout(resolve, ms)) }

async function runQuery() {
  error.value = null
  loading.value = true
  thinking.value = true
  assistantMsg.value = null

  let nextScene: any | null = null
  let reqError: string | null = null

  const minHold = delay(2000) // 至少展示 2 秒思考动画

  const req = (async () => {
    try {
      const res = await fetch('/api/assist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query.value })
      })
      if (!res.ok) throw new Error('HTTP ' + res.status)
      const data = await res.json()
      console.log('[assist] response JSON:', data)
      // 提取模型回复文本（兼容不同字段名）
      assistantMsg.value = data?.send_message || data?.message || null
      // 兼容旧的 { planck_scene } 和新的 { compile_scene: { planck_scene } }
      nextScene = data?.planck_scene || data?.compile_scene?.planck_scene || null
      if (!nextScene) reqError = 'No planck_scene in response'
    } catch (e: any) {
      console.error('[assist] request error:', e)
      reqError = e?.message || 'Network error'
    }
  })()

  await Promise.all([minHold, req])

  if (reqError) {
    error.value = reqError
    scene.value = null
  } else {
    scene.value = nextScene
  }

  thinking.value = false
  loading.value = false
}

function applyTheme(theme: 'light' | 'dark') {
  isDark.value = theme === 'dark'
  document.documentElement.setAttribute('data-theme', theme)
}

function toggleTheme() {
  const next = isDark.value ? 'light' : 'dark'
  localStorage.setItem('theme', next)
  applyTheme(next)
}

if (typeof window !== 'undefined') {
  const saved = (localStorage.getItem('theme') as 'light' | 'dark' | null)
  if (saved === 'light' || saved === 'dark') {
    applyTheme(saved)
  } else {
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
    applyTheme(prefersDark ? 'dark' : 'light')
  }
}

// 基于当前场景计算一些可视化统计
const stats = computed(() => {
  const s = scene.value
  if (!s) return null
  const objs = Array.isArray(s.objects) ? s.objects : []
  const total = objs.length
  const dynamicCount = objs.filter((o: any) => o.type === 'dynamic').length
  const staticCount = objs.filter((o: any) => o.type === 'static').length
  const circles = objs.filter((o: any) => o.shape === 'circle').length
  const boxes = objs.filter((o: any) => o.shape === 'box').length
  const gravity = s.world?.gravity ?? { x: 0, y: 0 }
  const speeds: number[] = objs
    .map((o: any) => o.initial_velocity || o.linearVelocity)
    .filter(Boolean)
    .map((v: any) => Math.sqrt((v.x || 0) ** 2 + (v.y || 0) ** 2))
  const avgSpeed = speeds.length ? (speeds.reduce((a, b) => a + b, 0) / speeds.length) : 0
  return { total, dynamicCount, staticCount, circles, boxes, gravity, avgSpeed }
})
</script>

<template>
  <main class="layout">
    <div v-if="thinking" class="thinking-overlay">
      <div class="thinking-card">
        <div class="spinner"></div>
        <div class="msg">Thinking…</div>
      </div>
    </div>
    <section class="left-pane">
      <div class="toolbar">
        <input v-model="query" class="prompt" type="text" placeholder="Enter your request..." />
        <button class="run" :disabled="loading" @click="runQuery">{{ loading ? 'Running...' : 'Run' }}</button>
        <button class="theme" @click="toggleTheme">{{ isDark ? '☀️ Light' : '🌙 Dark' }}</button>
      </div>

      <p v-if="error" class="err">{{ error }}</p>

      <section v-if="assistantMsg" class="assistant">
        <div class="assistant-title">Assistant Reply</div>
        <div class="assistant-body">{{ assistantMsg }}</div>
      </section>

      <section class="viz">
        <h2>Visualization</h2>
        <div class="charts">
          <EnergyChart />
          <EventStream />
        </div>
        <div v-if="stats" class="stats">
          <div class="card"><div class="label">Objects</div><div class="value">{{ stats.total }}</div></div>
          <div class="card"><div class="label">Dynamic Bodies</div><div class="value">{{ stats.dynamicCount }}</div></div>
          <div class="card"><div class="label">Static Bodies</div><div class="value">{{ stats.staticCount }}</div></div>
          <div class="card"><div class="label">Circles</div><div class="value">{{ stats.circles }}</div></div>
          <div class="card"><div class="label">Boxes</div><div class="value">{{ stats.boxes }}</div></div>
          <div class="card"><div class="label">Average Speed</div><div class="value">{{ stats.avgSpeed.toFixed(2) }}</div></div>
          <div class="card span-2"><div class="label">Gravity</div><div class="value">({{ stats.gravity.x.toFixed(2) }}, {{ stats.gravity.y.toFixed(2) }})</div></div>
        </div>
      </section>
    </section>

    <section class="right-sim">
      <PlanckSim :sceneData="scene || undefined" />
    </section>
  </main>
</template>

<style scoped>
.layout { display: grid; gap: 16px; grid-template-columns: minmax(420px, 560px) 800px; align-items: start; justify-content: center; padding: 20px 24px 16px; }
.thinking-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.25); display: grid; place-items: center; z-index: 999; }
.thinking-card { background: var(--color-background); color: var(--color-heading); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 16px 20px; box-shadow: 0 8px 30px rgba(0,0,0,0.12); display: flex; gap: 12px; align-items: center; }
.thinking-card .msg { font-weight: 600; }
.thinking-card .sub { font-size: 12px; color: var(--text-secondary); }
.spinner { width: 18px; height: 18px; border: 2px solid var(--color-border); border-top-color: var(--accent); border-radius: 50%; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.left-pane { display: flex; flex-direction: column; gap: 12px; }
.toolbar { display: flex; gap: 8px; }
.prompt { width: 100%; padding: 8px 10px; border: 1px solid var(--color-border); background: var(--surface-1); color: var(--text-primary); border-radius: var(--radius-sm); font-size: 14px; }
.prompt::placeholder { color: var(--text-secondary); }
.run { padding: 8px 12px; border-radius: var(--radius-sm); border: 1px solid var(--accent); background: var(--accent); color: #fff; cursor: pointer; }
.run:disabled { opacity: 0.6; cursor: not-allowed; }
.theme { padding: 8px 12px; border-radius: var(--radius-sm); border: 1px solid var(--color-border); background: var(--surface-1); color: var(--color-heading); cursor: pointer; }
.err { color: var(--error); margin: 0 0 12px; }

.viz { background: var(--surface-2); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 12px; }
.viz h2 { font-size: 16px; margin-bottom: 10px; }
.charts { display: grid; grid-template-columns: 1fr; gap: 10px; margin-bottom: 10px; }
.stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.card { background: var(--surface-1); border: 1px solid var(--color-border); border-radius: var(--radius-sm); padding: 10px; }
.card .label { color: var(--text-secondary); font-size: 12px; }
.card .value { font-size: 20px; font-weight: 600; margin-top: 4px; }
.card.span-2 { grid-column: span 2; }

.right-sim { position: sticky; top: 20px; margin-right: 0; }

@media (max-width: 1100px) {
  .layout { grid-template-columns: 1fr; }
  .right-sim { position: static; }
}

.assistant { background: var(--surface-1); border: 1px solid var(--color-border); border-radius: var(--radius-sm); padding: 10px; white-space: pre-wrap; }
.assistant-title { font-size: 13px; margin-bottom: 6px; color: var(--color-heading); font-weight: 600; }
.assistant-body { color: var(--text-secondary); line-height: 1.5; }
</style>
