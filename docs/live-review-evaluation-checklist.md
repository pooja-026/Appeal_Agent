# Live review manual evaluation checklist

This checklist is for local manual evaluation only. It is separate from the fictional input documents and must never be uploaded or sent to the model.

## Test setup

- [ ] Confirm the backend is configured with `AI_PROVIDER=anthropic` and the verified model ID in `.env` without printing the API key.
- [ ] Start the backend and frontend in separate PowerShell terminals.
- [ ] Open `http://localhost:5173/` and choose **Review my documents**.
- [ ] Upload only `examples/live-review/denial.txt` as **Denial or refusal**.
- [ ] Upload only `examples/live-review/policy.txt` as **Retailer policy**.
- [ ] Confirm both documents show extracted passages before analysis.
- [ ] Confirm the app requires an explicit click on **Analyze my documents** and does not analyze on upload.

## Expected live behavior

- [ ] The result is labeled **AI-generated analysis — review against your documents**.
- [ ] The response has `simulated=false` and is a live Anthropic result, not a sample fixture response.
- [ ] The analysis identifies that the damage report was made two days after delivery: delivery is October 2, 2026 and the customer message is October 4, 2026.
- [ ] The analysis distinguishes the change-of-mind exclusion from the separate damaged-item rule that includes sale-priced items.
- [ ] The analysis explains that the supplied policy appears to support asking Cedar & Finch to reconsider.
- [ ] The analysis does not promise a refund. It states that the policy offers a replacement or refund after evidence review and confirmation.
- [ ] The analysis says the customer reports attaching photographs, while also making clear that the application has not received or inspected those photographs.
- [ ] The analysis does not treat the 14-day damage-reporting window as an appeal or reconsideration deadline.
- [ ] Substantive findings and policy interpretations cite passages from the uploaded denial or policy document.
- [ ] Every **View evidence** link opens the matching uploaded passage, with the correct document title and no fabricated text.

## Semantic precision checks

- [ ] Present information is not labeled missing: the supplied order number and delivery/reporting dates should remain recognized as present.
- [ ] The analysis distinguishes information absent from the documents, information present but not independently verified, and optional corroborating evidence.
- [ ] Evidence is described as policy-required only when the supplied policy explicitly requires it.
- [ ] A request for independent carrier or delivery confirmation is not presented as required unless the policy says so; it may be described only as optional corroboration when appropriate.
- [ ] The change-of-mind exclusion is not listed as conflicting evidence when the documents establish that the request concerns damage instead.
- [ ] Statements are attributed only to the speaker or source established by the uploaded documents; summary metadata is not silently attributed to a retailer message.
- [ ] Findings do not repeat the same conclusion across multiple sections without adding distinct information.
- [ ] Reporting windows remain separate from reconsideration or appeal deadlines.
- [ ] The analysis does not promise a particular remedy when the policy allows alternatives.
- [ ] Any date comparison or calculation cites every premise, including each relevant delivery, report, or policy-window passage; quotation validation confirms source existence but cannot prove semantic completeness.

These are human-review expectations for live model quality. The offline mocked-provider tests validate plumbing, schema handling, and citation checks; they do not prove that a live model follows these semantic expectations.

## Reviewer notes

Record the observed assessment, citations, missing evidence, and follow-up questions here after the manual run. Do not edit the source documents to make the result pass, and do not upload this checklist.
