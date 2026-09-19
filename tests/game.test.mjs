import {test} from 'node:test';
import assert from 'node:assert/strict';
import {Game,demoAction} from '../lib/game.ts';
test('rules demonstration collects all scrolls and rescues the hostage',()=>{const g=new Game();for(let i=0;i<1800&&g.status==='playing';i++)g.step(demoAction(g));assert.equal(g.status,'won');assert.equal(g.collected,3);assert.ok(g.hp>0);});
test('scroll collection requires elevation and gate requires all three',()=>{const g=new Game();g.x=510;g.step();assert.equal(g.collected,0);g.y=178;g.step();assert.equal(g.collected,1);g.x=2520;g.step();assert.equal(g.status,'playing');g.scrolls.forEach(s=>s.found=true);g.step();assert.equal(g.status,'won');});
test('damage cooldown protects against simultaneous hits',()=>{const g=new Game();g.damage();g.damage();assert.equal(g.hp,4);});
test('jump lands on one-way platform',()=>{const g=new Game();g.x=260;g.step('jump_right');for(let i=0;i<90;i++)g.step();assert.equal(g.y,224);assert.ok(g.grounded);});
