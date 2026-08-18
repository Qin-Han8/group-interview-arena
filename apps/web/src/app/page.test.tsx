import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "./page";

describe("Home", () => {
  it("renders the P1 internal validation foundation copy", () => {
    render(<Home />);

    expect(
      screen.getByRole("heading", { level: 1, name: "AI 群面训练场" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Group Interview Arena")).toBeInTheDocument();
    expect(
      screen.getByText("Internal validation foundation"),
    ).toBeInTheDocument();
    expect(screen.getByText("Current phase: P1")).toBeInTheDocument();
    expect(
      screen.getByText("Target: V0.1 Internal Validation"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("AI candidates are virtual characters."),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Question-bound text sessions are available for internal validation.",
      ),
    ).toBeInTheDocument();
  });
});
