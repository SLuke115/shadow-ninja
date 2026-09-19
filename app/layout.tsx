import type { Metadata } from 'next';
import './globals.css';
export const metadata:Metadata={title:'竹影 · Shadow of the Bamboo',description:'原创竹林忍者游戏：大跳跃、飞镖与刀击。支持手动游玩、离线规则演示及 TypeSafe Jev AI 测试。',icons:{icon:'/favicon.svg'}};
export default function RootLayout({children}:Readonly<{children:React.ReactNode}>){return <html lang="zh-CN"><body>{children}</body></html>;}
