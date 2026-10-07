import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { TicketFilters } from "@/features/tickets/ticket-filters";
import { renderWithProviders } from "@/test/utils";

describe("TicketFilters", () => {
  it("emits a status filter on change", async () => {
    const onChange = vi.fn();
    renderWithProviders(
      <TicketFilters value={{}} onChange={onChange} onReset={() => {}} />,
    );

    await userEvent.click(screen.getByLabelText(/filter by status/i));
    await userEvent.click(await screen.findByRole("option", { name: /open/i }));

    expect(onChange).toHaveBeenCalledWith({
      status: ["OPEN"],
      page: 1,
    });
  });

  it("debounces nothing — search updates trigger immediately", async () => {
    const onChange = vi.fn();
    renderWithProviders(
      <TicketFilters value={{}} onChange={onChange} onReset={() => {}} />,
    );

    await userEvent.type(screen.getByLabelText(/search tickets/i), "billing");
    // Every keystroke fires onChange with the current value.
    expect(onChange).toHaveBeenCalled();
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    expect(lastCall).toEqual({ search: "billing", page: 1 });
  });

  it("shows the Clear button only when a filter is active", () => {
    const { rerender } = renderWithProviders(
      <TicketFilters value={{}} onChange={() => {}} onReset={() => {}} />,
    );
    expect(screen.queryByRole("button", { name: /clear/i })).toBeNull();

    rerender(
      <TicketFilters
        value={{ search: "x" }}
        onChange={() => {}}
        onReset={() => {}}
      />,
    );
    expect(screen.getByRole("button", { name: /clear/i })).toBeInTheDocument();
  });
});
