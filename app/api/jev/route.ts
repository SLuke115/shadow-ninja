import { ACTIONS } from '../../../lib/game';
const headers={'Cache-Control':'no-store'};
const error=(message:string,status:number)=>Response.json({error:message},{status,headers});
export async function POST(request:Request){
 const origin=request.headers.get('origin');
 if(origin&&origin!==new URL(request.url).origin)return error('不允许跨站调用。',403);
 if(Number(request.headers.get('content-length')||0)>32768)return error('请求过大。',413);
 try {
  const text=await request.text();if(text.length>32768)return error('请求过大。',413);
  const {key,state}=JSON.parse(text);
  if(typeof key!=='string'||!key.startsWith('apikey_')||key.length>512||/\s/.test(key))return error('请输入 TypeSafe 官方 Key（apikey_ 开头）。',400);
  if(!state||typeof state!=='object'||!state.player||typeof state.player.x!=='number')return error('游戏状态无效。',400);
  const start=Date.now();
  const response=await fetch('https://api.typesafe.ai/v1/systemone',{
   method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${key}`},
   body:JSON.stringify({model:'jev-latest',state,questions:{action:{type:'choice',instructions:'Control this ninja. Collect the remaining scrolls in order using platforms to reach high ones. Jump toward scrolls; reverse if overshooting. Throw toward enemies at your height; slash nearby enemies. After all scrolls, head right to x=2500. Select exactly one action macro.',criteria:ACTIONS}}}),
   signal:AbortSignal.timeout(15000),redirect:'error'
  });
  if(!response.ok){const messages:Record<number,string>={401:'Key 验证失败，请重新配置官方 Key。',403:'此 Key 没有调用权限，请检查官方账户。',402:'TypeSafe 账户余额不足，请在官方控制台检查额度。',429:'官方接口限流，游戏已暂停。请稍后手动重试。'};return error(messages[response.status]||`官方接口暂时不可用（${response.status}），请稍后重试。`,response.status>=400&&response.status<600?response.status:502);}
  const data=await response.json() as {answers?:Record<string,{choice:string;confidence:number;probabilities:Record<string,number>}>;choices?:Record<string,{choice:string;confidence:number;probabilities:Record<string,number>}>};const a=data.answers?.action??data.choices?.action;
  if(!a||!(a.choice in ACTIONS)||typeof a.confidence!=='number'||!a.probabilities)return error('模型响应格式不符合预期。',502);
  return Response.json({action:a.choice,confidence:a.confidence,probabilities:a.probabilities,latency:Date.now()-start},{headers});
 }catch(e){return error(e instanceof SyntaxError?'请求格式无效。':'连接超时或网络异常，游戏已暂停，可手动重试。',e instanceof SyntaxError?400:502);}
}
