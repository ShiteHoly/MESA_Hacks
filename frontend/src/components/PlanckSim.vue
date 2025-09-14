<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'

type Vec2 = { x: number; y: number }

// Accept external scene data
const props = defineProps<{ sceneData?: any }>()

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

const width = 800
const height = 600
const worldScale = 10
let currentScene: any = null

// Default example scene (ground + ball). Replace with real data as needed.
const defaultScene = {
  world: { gravity: { x: 0, y: -9.8 } },
  objects: [
    { id: 'ground', shape: 'box', type: 'static', position: { x: 25, y: 1 }, size: { width: 100, height: 1 } },
    { id: 'ball_1', shape: 'circle', type: 'dynamic', radius: 1.0, position: { x: 2, y: 12 }, initial_velocity: { x: 5, y: 10 } }
  ],
  joints: []
}

function stopLoop() {
  if (rafId) {
    cancelAnimationFrame(rafId)
    rafId = null
  }
}

function setupSimulation(sceneData: any) {
  const pl: any = (window as any).planck ?? (globalThis as any).planck
  if (!pl) {
    console.error('Planck.js not found on window. Make sure CDN is loaded.')
    return
  }

  const canvas = canvasRef.value!
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')!

  // stop any previous loop before rebuilding
  stopLoop()
  world = new pl.World(pl.Vec2(sceneData.world.gravity.x, sceneData.world.gravity.y))
  mainTrackedBody = null
  elapsedTime = 0
  netForce = { x: 0, y: 0 }
  previousVelocity = pl.Vec2(0, 0)
  currentScene = sceneData

  const bodyMap: Record<string, any> = {}

  // Build bodies
  sceneData.objects.forEach((obj: any) => {
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
      body.createFixture(pl.Box(obj.size.width / 2, obj.size.height / 2), fixtureDef)
    } else if (obj.shape === 'circle') {
      body.createFixture(pl.Circle(obj.radius), fixtureDef)
    }

    const lv = obj.initial_velocity || obj.linearVelocity
    if (lv) body.setLinearVelocity(pl.Vec2(lv.x, lv.y))
  })

  // Joints (Pulley)
  ;(sceneData.joints || []).forEach((jointData: any) => {
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
        ctx.strokeStyle = '#333'
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
    ctx.clearRect(0, 0, width, height)
    ctx.save()
    ctx.scale(worldScale, worldScale)
    const viewboxMaxY = height / worldScale
    ctx.translate(0, viewboxMaxY)
    ctx.scale(1, -1)

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
    world.step(timeStep)
    elapsedTime += timeStep
    if (mainTrackedBody) {
      const currentVelocity = mainTrackedBody.getLinearVelocity()
      const speed = Math.sqrt(currentVelocity.x ** 2 + currentVelocity.y ** 2)
      const deltaV = pl.Vec2.sub(currentVelocity, previousVelocity)
      const acceleration = pl.Vec2.mul(deltaV, 1 / timeStep)
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

      previousVelocity = currentVelocity.clone()
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
  setupSimulation(currentScene || defaultScene)
}

onMounted(() => {
  setupSimulation(props.sceneData || defaultScene)
})

onBeforeUnmount(() => {
  if (rafId) cancelAnimationFrame(rafId)
})

watch(
  () => props.sceneData,
  (val) => {
    if (val) setupSimulation(val)
  }
)
</script>

<template>
  <div class="sim-container">
    <div ref="infoRef" class="info-panel" />
    <button class="reset-button" @click="resetSimulation">Repeat Simulation</button>
    <div ref="paramsRef" class="params-panel" />
    <canvas ref="canvasRef" class="sim-canvas" />
  </div>
  
</template>

<style scoped>
.sim-container {
  position: relative;
  width: 800px;
  height: 600px;
  background: #d3e6ff;
}
.sim-canvas {
  width: 800px;
  height: 600px;
  display: block;
}
.info-panel {
  position: absolute;
  top: 10px;
  right: 10px;
  padding: 10px;
  background-color: rgba(0,0,0,0.5);
  color: white;
  font-family: monospace;
  border-radius: 5px;
  font-size: 14px;
}
.reset-button {
  position: absolute;
  top: 10px;
  left: 10px;
  padding: 8px 12px;
  font-size: 14px;
  cursor: pointer;
}
.params-panel {
  position: absolute;
  top: 50px;
  left: 10px;
  padding: 10px;
  background-color: rgba(0,0,0,0.5);
  color: white;
  font-family: monospace;
  border-radius: 5px;
  font-size: 14px;
}
</style>
