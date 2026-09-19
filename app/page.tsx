'use client';
import {useEffect,useRef,useState} from 'react';
import {Game,demoAction,LABELS,MACRO} from '../lib/game';
import {draw} from '../lib/draw';

type Mode='manual'|'demo'|'ai';
type Hud={mode:Mode;hp:number;scrolls:number;kills:number;elapsed:number;status:string;started:boolean;paused:boolean;busy:boolean;calls:number;limit:number;action:string;confidence:number;latency:number;error:string;probs:Record<string,number>};
const initial:Hud={mode:'manual',hp:5,scrolls:0,kills:0,elapsed:0,status:'playing',started:false,paused:false,busy:false,calls:0,limit:200,action:'wait',confidence:0,latency:0,error:'',probs:{}};
export default function Home(){
 const canvas=useRef<HTMLCanvasElement>(null),surface=useRef<HTMLDivElement>(null);
 const command=useRef<(name:string,value?:string)=>void>(()=>{});
 const touch=useRef<Record<string,boolean>>({});
 const [hud,setHud]=useState<Hud>(initial),[modal,setModal]=useState(false),[keyInput,setKeyInput]=useState(''),[keyError,setKeyError]=useState('');
 const modalOpen=useRef(false);
 useEffect(()=>{modalOpen.current=modal;},[modal]);
 useEffect(()=>{
  const ctx=canvas.current?.getContext('2d');if(!ctx)return;
  let game=new Game(),h={...initial},key='',generation=0,frames=0,acc=0,last=0,published=0,raf=0,disposed=false;
  let pending:AbortController|null=null;
  const keys:Record<string,boolean>={};
  const publish=()=>{if(!disposed)setHud({...h,hp:game.hp,scrolls:game.collected,kills:game.kills,elapsed:game.elapsed,status:game.status,probs:{...h.probs}});};
  const invalidate=()=>{generation++;pending?.abort();pending=null;h.busy=false;frames=0;acc=0;};
  const selectMode=(mode:Mode)=>{invalidate();h.mode=mode;h.error='';h.action='wait';h.probs={};h.confidence=0;h.latency=0;
   if(mode==='ai'&&!key){modalOpen.current=true;setModal(true);return;}h.started=true;h.paused=false;};
  command.current=(name,value)=>{
   if(name==='start'){h.started=true;h.paused=false;}
   if(['manual','demo','ai'].includes(name))selectMode(name as Mode);
   if(name==='restart'){invalidate();game=new Game();h.error='';h.started=true;h.paused=false;h.action='wait';}
   if(name==='pause')h.paused=!h.paused;
   if(name==='settings'){modalOpen.current=true;setModal(true);}
   if(name==='cancel'){modalOpen.current=false;setModal(false);if(!key&&h.mode==='ai')selectMode('manual');}
   if(name==='connect'){key=value??'';setKeyInput('');modalOpen.current=false;setModal(false);if(game.status!=='playing')game=new Game();selectMode('ai');}
   if(name==='retry'){h.error='';h.paused=false;}
   if(name==='limit'){h.limit=Number(value);if(h.calls<h.limit&&h.error.includes('本次测试'))h.error='';}
   publish();
  };
  async function decide(){
   if(h.calls>=h.limit){h.error='本次测试已达 '+h.limit+' 次调用上限，不代表账户欠费。可在下方提高上限，或改为手动继续。';return;}
   const gen=generation,controller=new AbortController();pending=controller;h.busy=true;h.calls++;publish();
   const timeout=setTimeout(()=>controller.abort(),20000);
   try{const response=await fetch('/api/jev',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key,state:game.state()}),signal:controller.signal});
    const data=await response.json() as {error?:string;action:string;confidence:number;latency:number;probabilities:Record<string,number>};if(gen!==generation||disposed)return;
    if(!response.ok)throw new Error(data.error||'模型调用失败，请重试。');
    h.action=data.action;h.confidence=data.confidence;h.latency=data.latency;h.probs=data.probabilities;frames=MACRO;
   }catch(e){if(gen===generation&&!disposed)h.error=controller.signal.aborted?'请求超时，游戏已暂停，请稍后重试。':e instanceof Error?e.message:'网络异常，请重试。';}
   finally{clearTimeout(timeout);if(gen===generation&&!disposed){h.busy=false;pending=null;publish();}}
  }
  function step(){
   if(!h.started||h.paused||modalOpen.current||game.status!=='playing')return;
   if(h.mode==='manual'){const pressed=(...names:string[])=>names.some(n=>keys[n]||touch.current[n]);h.action='manual';game.step('wait',[Number(pressed('d','ArrowRight'))-Number(pressed('a','ArrowLeft')),pressed(' ','w','ArrowUp'),pressed('j'),pressed('k')]);}
   else if(h.mode==='demo'){h.action=demoAction(game);game.step(h.action);}
   else if(!h.busy&&!h.error){if(frames>0){game.step(h.action);frames--;}else void decide();}
  }
  function frame(t:number){if(disposed)return;const delta=Math.min((t-last)/1000,.08);last=t;acc+=delta;while(acc>=1/60){step();acc-=1/60;}draw(ctx!,game,t/1000);if(t-published>100){publish();published=t;}raf=requestAnimationFrame(frame);}
  const down=(e:KeyboardEvent)=>{if(modalOpen.current||/INPUT|TEXTAREA|SELECT/.test((e.target as HTMLElement)?.tagName))return;let k=e.key.length===1?e.key.toLowerCase():e.key;
   if([' ','ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(k))e.preventDefault();keys[k]=true;if(e.repeat)return;
   const cmd:Record<string,string>={'1':'manual','2':'demo','3':'ai',r:'restart',p:'pause',F2:'settings'};if(cmd[k])command.current(cmd[k]);};
  const up=(e:KeyboardEvent)=>{keys[e.key.length===1?e.key.toLowerCase():e.key]=false;};
  const blur=()=>{for(const k of Object.keys(keys))delete keys[k];touch.current={};if(h.started)h.paused=true;publish();};
  window.addEventListener('keydown',down);window.addEventListener('keyup',up);window.addEventListener('blur',blur);raf=requestAnimationFrame(frame);
  return()=>{disposed=true;pending?.abort();cancelAnimationFrame(raf);key='';window.removeEventListener('keydown',down);window.removeEventListener('keyup',up);window.removeEventListener('blur',blur);};
 },[]);
 const modeNames={manual:'手动游玩',demo:'离线规则演示',ai:'Jev AI 官方直连'};
 const overlay=!hud.started||hud.paused||hud.status!=='playing';
 const control=(key:string,label:string)=><button aria-label={label} key={key} onPointerDown={e=>{e.preventDefault();e.currentTarget.setPointerCapture(e.pointerId);touch.current[key]=true;}} onPointerUp={()=>{touch.current[key]=false;}} onPointerCancel={()=>{touch.current[key]=false;}} onLostPointerCapture={()=>{touch.current[key]=false;}}>{label}</button>;
 return <main className="shell">
  <header className="masthead"><div className="brand"><h1>竹影<span>壹</span></h1><div><p>SHADOW OF THE BAMBOO</p><span>月下救援 · 原创忍者试验场</span></div></div><div className="chapter">第一幕<span>竹林之境</span></div></header>
  <section className="play-layout" aria-label="游戏试验场">
   <div className="game-column"><div className="game-hud"><span className="stage">CHAPTER 01 <i>/</i> 月下救援</span><div className="vitals"><span aria-label={`生命 ${hud.hp} / 5`} className="hearts">{'◆'.repeat(Math.max(0,hud.hp))}<b>{'◇'.repeat(5-Math.max(0,hud.hp))}</b></span><span>卷轴 <strong>{hud.scrolls}<small> / 3</small></strong></span></div></div>
    <div className="canvas-wrap" ref={surface}><canvas ref={canvas} width={480} height={320} aria-label="竹林横版忍者游戏画面" role="img"/>
     {overlay&&<div className="game-overlay"><span className="seal">影</span><p className="eyebrow">{hud.status==='won'?'MISSION COMPLETE':hud.status==='lost'?'TRY AGAIN':hud.paused?'PAUSED':'THE FOREST AWAITS'}</p><h2>{hud.status==='won'?'月下归来':hud.status==='lost'?'影落竹林':hud.paused?'稍作歇息':'踏入竹林'}</h2><p>{hud.status==='won'?'三枚卷轴已集齐，救援成功。':hud.status==='lost'?'再试一次，留意敌人的飞镖。':hud.paused?'准备好后，继续这场冒险。':'跃上竹台，集齐三枚卷轴，抵达鸟居完成救援。'}</p><button className="primary" onClick={()=>command.current(hud.status!=='playing'?'restart':'start')}>{hud.status!=='playing'?'重新挑战':hud.paused?'继续游戏':'开始游戏'} <span>↗</span></button>{!hud.started&&<button className="quiet" onClick={()=>command.current('demo')}>先看一场规则演示</button>}</div>}
     {hud.busy&&!overlay&&<div className="thinking">Jev 正在思考 <span>世界已暂停</span></div>}
    </div>
    <nav className="toolbar" aria-label="游戏模式"><div className="modes">{(['manual','demo','ai'] as Mode[]).map((m,i)=><button key={m} className={hud.mode===m?'selected':''} onClick={()=>command.current(m)} aria-pressed={hud.mode===m}><kbd>{i+1}</kbd>{m==='manual'?'手动':m==='demo'?'规则演示':'Jev AI'}</button>)}</div><div className="utilities"><button onClick={()=>command.current('restart')} title="R 重新开始">重开</button><button onClick={()=>command.current('pause')} title="P 暂停或继续">{hud.paused?'继续':'暂停'}</button><button onClick={()=>{if(document.fullscreenElement)void document.exitFullscreen();else void surface.current?.requestFullscreen();}} aria-label="全屏游戏">⛶</button></div></nav>
    <div className="touch-controls" aria-label="触屏操作"><div>{control('a','←')}{control('d','→')}</div><div>{control(' ','跳跃')}{control('j','飞镖')}{control('k','刀击')}</div></div>
    <div className="keyboard-help"><span><kbd>A</kbd><kbd>D</kbd> 移动</span><span><kbd>Space</kbd> 大跳跃</span><span><kbd>J</kbd> 飞镖</span><span><kbd>K</kbd> 刀击 / 挡镖</span></div>
   </div>
   <aside className="panel"><div className="panel-heading"><p className="eyebrow">CONTROL ROOM</p><h2>{modeNames[hud.mode]}</h2><span className="status">{hud.error?'调用已暂停':hud.busy?'等待模型回复':!hud.started?'准备就绪':hud.paused?'已暂停':hud.status==='won'?'救援成功':hud.status==='lost'?'挑战结束':'游戏进行中'}</span></div>
    <div className="decision"><span className="label">当前动作</span><strong>{LABELS[hud.action]||hud.action}</strong><span className="action-code">{hud.action.replaceAll('_',' ')}</span></div>
    <dl className="metrics"><div><dt>模型耗时</dt><dd>{hud.mode==='ai'?Math.round(hud.latency):'—'}<small> ms</small></dd></div><div><dt>置信度</dt><dd>{hud.mode==='ai'?Math.round(hud.confidence*100)+'%':'—'}</dd></div><div><dt>击败敌人</dt><dd>{hud.kills}</dd></div><div><dt>游戏时间</dt><dd>{hud.elapsed.toFixed(1)}<small> s</small></dd></div></dl>
    {hud.mode==='ai'&&<div className="api-budget"><div><span>本次测试调用</span><strong>{hud.calls} / {hud.limit}</strong></div><progress max={hud.limit} value={hud.calls}/><label>单次测试上限 <select aria-label="单次测试上限" value={hud.limit} onChange={e=>command.current('limit',e.target.value)}><option value="200">200 次</option><option value="500">500 次</option><option value="1000">1000 次</option></select></label><small>这是测试限制，不是账户余额。</small></div>}
    {hud.error?<div className="error" role="alert"><strong>需要处理</strong><p>{hud.error}</p><button onClick={()=>command.current('retry')}>重试连接</button><button onClick={()=>command.current('settings')}>更换 Key</button></div>:<div className="mission"><p className="eyebrow">任务 / MISSION</p><ol><li><span>01</span>跳上竹台，集齐三枚卷轴</li><li><span>02</span>飞镖远攻，近身挥刀挡镖</li><li><span>03</span>前往朱红鸟居，完成救援</li></ol></div>}
    <div className="ai-note"><p>{hud.mode==='demo'?'规则演示不调用 AI，也不会产生 API 费用。':'AI 每次执行 18 帧动作；等待回复时冻结世界。'}</p><button onClick={()=>command.current('settings')}>配置 TypeSafe Key <span>↗</span></button></div>
   </aside>
  </section>
  <footer><span>原创像素素材 · 无需安装 · 支持键盘与触屏</span><span>SHADOW LAB / 2026</span></footer>
  {modal&&<div className="modal-backdrop" onClick={()=>{command.current('cancel');setKeyInput('');}}><section role="dialog" aria-modal="true" aria-labelledby="key-title" className="key-modal" onClick={e=>e.stopPropagation()}><button className="close-modal" aria-label="关闭密钥窗口" onClick={()=>{command.current('cancel');setKeyInput('');}}>×</button><p className="eyebrow">CONNECT TO JEV</p><h2 id="key-title">让 Jev 接管这场冒险</h2><p>使用你自己的 TypeSafe 官方 Key。调用费用和额度归属于你的官方账户。</p><form onSubmit={e=>{e.preventDefault();const k=keyInput.trim();if(!k.startsWith('apikey_')||/\s/.test(k)){setKeyError('请输入 apikey_ 开头的官方 Key，Vercel Key 不适用。');return;}setKeyError('');command.current('connect',k);}}><label htmlFor="api-key">TypeSafe API Key</label><input id="api-key" type="password" autoComplete="off" autoFocus placeholder="apikey_…" value={keyInput} onChange={e=>setKeyInput(e.target.value)} maxLength={512}/>{keyError&&<p className="key-error" role="alert">{keyError}</p>}<p className="privacy-note">Key 仅保存在当前页面内存中，经本站服务器转发给 TypeSafe；应用不保存密钥，不写入日志。关闭页面后需要重新输入。</p><button className="primary" type="submit">连接并开始 AI 测试 <span>↗</span></button></form><button className="quiet" onClick={()=>{command.current('cancel');setKeyInput('');}}>暂时使用手动模式</button></section></div>}
 </main>;
}
