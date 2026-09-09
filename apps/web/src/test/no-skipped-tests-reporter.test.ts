import type {
  FullResult,
  TestCase,
  TestResult,
} from "@playwright/test/reporter";
import { describe, expect, it, vi } from "vitest";

import NoSkippedTestsReporter from "../../e2e/no-skipped-tests-reporter";

describe("NoSkippedTestsReporter", () => {
  it("fails a mandatory browser run when Playwright reports a skipped test", async () => {
    const reporter = new NoSkippedTestsReporter();
    const error = vi
      .spyOn(console, "error")
      .mockImplementation(() => undefined);

    reporter.onTestEnd(
      {
        titlePath: () => ["required.spec.ts", "required scenario"],
      } as TestCase,
      { status: "skipped" } as TestResult,
    );

    await expect(
      reporter.onEnd({ status: "passed" } as FullResult),
    ).resolves.toEqual({ status: "failed" });
    error.mockRestore();
  });

  it("does not override a browser run with zero skips", async () => {
    const reporter = new NoSkippedTestsReporter();

    reporter.onTestEnd(
      {
        titlePath: () => ["required.spec.ts", "required scenario"],
      } as TestCase,
      { status: "passed" } as TestResult,
    );

    await expect(
      reporter.onEnd({ status: "passed" } as FullResult),
    ).resolves.toBeUndefined();
  });
});
