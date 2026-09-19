import {Game,WORLD,GROUND} from './game';
const sprite=['    hhhh    ','   hhhhhhh  ','   hsssssh  ','   hhheehh  ','    hhhh    ','  bbbbbbbb  ',' bbbbbbbbbb ',' bb bbbb bb ',' ss bbbb ss ','    gggg    ','   bbbbbb   ','   bb  bb   ','  bbb  bbb  ','  hhh  hhh  '];
export function draw(ctx:CanvasRenderingContext2D,g:Game,t:number){
 const cam=Math.max(0,Math.min(WORLD-480,g.x-175));ctx.imageSmoothingEnabled=false;
 const rect=(color:string,x:number,y:number,w:number,h:number)=>{ctx.fillStyle=color;ctx.fillRect(Math.round(x),Math.round(y),w,h);};
 const poly=(color:string,points:number[][])=>{ctx.fillStyle=color;ctx.beginPath();points.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath();ctx.fill();};
 const circle=(color:string,x:number,y:number,r:number)=>{ctx.fillStyle=color;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();};
 const sky=ctx.createLinearGradient(0,0,0,320);sky.addColorStop(0,'#0c202b');sky.addColorStop(1,'#243c3e');ctx.fillStyle=sky;ctx.fillRect(0,0,480,320);
 circle('#ccd7b1',373-cam*.025,57,24);circle('#182f35',385-cam*.025,50,24);
 for(let layer=0;layer<2;layer++)for(let i=0;i<17;i++){const x=((i*57-cam*(layer?.4:.18))%610+610)%610-60,top=28+(i*31+layer*19)%110,color=layer?'#254e45':'#1b393d';rect(color,x,top,5+layer*2,300);
  for(let yy=top+10;yy<280;yy+=33){rect('#305b4d',x,yy,7,1);poly(color,[[x,yy],[x-28,yy-14],[x-10,yy+2]]);poly(color,[[x,yy],[x+32,yy-17],[x+14,yy+2]]);}}
 for(let i=0;i<4;i++){ctx.fillStyle='rgba(158,196,174,.035)';ctx.beginPath();ctx.ellipse(240+Math.sin(t*.15+i)*30,180+i*26,330,24,0,0,Math.PI*2);ctx.fill();}
 for(let i=0;i<18;i++)rect('#85a26c',((i*47-cam*.6+Math.sin(t+i)*5)%480+480)%480,70+(i*37)%180+Math.sin(t*.7+i)*6,1,1);
 rect('#142422',0,GROUND,480,34);rect('#63815b',0,GROUND,480,3);
 for(let i=0;i<70;i++){let x=((i*17-cam)%500+500)%500;rect('#496e50',x,GROUND-4-i%4,2,6+i%4);rect('#27362c',x,299+i%15,5,2);}
 for(const [px,py,pw] of g.platforms){let x=px-cam;if(x>-150&&x<490){rect('#3d442e',x,py,pw,9);rect('#828f5e',x,py,pw,3);rect('#313f2f',x+18,py+9,4,GROUND-py-9);rect('#313f2f',x+pw-18,py+9,4,GROUND-py-9);}}
 function ninja(x:number,y:number,enemy=false,facing=1,air=false){const colors:Record<string,string>={h:'#162126',s:'#d5b293',e:'#f9e9b7',b:enemy?'#af4746':'#48a896',g:'#dcbf70'};
  sprite.forEach((row,yy)=>[...row].forEach((c,xx)=>{if(colors[c])rect(colors[c],x-12+(facing===1?xx:11-xx)*2,y-28+yy*2,2,2);}));
  poly(enemy?'#b55249':'#e2a15b',[[x-facing*5,y-22],[x-facing*26,air?y-27:y-18],[x-facing*21,y-20],[x-facing*5,y-19]]);}
 const gx=2510-cam;rect('#9d5140',gx-28,205,6,81);rect('#9d5140',gx+27,205,6,81);rect('#ab5d44',gx-41,201,89,7);rect('#c38c5a',gx-35,218,77,5);ninja(gx,GROUND,false,-1);
 for(const s of g.scrolls)if(!s.found){const x=s.x-cam,y=s.y+Math.sin(t*2+s.x)*2;circle('rgba(216,189,120,.1)',x,y,13);rect('#dfc891',x-5,y-7,10,14);rect('#99683f',x-7,y-8,14,3);rect('#99683f',x-7,y+6,14,3);rect('#625638',x-1,y-3,2,6);}
 for(const e of g.enemies)if(e.x-cam>-25&&e.x-cam<505)ninja(e.x-cam,e.y,true,g.x>e.x?1:-1);
 if(g.invincible<=0||Math.floor(g.invincible*14)%2)ninja(g.x-cam,g.y,false,g.facing,!g.grounded);
 if(g.slashTime>0){ctx.strokeStyle='#f3e6ab';ctx.lineWidth=3;ctx.beginPath();ctx.arc(g.x-cam+g.facing*25,g.y-21,22,g.facing>0?-.9:2.2,g.facing>0?1.4:4.3);ctx.stroke();}
 for(const s of g.shots){const x=s.x-cam,y=s.y;poly(s.hostile?'#e6705b':'#cfe0bc',[[x-5,y],[x-1,y-1],[x,y-5],[x+1,y-1],[x+5,y],[x+1,y+1],[x,y+5],[x-1,y+1]]);}
 rect('#3e5445',14,310,452,2);for(const s of g.scrolls)circle(s.found?'#5f806a':'#debd70',14+s.x/WORLD*452,310,3);circle('#73e6b7',14+g.x/WORLD*452,310,3);
}
