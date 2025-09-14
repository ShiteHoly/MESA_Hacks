<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { recordEnergy, recordEvent, resetTelemetry } from '@/telemetry'

type Vec2 = { x: number; y: number }

// Accept external scene data
const props = defineProps<{ sceneData?: any }>()

const containerRef = ref<HTMLDivElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const infoRef = ref<HTMLDivElement | null>(null)
const paramsRef = ref<HTMLDivElement | null>(null)

let world: any = null
let mainTrackedBody: any = null
let rafId: number | null = null
let elapsedTime = 0
const timeStep = 1 / 60
let netForce: Vec2 = { x: 0, y: 0 }
let previousVelocity: any = null
let sampleAccum = 0 // 控制采样频率（用于图表）
const paused = ref(false)
const speed = ref(1) // 0.25x - 3x
// 可调参数
const gravityAbs = ref(9.8) // 重力加速度绝对值（向下）
const globalFriction = ref(0.3)
const globalRestitution = ref(0.4)
const linearDamping = ref(0)
const showGrid = ref(true)

const baseWidth = 800
const baseHeight = 600
// Map backend's x=0 (screen center) to world x=43
const X_OFFSET = 43
const worldScale = 10 // 固定世界比例（px/m），保持物理尺度不变
let viewWidth = baseWidth  // 当前 CSS 尺寸（随容器变化）
let viewHeight = baseHeight
let currentScene: any = null

function stopLoop() {
  if (rafId) {
    cancelAnimationFrame(rafId)
    rafId = null
  }
}

function remapSceneX(sceneData: any, dx: number) {
  const s = JSON.parse(JSON.stringify(sceneData || {}))
  if (Array.isArray(s.objects)) {
    s.objects = s.objects.map((o: any) => {
      const pos = o.position || { x: 0, y: 0 }
      return { ...o, position: { ...pos, x: (pos.x || 0) + dx } }
    })
  }
  if (Array.isArray(s.joints)) {
    s.joints = s.joints.map((j: any) => {
      if (j && j.type === 'PulleyJoint') {
        const ga = j.ground_anchor_a || { x: 0, y: 0 }
        const gb = j.ground_anchor_b || { x: 0, y: 0 }
        return {
          ...j,
          ground_anchor_a: { ...ga, x: (ga.x || 0) + dx },
          ground_anchor_b: { ...gb, x: (gb.x || 0) + dx },
        }
      }
      return j
    })
  }
  return s
}

function setupSimulation(sceneData: any, alreadyMapped = false) {
  const pl: any = (window as any).planck ?? (globalThis as any).planck
  if (!pl) {
    console.error('Planck.js not found on window. Make sure CDN is loaded.')
    return
  }

  const canvas = canvasRef.value!
  const dpr = Math.max(1, Math.floor(window.devicePixelRatio || 1))
  // 初始化为当前视图尺寸（后续会在 resize 时更新）
  canvas.style.width = viewWidth + 'px'
  canvas.style.height = viewHeight + 'px'
  canvas.width = Math.floor(viewWidth * dpr)
  canvas.height = Math.floor(viewHeight * dpr)
  const ctx = canvas.getContext('2d')!

  // stop any previous loop before rebuilding
  stopLoop()
  const mapped = alreadyMapped
    ? JSON.parse(JSON.stringify(sceneData || {}))
    : remapSceneX(sceneData, X_OFFSET)
  world = new pl.World(pl.Vec2(mapped.world.gravity.x, mapped.world.gravity.y))
  mainTrackedBody = null
  elapsedTime = 0
  netForce = { x: 0, y: 0 }
  previousVelocity = pl.Vec2(0, 0)
  currentScene = mapped
  resetTelemetry()

  const bodyMap: Record<string, any> = {}

  // Build bodies
  mapped.objects.forEach((obj: any) => {
    const bodyDef: any = {
      type: obj.type,
      position: obj.position,
      angle: ((obj.angle || 0) * Math.PI) / 180
    }

    let body: any
    if (obj.type === 'static') body = world.createBody(bodyDef)
    else if (obj.type === 'dynamic') {
      body = world.createDynamicBody(bodyDef)
      if (!mainTrackedBody) mainTrackedBody = body
    } else body = world.createBody(bodyDef)

    if (obj.fixedRotation) body.setFixedRotation(true)
    if (typeof obj.gravityScale === 'number') body.setGravityScale(obj.gravityScale)
    if (obj.bullet) body.setBullet(true)

    body.userData = { id: obj.id || 'unknown' }
    bodyMap[obj.id] = body

    const fixtureDef: any = {
      density: obj.density || 1.0,
      friction: obj.friction === 0 ? 0 : obj.friction || 0.3,
      restitution: obj.restitution || 0.4,
      isSensor: !!obj.isSensor
    }

    if (obj.shape === 'box') {
      const w = (obj.size && obj.size.width) ? obj.size.width : obj.width
      const h = (obj.size && obj.size.height) ? obj.size.height : obj.height
      const halfW = (typeof w === 'number' ? w : 1) / 2
      const halfH = (typeof h === 'number' ? h : 1) / 2
      body.createFixture(pl.Box(halfW, halfH), fixtureDef)
    } else if (obj.shape === 'circle') {
      body.createFixture(pl.Circle(obj.radius), fixtureDef)
    }

    const lv = obj.initial_velocity || obj.linearVelocity
    if (lv) body.setLinearVelocity(pl.Vec2(lv.x, lv.y))
  })

  // Joints (Pulley)
  ;(mapped.joints || []).forEach((jointData: any) => {
    if (jointData.type === 'PulleyJoint') {
      const bodyA = bodyMap[jointData.object_a_id]
      const bodyB = bodyMap[jointData.object_b_id]
      if (bodyA && bodyB) {
        const jointDef = {
          bodyA,
          bodyB,
          groundAnchorA: pl.Vec2(jointData.ground_anchor_a.x, jointData.ground_anchor_a.y),
          groundAnchorB: pl.Vec2(jointData.ground_anchor_b.x, jointData.ground_anchor_b.y),
          localAnchorA: pl.Vec2(jointData.local_anchor_a.x, jointData.local_anchor_a.y),
          localAnchorB: pl.Vec2(jointData.local_anchor_b.x, jointData.local_anchor_b.y),
          lengthA: jointData.length_a,
          lengthB: jointData.length_b,
          ratio: jointData.ratio || 1.0
        }
        world.createJoint(pl.PulleyJoint(jointDef))
      }
    }
  })

  // 监听碰撞（post-solve 拿到冲量更直观）
  world.on('post-solve', (contact: any, impulse: any) => {
    try {
      // normalImpulses 是数组；这里取首个作为代表
      const imp = Array.isArray(impulse?.normalImpulses) ? impulse.normalImpulses[0] : 0
      if (imp && imp > 0) recordEvent({ t: elapsedTime, impulse: imp })
    } catch {}
  })

  // 初始应用调参（重力/阻尼/摩擦/弹性）
  applyTuning()

  function drawVector(startPos: any, vector: any, color: string, scale = 1.0) {
    ctx.beginPath()
    ctx.strokeStyle = color
    ctx.lineWidth = 0.2
    const endPos = pl.Vec2.add(startPos, pl.Vec2.mul(vector, scale))
    ctx.moveTo(startPos.x, startPos.y)
    ctx.lineTo(endPos.x, endPos.y)
    const angle = Math.atan2(vector.y, vector.x)
    ctx.moveTo(endPos.x, endPos.y)
    ctx.lineTo(endPos.x - 1 * Math.cos(angle - Math.PI / 6), endPos.y - 1 * Math.sin(angle - Math.PI / 6))
    ctx.moveTo(endPos.x, endPos.y)
    ctx.lineTo(endPos.x - 1 * Math.cos(angle + Math.PI / 6), endPos.y - 1 * Math.sin(angle + Math.PI / 6))
    ctx.stroke()
  }

  function drawPulleyJoints() {
    for (let j = world.getJointList(); j; j = j.getNext()) {
      if (j.getType() === 'pulley-joint') {
        const pulley = j
        const groundA = pulley.getGroundAnchorA()
        const groundB = pulley.getGroundAnchorB()
        const anchorA = pulley.getAnchorA()
        const anchorB = pulley.getAnchorB()

        ctx.beginPath()
        const cs = getComputedStyle(document.documentElement)
        ctx.strokeStyle = (cs.getPropertyValue('--chart-axis').trim() || '#333')
        ctx.lineWidth = 0.15
        ctx.moveTo(groundA.x, groundA.y)
        ctx.lineTo(anchorA.x, anchorA.y)
        ctx.moveTo(groundB.x, groundB.y)
        ctx.lineTo(anchorB.x, anchorB.y)
        ctx.stroke()
      }
    }
  }

  function render() {
    // 复位矩阵并按物理像素清屏
    ctx.setTransform(1, 0, 0, 1, 0, 0)
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.save()
    // DPR 缩放到 CSS 像素，再进入世界坐标
    const dprLocal = Math.max(1, Math.floor(window.devicePixelRatio || 1))
    ctx.scale(dprLocal, dprLocal)
    ctx.scale(worldScale, worldScale)
    const viewboxMaxY = viewHeight / worldScale
    ctx.translate(0, viewboxMaxY)
    ctx.scale(1, -1)

    // 背景网格（世界坐标，可开关）
    if (showGrid.value) {
      const cs = getComputedStyle(document.documentElement)
      const minorColor = cs.getPropertyValue('--grid-minor').trim() || 'rgba(0,0,0,0.06)'
      const majorColor = cs.getPropertyValue('--grid-major').trim() || 'rgba(0,0,0,0.12)'
      const vw = viewWidth / worldScale
      const vh = viewHeight / worldScale
      ctx.save()
      ctx.lineWidth = 0.02
      // 次级网格 1m
      ctx.strokeStyle = minorColor
      for (let x = 0; x <= vw; x += 1) {
        ctx.beginPath()
        ctx.moveTo(x, 0)
        ctx.lineTo(x, vh)
        ctx.stroke()
      }
      for (let y = 0; y <= vh; y += 1) {
        ctx.beginPath()
        ctx.moveTo(0, y)
        ctx.lineTo(vw, y)
        ctx.stroke()
      }
      // 主网格 5m
      ctx.strokeStyle = majorColor
      ctx.lineWidth = 0.03
      for (let x = 0; x <= vw; x += 5) {
        ctx.beginPath()
        ctx.moveTo(x, 0)
        ctx.lineTo(x, vh)
        ctx.stroke()
      }
      for (let y = 0; y <= vh; y += 5) {
        ctx.beginPath()
        ctx.moveTo(0, y)
        ctx.lineTo(vw, y)
        ctx.stroke()
      }
      ctx.restore()
    }

    // Bodies
    for (let body = world.getBodyList(); body; body = body.getNext()) {
      const pos = body.getPosition()
      const id = body.userData.id

      ctx.save()
      ctx.translate(pos.x, pos.y)
      ctx.rotate(body.getAngle())
      for (let fixture = body.getFixtureList(); fixture; fixture = fixture.getNext()) {
        const shape = fixture.getShape()
        if (shape.getType() === 'circle') {
          ctx.beginPath()
          ctx.arc(0, 0, shape.m_radius, 0, 2 * Math.PI)
          ctx.fillStyle = body.isDynamic() ? '#ff6347' : '#808080'
          ctx.fill()
        } else if (shape.getType() === 'polygon') {
          const vertices = shape.m_vertices
          ctx.beginPath()
          ctx.moveTo(vertices[0].x, vertices[0].y)
          for (let i = 1; i < vertices.length; i++) ctx.lineTo(vertices[i].x, vertices[i].y)
          ctx.closePath()
          ctx.fillStyle = '#808080'
          ctx.fill()
        }
      }
      ctx.restore()

      // Labels upright
      ctx.save()
      ctx.translate(pos.x, pos.y)
      ctx.scale(1, -1)
      ctx.fillStyle = 'black'
      ctx.font = 'bold 1.5px Arial'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(id, 0, 0)
      ctx.restore()
    }

    // Joints/ropes after bodies
    drawPulleyJoints()

    // Net force vector on main tracked body
    if (mainTrackedBody) {
      const bodyPos = mainTrackedBody.getPosition()
      drawVector(bodyPos, netForce, 'red', 0.1)
    }

    ctx.restore()
  }

  function step() {
    const dt = paused.value ? 0 : timeStep * speed.value
    if (!paused.value) {
      world.step(dt)
      elapsedTime += dt
      sampleAccum += dt
    }
    if (mainTrackedBody) {
      const currentVelocity = mainTrackedBody.getLinearVelocity()
      const speed = Math.sqrt(currentVelocity.x ** 2 + currentVelocity.y ** 2)
      const deltaV = pl.Vec2.sub(currentVelocity, previousVelocity)
      const acceleration = dt > 0 ? pl.Vec2.mul(deltaV, 1 / dt) : pl.Vec2(0, 0)
      const mass = mainTrackedBody.getMass()
      netForce = pl.Vec2.mul(acceleration, mass)
      const netForceMagnitude = Math.sqrt(netForce.x ** 2 + netForce.y ** 2)

      if (infoRef.value) {
        infoRef.value.innerHTML = `Time: ${elapsedTime.toFixed(2)} s<br>Speed: ${speed.toFixed(2)} m/s<br>Accel: (${acceleration.x.toFixed(2)}, ${acceleration.y.toFixed(2)})<br>Net Force: ${netForceMagnitude.toFixed(2)} N`
      }

      if (paramsRef.value) {
        const id = mainTrackedBody.userData.id
        const massVal = mainTrackedBody.getMass()
        const ballFixture = mainTrackedBody.getFixtureList()
        const friction = ballFixture ? ballFixture.getFriction() : 'N/A'
        const inertia = mainTrackedBody.getInertia()
        paramsRef.value.innerHTML = `--- World Params ---<br>Gravity: (${world.getGravity().x.toFixed(2)}, ${world.getGravity().y.toFixed(2)})<br><br>--- Object ${id} Params ---<br>Mass: ${massVal.toFixed(2)} kg<br>Friction Coeff: ${friction}<br>Inertia: ${inertia.toFixed(4)}`
      }

      if (!paused.value) previousVelocity = currentVelocity.clone()

      // 20Hz 采样能量，降低图表数据量
      if (sampleAccum >= 1 / 20) {
        sampleAccum = 0
        const pos = mainTrackedBody.getPosition()
        const g = Math.abs(world.getGravity().y)
        const K = 0.5 * mass * speed * speed
        const U = mass * g * pos.y
        const E = K + U
        recordEnergy({ t: elapsedTime, y: pos.y, speed, mass, K, U, E })
      }
    }
    render()
    rafId = requestAnimationFrame(step)
  }

  // Kick-off
  render()
  step()
}

function resetSimulation() {
  if (!world) return
  // Destroy all bodies
  for (let b = world.getBodyList(); b; b = b.getNext()) {
    world.destroyBody(b)
  }
  if (currentScene) setupSimulation(currentScene, true)
}

function applyTuning() {
  if (!world) return
  const pl: any = (window as any).planck ?? (globalThis as any).planck
  world.setGravity(pl.Vec2(0, -gravityAbs.value))
  for (let body = world.getBodyList(); body; body = body.getNext()) {
    if (body.isDynamic && body.isDynamic()) {
      body.setLinearDamping(linearDamping.value)
    }
    for (let fix = body.getFixtureList(); fix; fix = fix.getNext()) {
      if (typeof fix.setFriction === 'function') fix.setFriction(globalFriction.value)
      if (typeof fix.setRestitution === 'function') fix.setRestitution(globalRestitution.value)
    }
  }
}

function applyResize() {
  const container = containerRef.value
  const canvas = canvasRef.value
  if (!container || !canvas) return
  const dpr = Math.max(1, Math.floor(window.devicePixelRatio || 1))
  // 仅考虑 16:9 页面布局，这里按容器宽度计算 4:3 画布高
  const maxW = container.clientWidth
  // 可根据需要限制最大宽度，这里允许扩展到容器宽度
  viewWidth = Math.max(400, Math.min(maxW, baseWidth))
  viewHeight = Math.round((viewWidth * baseHeight) / baseWidth)
  // 更新 CSS 与物理像素尺寸
  canvas.style.width = viewWidth + 'px'
  canvas.style.height = viewHeight + 'px'
  canvas.width = Math.floor(viewWidth * dpr)
  canvas.height = Math.floor(viewHeight * dpr)
}

onMounted(() => {
  applyResize()
  window.addEventListener('resize', applyResize)
  if (props.sceneData) setupSimulation(props.sceneData, false)
})

onBeforeUnmount(() => {
  if (rafId) cancelAnimationFrame(rafId)
  window.removeEventListener('resize', applyResize)
})

watch(
  () => props.sceneData,
  (val) => {
    if (val) setupSimulation(val, false)
  }
)

// 滑块调参监听，变更后立即作用于世界
watch([gravityAbs, globalFriction, globalRestitution, linearDamping], applyTuning)
watch(speed, () => { /* 速度直接在 step 中读取，无需额外操作 */ })
</script>

<template>
  <div class="sim-container" ref="containerRef">
    <div ref="infoRef" class="info-panel" />
    <div class="controls">
      <button class="btn" @click="paused = !paused">{{ paused ? 'Resume' : 'Pause' }}</button>
      <div class="spacer"></div>
      <button class="btn" :class="{ active: speed === 0.5 }" @click="speed = 0.5">0.5x</button>
      <button class="btn" :class="{ active: speed === 1 }" @click="speed = 1">1x</button>
      <button class="btn" :class="{ active: speed === 2 }" @click="speed = 2">2x</button>
      <div class="spacer"></div>
      <button class="btn primary" @click="resetSimulation">Replay</button>
    </div>
    <div ref="paramsRef" class="params-panel" />
    <canvas ref="canvasRef" class="sim-canvas" />
  </div>
  <div class="tune-bar">
    <div class="row">
      <label>Gravity |g|</label>
      <input class="num" type="number" step="0.1" min="0" max="20" v-model.number="gravityAbs" />
    </div>
    <div class="row">
      <label>Damping</label>
      <input class="num" type="number" step="0.1" min="0" max="5" v-model.number="linearDamping" />
    </div>
    <div class="row">
      <label>Friction</label>
      <input type="range" min="0" max="1" step="0.05" v-model.number="globalFriction" />
      <span class="val">{{ globalFriction.toFixed(2) }}</span>
    </div>
    <div class="row">
      <label>Restitution</label>
      <input type="range" min="0" max="1" step="0.05" v-model.number="globalRestitution" />
      <span class="val">{{ globalRestitution.toFixed(2) }}</span>
    </div>
    <div class="row inline">
      <label><input type="checkbox" v-model="showGrid" /> Show Grid</label>
    </div>
  </div>
  
</template>

<style scoped>
.sim-container {
  position: relative;
  width: 800px; /* 右列宽度固定为 800px；内部画布自适应该宽度上限 */
  height: 600px; /* 初始高度；实际以 4:3 比例由视图高度控制 */
  background: var(--sim-bg);
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: 0 6px 20px rgba(0,0,0,0.08);
}
.sim-canvas {
  width: 100%;
  height: auto;
  display: block;
}
.controls {
  position: absolute;
  top: 10px;
  left: 10px;
  display: flex;
  gap: 6px;
  align-items: center;
  background: var(--panel-bg);
  color: var(--panel-text);
  border-radius: var(--radius-sm);
  padding: 6px;
}
.controls .spacer { width: 8px; }
.btn {
  padding: 4px 8px;
  border: 1px solid var(--color-border);
  background: var(--color-background);
  color: var(--color-heading);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 12px;
}
.btn.primary { border-color: var(--accent); background: var(--accent); color: #fff; }
.btn.active { outline: 2px solid var(--accent); }
.info-panel {
  position: absolute;
  top: 10px;
  right: 10px;
  padding: 10px;
  background-color: var(--panel-bg);
  color: var(--panel-text);
  font-family: monospace;
  border-radius: var(--radius-sm);
  font-size: 14px;
}
.reset-button {
  position: absolute;
  top: 10px;
  left: 10px;
  padding: 8px 12px;
  font-size: 14px;
  cursor: pointer;
  border: 1px solid var(--accent);
  background: var(--accent);
  color: #fff;
  border-radius: var(--radius-sm);
}
.params-panel {
  position: absolute;
  top: 50px;
  left: 10px;
  padding: 10px;
  background-color: var(--panel-bg);
  color: var(--panel-text);
  font-family: monospace;
  border-radius: var(--radius-sm);
  font-size: 14px;
}
/* 画布下方的调参栏 */
.tune-bar {
  margin-top: 8px;
  background: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 8px;
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.tune-bar .row { display: flex; align-items: center; gap: 8px; }
.tune-bar .row.inline { grid-column: span 2; }
.tune-bar label { font-size: 12px; min-width: 64px; color: var(--color-heading); }
.tune-bar .num { width: 80px; padding: 4px 6px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); background: var(--color-background-soft); color: var(--color-heading); }
.tune-bar select { padding: 4px 6px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); background: var(--color-background-soft); color: var(--color-heading); }
.tune-bar input[type=\"range\"] { flex: 1; }
.tune-bar .val { font-size: 12px; color: var(--color-heading); font-weight: 600; width: 48px; text-align: right; }
</style>
