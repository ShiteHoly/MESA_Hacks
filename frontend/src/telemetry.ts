import { reactive, computed } from 'vue'

export type EnergyPoint = {
  t: number // seconds
  y: number // height (world units)
  speed: number // m/s
  mass: number // kg
  K: number // kinetic
  U: number // potential
  E: number // total
}

export type CollisionEvent = {
  t: number
  impulse: number
}

// Simple reactive store without external deps
const state = reactive({
  energy: [] as EnergyPoint[],
  events: [] as CollisionEvent[],
  // sampling control
  maxPoints: 1500, // cap to avoid unbounded growth
})

export function resetTelemetry() {
  state.energy.length = 0
  state.events.length = 0
}

export function recordEnergy(p: EnergyPoint) {
  state.energy.push(p)
  if (state.energy.length > state.maxPoints) state.energy.shift()
}

export function recordEvent(e: CollisionEvent) {
  state.events.push(e)
  if (state.events.length > state.maxPoints) state.events.shift()
}

export const energySeries = computed(() => state.energy)
export const eventSeries = computed(() => state.events)

