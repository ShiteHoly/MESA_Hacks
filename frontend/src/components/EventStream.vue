<script setup lang="ts">
import { onMounted, onBeforeUnmount, watch } from 'vue'
import { eventSeries } from '@/telemetry'

let chart: any = null
let el: HTMLDivElement | null = null

function init() {
  const ec = (window as any).echarts
  if (!ec || !el) return
  chart = ec.init(el)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 12, top: 10, bottom: 25 },
    xAxis: { type: 'category', data: [] },
    yAxis: { type: 'value', name: 'Impulse', scale: true },
    series: [
      {
        name: '碰撞冲量',
        type: 'bar',
        data: [],
        barWidth: 3,
        itemStyle: { color: '#ff7f50' },
      },
    ],
  })
}

function update() {
  if (!chart) return
  const data = eventSeries.value
  const t = data.map((d) => d.t.toFixed(2))
  const impulses = data.map((d) => d.impulse)
  chart.setOption({ xAxis: { data: t }, series: [{ data: impulses }] })
}

onMounted(() => {
  el = document.getElementById('event-stream') as HTMLDivElement
  init()
  update()
})

onBeforeUnmount(() => { if (chart) chart.dispose() })

watch(eventSeries, () => update(), { deep: true })
</script>

<template>
  <div class="panel">
    <div class="panel-title">碰撞事件流（冲量）</div>
    <div id="event-stream" class="chart"></div>
  </div>
</template>

<style scoped>
.panel { background: var(--color-background); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 8px; }
.panel-title { font-size: 14px; margin-bottom: 6px; color: var(--color-heading); }
.chart { width: 100%; height: 160px; }
</style>

