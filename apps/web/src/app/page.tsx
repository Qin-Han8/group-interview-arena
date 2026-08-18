import AuthPanel from "./auth-panel";
import HealthStatus from "./health-status";

export default function Home() {
  return (
    <main className="min-h-screen bg-[#f7f7f5] px-6 py-16 text-neutral-950 sm:px-10 sm:py-24">
      <section className="mx-auto flex min-h-[calc(100vh-8rem)] max-w-3xl flex-col justify-center">
        <p className="mb-8 text-sm font-medium tracking-[0.16em] text-neutral-500 uppercase">
          Internal validation foundation
        </p>

        <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
          AI 群面训练场
        </h1>
        <p className="mt-3 text-xl text-neutral-600 sm:text-2xl">
          Group Interview Arena
        </p>

        <div className="my-10 space-y-2 border-y border-neutral-300 py-6 text-sm sm:flex sm:gap-10 sm:space-y-0">
          <p>Current phase: P1</p>
          <p>Target: V0.1 Internal Validation</p>
        </div>

        <div className="space-y-2 text-sm leading-6 text-neutral-600">
          <p>AI candidates are virtual characters.</p>
          <p>
            Question-bound text sessions are available for internal validation.
          </p>
          <HealthStatus />
        </div>

        <AuthPanel />
      </section>
    </main>
  );
}
