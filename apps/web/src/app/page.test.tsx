import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import Home from "./page";

vi.mock("./auth-panel", () => ({
  default: () => <div data-testid="auth-panel-boundary" />,
}));

describe("Home", () => {
  it("is a neutral full-width root that delegates shell ownership", () => {
    const { container } = render(<Home />);

    expect(screen.getByRole("main")).toHaveClass("min-h-dvh", "w-full");
    expect(screen.getByTestId("auth-panel-boundary")).toBeInTheDocument();
    expect(container.querySelector(".max-w-3xl")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Internal validation foundation"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Current phase: P1")).not.toBeInTheDocument();
  });
});
