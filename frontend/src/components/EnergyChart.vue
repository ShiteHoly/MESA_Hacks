<script setup lang="ts">
import { onMounted, onBeforeUnmount, watch } from 'vue'
import { energySeries } from '@/telemetry'

let chart: any = null
let el: HTMLDivElement | null = null
let mo: MutationObserver | null = null

function cssVar(name: string, fallback = ''): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name)
  return v?.trim() || fallback
}

function init() {
  const ec = (window as any).echarts
  if (!ec || !el) return
  chart = ec.init(el)
  chart.setOption({
    backgroundColor: 'transparent',
    textStyle: { color: cssVar('--chart-text', '#333') },
    tooltip: { trigger: 'axis' },
    legend: { data: ['K', 'U', 'E'], top: 0, textStyle: { color: cssVar('--chart-text', '#333') } },
    grid: { left: 40, right: 12, top: 30, bottom: 25 },
    xAxis: {
      type: 'category', boundaryGap: false, data: [],
      axisLabel: { color: cssVar('--chart-text', '#333') },
      axisLine: { lineStyle: { color: cssVar('--chart-axis', '#aaa') } },
      splitLine: { show: true, lineStyle: { color: cssVar('--chart-grid', '#eee') } },
    },
    yAxis: {
      type: 'value', name: 'Energy', scale: true,
      axisLabel: { color: cssVar('--chart-text', '#333') },
      axisLine: { lineStyle: { color: cssVar('--chart-axis', '#aaa') } },
      splitLine: { show: true, lineStyle: { color: cssVar('--chart-grid', '#eee') } },
    },
    color: [cssVar('--accent', '#2d6cdf'), cssVar('--accent-2', '#34c38f'), cssVar('--accent-3', '#ff7f50')],
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
  // observe theme changes
  mo = new MutationObserver((mutations) => {
    for (const m of mutations) {
      if (m.type === 'attributes' && m.attributeName === 'data-theme') {
        if (chart) {
          chart.setOption({
            textStyle: { color: cssVar('--chart-text', '#333') },
            legend: { textStyle: { color: cssVar('--chart-text', '#333') } },
            xAxis: {
              axisLabel: { color: cssVar('--chart-text', '#333') },
              axisLine: { lineStyle: { color: cssVar('--chart-axis', '#aaa') } },
              splitLine: { show: true, lineStyle: { color: cssVar('--chart-grid', '#eee') } },
            },
            yAxis: {
              axisLabel: { color: cssVar('--chart-text', '#333') },
              axisLine: { lineStyle: { color: cssVar('--chart-axis', '#aaa') } },
              splitLine: { show: true, lineStyle: { color: cssVar('--chart-grid', '#eee') } },
            },
            color: [cssVar('--accent', '#2d6cdf'), cssVar('--accent-2', '#34c38f'), cssVar('--accent-3', '#ff7f50')],
          })
        }
      }
    }
  })
  mo.observe(document.documentElement, { attributes: true })
})

onBeforeUnmount(() => {
  if (chart) chart.dispose()
  if (mo) { try { mo.disconnect() } catch {} mo = null }
})

watch(energySeries, () => update(), { deep: true })
</script>

<template>
  <div class="panel">
    <div class="panel-title">Energy Stacked (K / U / E)</div>
    <div id="energy-chart" class="chart"></div>
  </div>
  
</template>

<style scoped>
.panel { background: var(--surface-1); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 8px; overflow: hidden; }
.panel-title { font-size: 14px; margin-bottom: 6px; color: var(--color-heading); }
.chart { width: 100%; max-width: 100%; height: 240px; }
</style>
