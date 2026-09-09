import type {
  FullResult,
  Reporter,
  TestCase,
  TestResult,
} from "@playwright/test/reporter";

export default class NoSkippedTestsReporter implements Reporter {
  private readonly skippedTests: string[] = [];

  onTestEnd(test: TestCase, result: TestResult): void {
    if (result.status === "skipped") {
      this.skippedTests.push(test.titlePath().join(" > "));
    }
  }

  async onEnd(
    _result: FullResult,
  ): Promise<{ status: FullResult["status"] } | undefined> {
    void _result;
    if (this.skippedTests.length === 0) {
      return undefined;
    }
    console.error(
      `Mandatory Playwright tests skipped:\n${this.skippedTests.join("\n")}`,
    );
    return { status: "failed" };
  }
}
