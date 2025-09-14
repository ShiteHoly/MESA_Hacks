<script setup lang="ts">
import { onMounted, onBeforeUnmount, watch } from 'vue'
import { energySeries } from '@/telemetry'

let chart: any = null
let el: HTMLDivElement | null = null

function init() {
  const ec = (window as any).echarts
  if (!ec || !el) return
  chart = ec.init(el)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['K', 'U', 'E'], top: 0 },
    grid: { left: 40, right: 12, top: 30, bottom: 25 },
    xAxis: { type: 'category', boundaryGap: false, data: [] },
    yAxis: { type: 'value', name: 'Energy', scale: true },
    series: [
      { name: 'K', type: 'line', areaStyle: {}, stack: 'energy', data: [] },
      { name: 'U', type: 'line', areaStyle: {}, stack: 'energy', data: [] },
      { name: 'E', type: 'line', data: [], symbol: 'none', lineStyle: { width: 2 } },
    ],
  })
}

function update() {
  if (!chart) return
  const data = energySeries.value
  const t = data.map((d) => d.t.toFixed(2))
  const K = data.map((d) => d.K)
  const U = data.map((d) => d.U)
  const E = data.map((d) => d.E)
  chart.setOption({
    xAxis: { data: t },
    series: [{ data: K }, { data: U }, { data: E }],
  })
}

onMounted(() => {
  el = document.getElementById('energy-chart') as HTMLDivElement
  init()
  update()
})

onBeforeUnmount(() => {
  if (chart) chart.dispose()
})

watch(energySeries, () => update(), { deep: true })
</script>

<template>
  <div class="panel">
    <div class="panel-title">能量堆叠图 (K / U / E)</div>
    <div id="energy-chart" class="chart"></div>
  </div>
  
</template>

<style scoped>
.panel { background: var(--color-background); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 8px; }
.panel-title { font-size: 14px; margin-bottom: 6px; color: var(--color-heading); }
.chart { width: 100%; height: 240px; }
</style>

