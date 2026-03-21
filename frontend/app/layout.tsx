import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ChartPattern.io — 차트 패턴 분석기",
  description:
    "종목 + 기간 선택 → 현재 차트가 어떤 고전 패턴과 가장 유사한지 Top 3를 유사도(%)로 보여주는 무료 웹 서비스. Lo(2000) 논문 기반 순수 알고리즘.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-slate-50 text-slate-900">
        {children}
      </body>
    </html>
  );
}
