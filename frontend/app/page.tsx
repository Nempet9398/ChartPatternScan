import SearchBar from "@/components/SearchBar";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center px-4 py-20">
      {/* 로고 / 타이틀 */}
      <div className="mb-10 text-center">
        <h1 className="text-4xl font-black tracking-tight text-slate-900 sm:text-5xl">
          Chart<span className="text-blue-600">Pattern</span>.io
        </h1>
        <p className="mt-3 text-base text-slate-500 max-w-md">
          종목 + 기간 선택 →{" "}
          <span className="font-semibold text-slate-700">
            현재 차트와 가장 유사한 고전 패턴 Top 3
          </span>
          를 유사도(%)로 분석합니다
        </p>
        <p className="mt-1 text-xs text-slate-400">
          Lo, Mamaysky &amp; Wang (2000) 논문 기반 규칙 매칭 · LLM 미사용
        </p>
      </div>

      {/* 검색바 */}
      <SearchBar />

      {/* 빠른 예시 */}
      <div className="mt-6 flex flex-wrap gap-2 justify-center">
        {[
          { label: "Apple", symbol: "AAPL" },
          { label: "삼성전자", symbol: "005930.KS" },
          { label: "Bitcoin", symbol: "BTC-USD" },
          { label: "NVIDIA", symbol: "NVDA" },
          { label: "카카오", symbol: "035720.KQ" },
        ].map(({ label, symbol }) => (
          <a
            key={symbol}
            href={`/result/${encodeURIComponent(symbol)}`}
            className="px-3 py-1.5 rounded-full text-xs font-medium
                       bg-white border border-slate-200 text-slate-600
                       hover:border-blue-400 hover:text-blue-600 transition shadow-sm"
          >
            {label}
          </a>
        ))}
      </div>

      {/* 면책 고지 */}
      <p className="mt-16 text-center text-xs text-slate-400 max-w-sm leading-relaxed">
        본 서비스의 분석 결과는 투자 권유가 아닙니다.
        <br />
        투자 손익의 책임은 전적으로 본인에게 있습니다.
      </p>
    </main>
  );
}
