<script setup lang="ts">
import { ref } from 'vue'
import PlanckSim from './components/PlanckSim.vue'

const query = ref('')
const loading = ref(false)
const error = ref<string | null>(null)
const scene = ref<any | null>(null)

async function runQuery() {
  error.value = null
  loading.value = true
  try {
    console.log(query.value);
    const res = await fetch('/api/assist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query.value })
      
    })
    const data = await res.json()
    scene.value = data.planck_scene || null
    if (!scene.value) error.value = 'No planck_scene in response'
  } catch (e: any) {
    error.value = e?.message || 'Network error'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="page">
    <section class="toolbar">
      <input v-model="query" class="prompt" type="text" placeholder="输入你的请求..." />
      <button class="run" :disabled="loading" @click="runQuery">{{ loading ? '运行中...' : '运行' }}</button>
    </section>

    <p v-if="error" class="err">{{ error }}</p>

    <PlanckSim :sceneData="scene || undefined" />
  </main>
</template>

<style scoped>
.page { display: grid; place-items: center; padding: 24px; }
.toolbar { display: flex; gap: 8px; margin-bottom: 12px; }
.prompt { width: 520px; padding: 8px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
.run { padding: 8px 12px; border-radius: 6px; border: 1px solid #2d6cdf; background: #2d6cdf; color: white; cursor: pointer; }
.run:disabled { opacity: 0.6; cursor: not-allowed; }
.err { color: #c00; margin: 0 0 12px; }
</style>


