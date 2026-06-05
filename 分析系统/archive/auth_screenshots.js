const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();
  const base = 'http://127.0.0.1:5001';

  // Register
  await page.goto(`${base}/register`, { waitUntil: 'networkidle' });
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.fill('#confirm', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(1000);
  // Now logged in, should be on dashboard
  await page.screenshot({ path: 'C:/Users/Administrator/Desktop/All Mix/p_dashboard.png', fullPage: true });
  console.log('Dashboard captured');

  // Go to home
  await page.goto(`${base}/home`, { waitUntil: 'networkidle' });
  await page.screenshot({ path: 'C:/Users/Administrator/Desktop/All Mix/p_home.png', fullPage: true });
  console.log('Home captured');

  // API health
  await page.goto(`${base}/api/v1/cli/health`, { waitUntil: 'networkidle' });
  await page.screenshot({ path: 'C:/Users/Administrator/Desktop/All Mix/p_api_health.png', fullPage: true });
  console.log('API health captured');

  // API system info
  await page.goto(`${base}/api/v1/system/info`, { waitUntil: 'networkidle' });
  await page.screenshot({ path: 'C:/Users/Administrator/Desktop/All Mix/p_api_info.png', fullPage: true });
  console.log('API info captured');

  await browser.close();
  console.log('Done');
})();
