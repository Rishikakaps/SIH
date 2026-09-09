// Run with both servers started: node tests/ui-smoke.cjs
// Install Playwright separately: npm install --no-save playwright
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
(async () => {
 const browser = await chromium.launch({ headless:true, channel:process.env.BROWSER_CHANNEL || 'msedge' });
 const context = await browser.newContext({ viewport:{width:1440,height:1000}, acceptDownloads:true });
 await context.addInitScript(() => {
   class MockSpeech {
     constructor(){ window.testRecognition=this; }
     start(){ window.speechStarts=(window.speechStarts||0)+1; }
     stop(){ setTimeout(()=>this.onend?.(),0); }
     abort(){ this.aborted=true; this.onend?.(); }
   }
   window.SpeechRecognition=MockSpeech;
 });
 const page = await context.newPage();
 const errors=[]; page.on('pageerror',e=>errors.push(e.message));
 const posts=[]; page.on('request',r=>{ if(r.method()==='POST')posts.push({url:r.url(),body:r.postData()}); });
 const button=name=>page.getByRole('button',{name,exact:true});
 const ready=()=>page.waitForFunction(()=>!document.querySelector('.status'));
 await page.goto(process.env.APP_URL || 'http://localhost:3000');
 await button('Start your visit').evaluate(el=>{el.click();el.click();});
 await page.getByRole('checkbox').waitFor();
 assert.equal(posts.filter(r=>r.url.endsWith('/sessions')).length,1,'duplicate start blocked');
 await page.getByRole('checkbox').check(); await button('Agree & continue').click();
 await page.getByRole('button',{name:/General medicine Tell/}).click();
 await button('Chest pain').click();
 assert.equal(await page.locator('#answer').inputValue(),'Chest pain');
 await button('हिन्दी').click(); await ready();
 assert.equal(await page.locator('#answer').inputValue(),'सीने में दर्द');
 assert.match(await page.locator('.question').innerText(),/तकलीफ़/);
 await button('English').click(); await ready();
 await button('Save & continue').evaluate(el=>{el.click();el.click();}); await ready();
 assert.match(await page.locator('.question').innerText(),/When did/);
 assert.equal(posts.filter(r=>r.url.endsWith('/conversation/message')).length,1,'duplicate answer blocked');
 await button('Back').click(); await ready();
 assert.match(await page.locator('.question').innerText(),/What problem/);
 assert.equal(await page.locator('#answer').inputValue(),'Chest pain');
 await button('Fever').click(); await button('Save & continue').click(); await ready();
  await page.locator('#answer').fill('');
 await page.locator('#voice-mode').selectOption('browser');
 await button('Speak your answer').click();
 assert.equal(await page.evaluate(()=>window.testRecognition.lang),'en-IN');
 assert.equal(await page.evaluate(()=>window.testRecognition.continuous),true);
 await page.evaluate(()=>window.testRecognition.onresult({results:[[{transcript:'It started yesterday'}],[{transcript:'after walking home.'}]]}));
 await button('Stop recording').click(); await button('Speak your answer').waitFor();
 assert.equal(await page.locator('#answer').inputValue(),'It started yesterday after walking home.');
 await page.locator('#answer').fill('It started two days ago after walking home.');
 await button('Save & continue').click(); await ready();
 assert.match(posts.filter(r=>r.url.endsWith('/conversation/message')).at(-1).body,/two days ago/);
 await button('हिन्दी').click(); await ready();
 await button('अपना उत्तर बोलें').click();
 assert.equal(await page.evaluate(()=>window.testRecognition.lang),'hi-IN');
 await page.evaluate(()=>window.testRecognition.onresult({results:[[{transcript:'लगभग दो घंटे तक रहता है'}]]}));
 await button('रिकॉर्डिंग रोकें').click(); await button('अपना उत्तर बोलें').waitFor();
 assert.equal(await page.locator('#answer').inputValue(),'लगभग दो घंटे तक रहता है');
 await button('English').click(); await ready();
 await button('Speak your answer').click();
 await page.evaluate(()=>{window.testRecognition.onerror({error:'not-allowed'});window.testRecognition.onend();});
 assert.match(await page.locator('.speech-error').innerText(),/denied/);
 // Changing mode after answers requires the visible reset confirmation.
 await page.getByRole('button',{name:/Care mode/}).click();
 await page.getByRole('button',{name:/AYUSH care Share/}).click();
 await button('Change mode & restart').click(); await ready();
 assert.equal(await page.locator('.history-item').count(),0);
 await page.locator('#answer').fill('I feel tired after eating');
 await button('Save & continue').click(); await ready();
 await button('Back').click(); await ready();
 assert.equal(await page.locator('#answer').inputValue(),'I feel tired after eating');
 await button('Save & continue').click(); await ready();
 // Finish AYUSH with arbitrary typed input and test Back after completion.
 for(let i=0;i<40 && await page.locator('#answer').count();i++) {
   await page.locator('#answer').fill('No additional details');
   await button('Save & continue').click(); await ready();
 }
 await button('Back to history').click();
 await button('Back').click(); await ready();
 assert.equal(await page.locator('#answer').inputValue(),'No additional details');
 await page.locator('#answer').fill('No known allergies');
 await button('Save & continue').click(); await ready();
 // Real OCR through the browser and editable text.
 await button('Try the two sample documents').click();
 await page.locator('.document-row').first().waitFor({timeout:180000}); await ready();
 assert.equal(await page.locator('.document-row').count(),2);
 await button('Review records').click();
 const text=page.locator('.document-editor textarea').first();
 const original=await text.inputValue();
 await text.fill(original.replace('8.4','5.1'));
 await button('Save corrected text').first().click(); await ready();
 assert.match(await page.locator('.document-editor textarea').first().inputValue(),/5.1/);
 await button('Prepare physician draft').click(); await ready();
 assert.match(await page.locator('#summary').inputValue(),/patient_history/);
 await button('Reject draft').click(); await ready();
 assert.equal(await button('Approve & prepare export').isDisabled(),true);
 await page.locator('#summary').fill((await page.locator('#summary').inputValue())+'\nPhysician reviewed.');
 await button('Approve & prepare export').click(); await ready();
 const downloadPromise=page.waitForEvent('download'); await button('Download record').click();
 assert.equal((await downloadPromise).suggestedFilename(),'rx-lens-record.json');
 await button('Simulate hospital sync').click(); await button('Demo sync complete').waitFor();
 // Responsive screenshots and overflow check.
 await page.setViewportSize({width:390,height:844});
 await page.getByRole('button',{name:/Welcome/}).click();
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);
 const out=process.env.SCREENSHOT_DIR;
 if(out){fs.mkdirSync(out,{recursive:true});await page.screenshot({path:out+'/mobile-en.png',fullPage:true});}
 await button('हिन्दी').click(); await ready();
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);
 if(out) await page.screenshot({path:out+'/mobile-hi.png',fullPage:true});
 assert.deepEqual(errors,[]);
 console.log('PASS: duplicate clicks, bilingual state, both-mode corrections, completion undo, arbitrary speech event handling, microphone errors, real OCR, OCR correction, review/reject/export/sync, 390px layout.');
 await browser.close();
})().catch(error=>{console.error(error);process.exit(1)});

