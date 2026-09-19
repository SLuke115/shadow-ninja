export const WORLD=2600, GROUND=286, DT=1/60, MACRO=18;
export const ACTIONS: Record<string,string> = {
 wait:'Stand still. Let a projectile pass or wait to land.',
 left:'Move left.',right:'Move right toward the rescue gate.',
 jump_left:'Move left and jump if grounded. Jump repeats on landing.',
 jump_right:'Move right and jump if grounded. Jump repeats on landing.',
 throw_left:'Move left and throw a shuriken left if ready.',
 throw_right:'Move right and throw a shuriken right if ready.',
 jump_throw_left:'Jump and move left, throwing left if ready.',
 jump_throw_right:'Jump and move right, throwing right if ready.',
 slash:'Stand and slash toward facing direction, 54 pixel range; deflect nearby shots.'
};
export const LABELS: Record<string,string>={wait:'等待',left:'向左移动',right:'向右移动',jump_left:'向左跳跃',jump_right:'向右跳跃',throw_left:'向左投镖',throw_right:'向右投镖',jump_throw_left:'左跳投镖',jump_throw_right:'右跳投镖',slash:'近身刀击',manual:'手动控制'};
export type Enemy={x:number;y:number;hp:number;cooldown:number};
export type Shot={x:number;y:number;vx:number;hostile:boolean;life:number};
export type Controls=[number,boolean,boolean,boolean];
export class Game {
 x=64;y=GROUND;vy=0;facing=1;hp=5;grounded=true;cooldown=0;swordCd=0;invincible=0;slashTime=0;elapsed=0;kills=0;status='playing';
 platforms=[[220,224,115],[460,178,110],[720,224,140],[1040,200,125],[1340,154,140],[1620,214,140],[1920,190,150],[2180,224,120]];
 scrolls=[{x:510,y:162,found:false},{x:1410,y:138,found:false},{x:1995,y:174,found:false}];
 enemies:Enemy[]=[380,680,960,1240,1560,1860,2170,2380].map((x,i)=>({x,y:GROUND,hp:2,cooldown:1.4+i*.25}));
 shots:Shot[]=[];
 get collected(){return this.scrolls.filter(s=>s.found).length;}
 damage(){if(this.invincible<=0){this.hp--;this.invincible=1.25;if(this.hp<=0)this.status='lost';}}
 hit(e:Enemy,n=1){e.hp-=n;if(e.hp<=0){this.enemies=this.enemies.filter(v=>v!==e);this.kills++;}}
 step(action='wait',controls?:Controls){
  if(this.status!=='playing')return;
  this.elapsed+=DT;
  const [dir,jump,shoot,slash]=controls??[action.includes('left')?-1:action.includes('right')?1:0,action.includes('jump'),action.includes('throw'),action==='slash'];
  this.cooldown=Math.max(0,this.cooldown-DT);this.swordCd=Math.max(0,this.swordCd-DT);this.invincible=Math.max(0,this.invincible-DT);this.slashTime=Math.max(0,this.slashTime-DT);
  if(dir)this.facing=dir;
  this.x=Math.max(12,Math.min(WORLD-12,this.x+dir*145*DT));
  if(jump&&this.grounded){this.vy=-435;this.grounded=false;}
  const prev=this.y;this.vy+=720*DT;this.y+=this.vy*DT;this.grounded=false;
  if(this.vy>=0){for(const [x,y,w] of [...this.platforms].sort((a,b)=>a[1]-b[1]))if(x-7<this.x&&this.x<x+w+7&&prev<=y&&y<=this.y){this.y=y;this.vy=0;this.grounded=true;break;}
   if(this.y>=GROUND){this.y=GROUND;this.vy=0;this.grounded=true;}}
  if(shoot&&this.cooldown<=0){this.shots.push({x:this.x+12*this.facing,y:this.y-17,vx:this.facing*360,hostile:false,life:2});this.cooldown=.28;}
  if(slash&&this.swordCd<=0){this.swordCd=.32;this.slashTime=.16;for(const e of [...this.enemies])if(-8<(e.x-this.x)*this.facing&&(e.x-this.x)*this.facing<54&&Math.abs(e.y-this.y)<38)this.hit(e,2);
   this.shots=this.shots.filter(s=>!(s.hostile&&Math.abs(s.x-this.x)<54&&Math.abs(s.y-(this.y-16))<35));}
  for(const e of this.enemies){const d=this.x-e.x;if(Math.abs(d)<380){e.x+=(d>0?1:-1)*27*DT;e.cooldown-=DT;
   if(e.cooldown<=0){this.shots.push({x:e.x,y:e.y-17,vx:d>0?155:-155,hostile:true,life:3});e.cooldown=2.5;}
   if(Math.abs(d)<20&&Math.abs(e.y-this.y)<25)this.damage();}}
  this.shots=this.shots.filter(s=>{s.x+=s.vx*DT;s.life-=DT;if(s.life<=0)return false;
   if(s.hostile){if(Math.abs(s.x-this.x)<12&&this.y-30<s.y&&s.y<this.y){this.damage();return false;}}
   else for(const e of [...this.enemies])if(Math.abs(s.x-e.x)<14&&e.y-30<s.y&&s.y<e.y){this.hit(e);return false;}
   return true;});
  for(const s of this.scrolls)if(!s.found&&Math.abs(this.x-s.x)<23&&Math.abs(this.y-18-s.y)<27)s.found=true;
  if(this.x>WORLD-100&&this.collected===3&&this.hp>0)this.status='won';
 }
 state(){return {goal:'Collect all three scrolls, then reach rescue gate at x=2500. Stay alive.',coordinates:'x rightward; y downward; player y is feet; scroll y is center.',
 player:{x:Math.round(this.x),feet_y:Math.round(this.y),vy:Math.round(this.vy),grounded:this.grounded,facing:this.facing,hp:this.hp,throw_ready:this.cooldown===0,sword_ready:this.swordCd===0},
 physics:{macro_frames:MACRO,speed:145,jump_height:130,jump_distance:175,platforms:'one-way; land from above; no pits; jump repeats on landing',network:'World pauses during inference.'},
 remaining_scrolls:this.scrolls.filter(s=>!s.found).map(s=>({x:s.x,y:s.y,dx:Math.round(s.x-this.x)})),
 platforms:this.platforms.filter(p=>Math.abs(p[0]-this.x)<550).map(([x,y,w])=>({x,top_y:y,width:w})),
 enemies:this.enemies.filter(e=>Math.abs(e.x-this.x)<420).map(e=>({dx:Math.round(e.x-this.x),feet_y:e.y,hp:e.hp})),
 incoming_shuriken:this.shots.filter(s=>s.hostile&&Math.abs(s.x-this.x)<260).map(s=>({dx:Math.round(s.x-this.x),y:Math.round(s.y),vx:s.vx})),collected:this.collected,status:this.status};}
}
export function demoAction(g:Game){const targets=g.scrolls.filter(s=>!s.found),target=targets[0]?.x??2520,d=target>g.x?'right':'left';
 const e=g.enemies.find(e=>Math.abs(e.x-g.x)<48&&Math.abs(e.y-g.y)<30);if(e&&(e.x-g.x)*g.facing>0)return 'slash';
 return (targets.length&&Math.abs(target-g.x)<260?'jump_throw_':'throw_')+d;}
