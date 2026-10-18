import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const sampleCase = {
  case_id: "case-a-damaged-sale",
  title: "Damaged sale item with timely report",
  created_at: "2026-10-01T12:00:00Z",
  documents: [{
    document_id: "a-policy",
    document_type: "policy",
    title: "Fictional refund policy",
    passages: [{ passage_id: "a-policy-p1", text: "including items purchased at a sale price", page_number: null }],
  }],
};

const analysis = {
  case_id: sampleCase.case_id,
  findings: [{ classification: "documented_fact", statement: "The policy includes sale purchases.", sources: [{ document_id: "a-policy", passage_id: "a-policy-p1", quoted_text: "including items purchased at a sale price" }] }],
  supporting_policy_clauses: [],
  conflicting_policy_clauses: [],
  missing_evidence: [],
  follow_up_questions: [],
  assessment: "potentially_supported",
  explanation: "The supplied documents potentially support a request.",
  documented_deadline: null,
  provider: "mock",
  simulated: true,
};

const summaries = [{ case_id: sampleCase.case_id, title: sampleCase.title, description: "A fictional damaged item example." }];

function jsonResponse(value: unknown, status = 200) {
  return Promise.resolve({ ok: status >= 200 && status < 300, status, json: () => Promise.resolve(value) } as Response);
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("Appeal Agent frontend", () => {
  it("renders a sample, shows simulated findings, and opens cited evidence", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/sample-cases")) return jsonResponse(summaries);
      if (url.includes("/sample-cases/")) return jsonResponse(sampleCase);
      return jsonResponse(analysis);
    });

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /try an example/i }));
    await screen.findByText(sampleCase.title);
    fireEvent.click(screen.getByRole("button", { name: new RegExp(sampleCase.title) }));
    await screen.findByText(/Selected example/i);
    fireEvent.click(screen.getByRole("button", { name: /show example findings/i }));
    await screen.findByText(/Fictional example — simulated findings/i);
    fireEvent.click(screen.getAllByRole("button", { name: /view evidence/i }).at(-1)!);
    expect(await screen.findByRole("dialog")).toHaveTextContent("including items purchased at a sale price");
  });

  it("shows a readable upload error and does not create an upload workspace", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => jsonResponse({ detail: { code: "unsupported_file_type", message: "Only .pdf and .txt files are supported." } }, 422));

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /review my documents/i }));
    const input = screen.getByLabelText(/document file/i);
    fireEvent.change(input, { target: { files: [new File(["not supported"], "notes.docx")] } });
    expect(await screen.findByRole("alert")).toHaveTextContent("Only .pdf and .txt files are supported.");
    expect(screen.queryByText(/Extracted documents/i)).not.toBeInTheDocument();
  });

  it("displays passage text and page metadata after successful extraction", async () => {
    const extracted = {
      document: {
        document_id: "doc-fictional-pdf",
        document_type: "receipt",
        title: "Fictional refund sample",
        passages: [
          { passage_id: "p-1", text: "FICTIONAL PAGE ONE\nOrder HF-2048", page_number: 1 },
          { passage_id: "p-2", text: "FICTIONAL PAGE TWO", page_number: 2 },
        ],
      },
      metadata: { format: "pdf", page_count: 2, character_count: 40, passage_count: 2 },
      warnings: [],
    };
    vi.spyOn(globalThis, "fetch").mockImplementation(() => jsonResponse(extracted));

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /review my documents/i }));
    fireEvent.change(screen.getByLabelText(/document file/i), { target: { files: [new File(["fictional"], "fictional.pdf", { type: "application/pdf" })] } });

    expect(await screen.findByText("Fictional refund sample")).toBeInTheDocument();
    expect(screen.getByText("2 extracted passages")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /hide extracted text/i })).toBeInTheDocument();
    expect(screen.getByText(/FICTIONAL PAGE ONE/)).toBeInTheDocument();
    expect(screen.getByText(/Order HF-2048/)).toBeInTheDocument();
    expect(screen.getByText(/Page 1/)).toBeInTheDocument();
  });

  it("ignores a stale sample response after the user switches cases", async () => {
    let resolveFirst!: (value: Response) => void;
    const first = new Promise<Response>((resolve) => { resolveFirst = resolve; });
    const secondCase = {
      ...sampleCase,
      case_id: "case-b-missing-dates",
      title: "Missing dates example",
      documents: [{
        ...sampleCase.documents[0],
        title: "Second policy",
        passages: [{ passage_id: "b-policy-p1", text: "within 14 calendar days after delivery", page_number: null }],
      }],
    };
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/sample-cases")) return jsonResponse([
        ...summaries,
        { case_id: secondCase.case_id, title: secondCase.title, description: "A second fictional example." },
      ]);
      if (url.includes(sampleCase.case_id)) return first;
      return jsonResponse(secondCase);
    });

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /try an example/i }));
    await screen.findByText(secondCase.title);
    fireEvent.click(screen.getAllByRole("button", { name: new RegExp(sampleCase.title) })[0]);
    fireEvent.click(screen.getAllByRole("button", { name: new RegExp(secondCase.title) })[0]);
    await waitFor(() => expect(screen.getByText(secondCase.title)).toBeInTheDocument());
    resolveFirst(jsonResponse(sampleCase) as unknown as Response);
    await waitFor(() => expect(screen.queryByText("Fictional refund policy")).not.toBeInTheDocument());
    expect(screen.getByRole("heading", { name: secondCase.title })).toBeInTheDocument();
  });
});
