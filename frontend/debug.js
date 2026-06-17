import puppeteer from 'puppeteer';

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('BROWSER_LOG:', msg.text()));
  page.on('pageerror', error => console.log('BROWSER_ERROR:', error.message));
  
  await page.goto('http://localhost:5173/graph', { waitUntil: 'networkidle2' });
  
  // Wait a moment for rendering
  await new Promise(r => setTimeout(r, 2000));
  
  const content = await page.content();
  console.log('HTML length:', content.length);
  
  const hasPlotly = await page.evaluate(() => {
    return document.querySelectorAll('.js-plotly-plot').length;
  });
  console.log('Plotly instances:', hasPlotly);
  
  const text = await page.evaluate(() => document.body.innerText);
  console.log('PAGE TEXT:', text.slice(0, 500));
  
  await page.screenshot({ path: 'screenshot.png' });
  
  await browser.close();
})();
