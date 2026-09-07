import * as THREE from 'three';
import { OrbitControls } from './OrbitControls.js';

const canvas = document.getElementById('viewport');
const error = document.getElementById('error');
try {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0xf5f7f8);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(40, 1, 0.01, 10000);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.12;
  scene.add(new THREE.HemisphereLight(0xffffff, 0x68747c, 2.5));
  const light = new THREE.DirectionalLight(0xffffff, 2);
  light.position.set(1, 2, 3);
  scene.add(light);
  let layers = new THREE.Group();
  scene.add(layers);
  let current = null;
  let extent = new THREE.Box3(new THREE.Vector3(-10, -10, -10), new THREE.Vector3(10, 10, 10));

  function atoms(points, color, radius) {
    if (!points.length) return;
    const mesh = new THREE.InstancedMesh(
      new THREE.SphereGeometry(radius, 10, 8),
      new THREE.MeshStandardMaterial({ color, roughness: 0.6 }), points.length,
    );
    const matrix = new THREE.Matrix4();
    points.forEach((p, i) => mesh.setMatrixAt(i, matrix.makeTranslation(...p)));
    mesh.instanceMatrix.needsUpdate = true;
    layers.add(mesh);
  }

  function reset() {
    const center = extent.getCenter(new THREE.Vector3());
    const radius = Math.max(1, extent.getSize(new THREE.Vector3()).length() / 2);
    const vertical = THREE.MathUtils.degToRad(camera.fov / 2);
    const angle = Math.min(vertical, Math.atan(Math.tan(vertical) * camera.aspect));
    const distance = radius / Math.sin(angle) * 1.15;
    camera.position.copy(center).add(new THREE.Vector3(1, 0.75, 1.2).normalize().multiplyScalar(distance));
    camera.near = Math.max(0.001, distance / 10000);
    camera.far = distance * 100;
    camera.updateProjectionMatrix();
    controls.target.copy(center);
    controls.minDistance = radius * 0.03;
    controls.maxDistance = distance * 8;
    controls.update();
  }

  window.setVinaLabScene = (data) => {
    const content = JSON.stringify([data.receptor, data.reference, data.box]);
    if (current !== content) {
      layers.traverse((object) => { object.geometry?.dispose(); object.material?.dispose(); });
      scene.remove(layers);
      layers = new THREE.Group();
      scene.add(layers);
      atoms(data.receptor || [], 0x768a96, 0.33);
      atoms(data.reference || [], 0xc33f68, 0.55);
      if (data.box) {
        const geometry = new THREE.BoxGeometry(...data.box.size);
        const edges = new THREE.EdgesGeometry(geometry);
        geometry.dispose();
        const box = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0x00866f }));
        box.position.set(...data.box.center);
        layers.add(box);
      }
      extent = new THREE.Box3().setFromObject(layers);
      if (extent.isEmpty()) extent.set(new THREE.Vector3(-10, -10, -10), new THREE.Vector3(10, 10, 10));
      current = content;
    }
    if (data.autoFit) reset();
    renderer.render(scene, camera);
  };
  window.resetVinaLabView = reset;
  window.vinalabCamera = () => camera.position.toArray();
  new ResizeObserver(() => {
    const width = Math.max(1, canvas.clientWidth);
    const height = Math.max(1, canvas.clientHeight);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    reset();
  }).observe(canvas);
  canvas.addEventListener('webglcontextlost', (event) => {
    event.preventDefault();
    error.textContent = '3D graphics context lost. Reopen the preview.';
    error.hidden = false;
    window.vinalabReady = false;
    console.error('VINALAB_RENDERER_ERROR:Graphics context lost. Reopen the preview.');
  });
  renderer.setAnimationLoop(() => { controls.update(); renderer.render(scene, camera); });
  reset();
  window.vinalabReady = true;
  console.info('VINALAB_RENDERER_READY');
  if (window.vinalabPending) window.setVinaLabScene(window.vinalabPending);
} catch (exception) {
  error.textContent = `3D preview unavailable: ${exception.message}`;
  error.hidden = false;
  window.vinalabReady = false;
  console.error(`VINALAB_RENDERER_ERROR:${exception.message}`);
}
