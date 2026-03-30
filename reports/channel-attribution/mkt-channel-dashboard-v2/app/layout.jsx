import { Inter, JetBrains_Mono, Noto_Sans_SC } from 'next/font/google';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });
const jetbrains = JetBrains_Mono({ subsets: ['latin'], variable: '--font-mono' });
const notoSC = Noto_Sans_SC({ subsets: ['latin'], weight: ['400', '500', '600', '700'], variable: '--font-cn' });

export const metadata = {
  title: '瑞幸北美 · 渠道流量贡献分析 V2',
  description: '基于排除法的营销团队贡献度追踪 — Luckin Coffee NA Channel Attribution V2',
};

export default function RootLayout({ children }) {
  return (
    <html lang="zh-CN" className={`${inter.variable} ${jetbrains.variable} ${notoSC.variable}`}>
      <body style={{ margin: 0, padding: 0, fontFamily: 'var(--font-inter), var(--font-cn), system-ui, sans-serif', background: '#f8f9fb', color: '#1f2937' }}>
        {children}
      </body>
    </html>
  );
}
