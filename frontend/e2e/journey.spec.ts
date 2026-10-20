import {test,expect} from '@playwright/test';
test('complete sandbox journey and responsive layout',async({page})=>{
 await page.goto('/');await expect(page.getByText('T2D / hypertension / CKD context')).toBeVisible();
 await page.getByRole('button',{name:'Patient & FHIR'}).click();await expect(page.getByText('FHIR R4 document inspection')).toBeVisible();
 await page.getByRole('button',{name:'Control room'}).click();await page.getByRole('button',{name:'Start replay'}).click();await page.waitForTimeout(1400);await page.getByRole('button',{name:'Pause replay'}).click();
 await page.getByRole('button',{name:'Post-meal input',exact:true}).click();await expect(page.getByText('Packet 157 / 2880')).toBeVisible();
 await page.getByRole('button',{name:'Compare scenario'}).click();await expect(page.getByRole('heading',{name:/Peak delta/})).toBeVisible();
 await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:'../reports/dashboard-desktop.png',fullPage:true});
 await page.getByRole('button',{name:'Evaluation',exact:true}).click();await expect(page.getByText('Held-out synthetic evaluation')).toBeVisible();await expect(page.getByRole('cell',{name:'reduced_order',exact:true})).toHaveCount(5);
 await page.getByRole('button',{name:'Revoke consent'}).click();await expect(page.getByText('Demo access locked')).toBeVisible();
 const response=await page.request.get('/api/v1/twin/PT-IND-001/state');expect(response.status()).toBe(403);
 await page.getByRole('button',{name:'Restore demo access'}).click();await expect(page.getByText('T2D / hypertension / CKD context')).toBeVisible();
 await page.getByLabel('Synthetic patient').selectOption('PT-IND-003');await expect(page.getByText('Prediabetes / rotating shift work context')).toBeVisible();
 await page.getByRole('button',{name:'Control room'}).click();await page.setViewportSize({width:390,height:844});await page.screenshot({path:'../reports/dashboard-mobile.png',fullPage:true});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
