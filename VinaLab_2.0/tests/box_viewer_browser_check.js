async (page) => {
  const results = [];
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const remote = [];
  await page.route('**/*', route => {
    if (!route.request().url().startsWith('http://127.0.0.1:8876/')) {
      remote.push(route.request().url());
      return route.abort();
    }
    return route.continue();
  });
  for (const size of [{ width: 1200, height: 800 }, { width: 390, height: 640 }]) {
    await page.setViewportSize(size);
    await page.goto('http://127.0.0.1:8876/index.html');
    await page.waitForFunction(() => window.vinalabReady === true);
    await page.evaluate(() => window.setVinaLabScene({
      receptor: Array.from({ length: 70 }, (_, i) => [
        Math.cos(i * 0.4) * 7, (i - 35) * 0.25, Math.sin(i * 0.4) * 7,
      ]),
      reference: [[-2, 0, 0], [0, 1, 0], [2, 0, 1]],
      box: { center: [0, 0, 0], size: [12, 14, 16] }, autoFit: true,
    }));
    await page.waitForTimeout(200);
    const pixels = await page.evaluate(() => {
      const source = document.querySelector('canvas');
      const copy = document.createElement('canvas');
      copy.width = source.width;
      copy.height = source.height;
      const ctx = copy.getContext('2d');
      ctx.drawImage(source, 0, 0);
      const data = ctx.getImageData(0, 0, copy.width, copy.height).data;
      let dark = 0, reference = 0, box = 0;
      for (let i = 0; i < data.length; i += 4) {
        const [r, g, b] = data.slice(i, i + 3);
        if (r < 220 || g < 220 || b < 220) dark++;
        if (r > g * 1.2 && r > b * 1.08 && r > 100) reference++;
        if (g > r * 1.3 && g > b * 1.03 && g > 70) box++;
      }
      return { dark, reference, box };
    });
    if (pixels.dark < 500 || pixels.reference < 15 || pixels.box < 40) {
      throw new Error(`Blank/missing layers: ${JSON.stringify(pixels)}`);
    }
    const before = await page.evaluate(() => window.vinalabCamera());
    await page.mouse.move(size.width / 2, size.height / 2);
    await page.mouse.down();
    await page.mouse.move(size.width / 2 + 70, size.height / 2 + 40, { steps: 10 });
    await page.mouse.up();
    await page.waitForTimeout(400);
    const rotated = await page.evaluate(() => window.vinalabCamera());
    if (JSON.stringify(before) === JSON.stringify(rotated)) throw new Error('Rotation failed');
    await page.mouse.wheel(0, -200);
    await page.waitForTimeout(400);
    const zoomed = await page.evaluate(() => window.vinalabCamera());
    if (JSON.stringify(rotated) === JSON.stringify(zoomed)) throw new Error('Zoom failed');
    await page.evaluate(() => window.resetVinaLabView());
    await page.waitForTimeout(600);
    const reset = await page.evaluate(() => window.vinalabCamera());
    if (reset.some((value, i) => Math.abs(value - before[i]) > 0.01)) {
      throw new Error('Reset did not restore the fitted camera');
    }
    await page.screenshot({ path: `vinalab-box-${size.width}.png` });
    results.push({ viewport: size, pixels, rotation: true, zoom: true, reset: true });
  }
  if (errors.length || remote.length) throw new Error(JSON.stringify({ errors, remote }));
  return { results, errors, externalRequests: remote };
}
